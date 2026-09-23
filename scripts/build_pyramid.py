"""Build a resumable visualization pyramid for one S3-backed Zarr dataset.

The native dataset remains in its existing store and acts as level 0. Only
coarsened levels 1..N are written to ``*_pyramid.zarr``. Each level is derived
from the preceding level and receives a ``_SUCCESS`` marker after a complete
write, allowing interrupted jobs to resume safely.

This produces visualization overviews, not scientifically interchangeable
aggregates. Select reducers deliberately: ``mean`` for continuous variables,
``max`` for event/presence layers, and ``first`` for categorical classes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

import dask
import numpy as np
import s3fs
import xarray as xr
import zarr

_SPATIAL_CANDIDATES = (
    ("latitude", "longitude"),
    ("lat", "lon"),
    ("y", "x"),
)
_REDUCERS = {"mean", "max", "first"}


def first_valid(values: np.ndarray, axis: int | tuple[int, ...] | None = None) -> np.ndarray:
    """Select the first non-null value across xarray's coarsening axes."""
    if axis is None:
        axes = tuple(range(values.ndim))
    elif isinstance(axis, int):
        axes = (axis,)
    else:
        axes = axis
    axes = tuple(item if item >= 0 else values.ndim + item for item in axes)
    destinations = tuple(range(values.ndim - len(axes), values.ndim))
    moved = np.moveaxis(values, axes, destinations)
    flat = moved.reshape(*moved.shape[: -len(axes)], -1)
    valid = ~np.isnan(flat)
    positions = valid.argmax(axis=-1)
    selected = np.take_along_axis(flat, positions[..., None], axis=-1)[..., 0]
    return np.where(valid.any(axis=-1), selected, np.nan)


def make_s3() -> s3fs.S3FileSystem:
    """Create an authenticated S3 client for the GFZ-compatible endpoint."""
    kwargs: dict[str, Any] = {
        "client_kwargs": {
            "endpoint_url": os.environ.get("AWS_S3_ENDPOINT", "https://s3.gfz-potsdam.de")
        }
    }
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        kwargs["key"] = os.environ["AWS_ACCESS_KEY_ID"]
    if os.environ.get("AWS_SECRET_ACCESS_KEY"):
        kwargs["secret"] = os.environ["AWS_SECRET_ACCESS_KEY"]
    if os.environ.get("AWS_SESSION_TOKEN"):
        kwargs["token"] = os.environ["AWS_SESSION_TOKEN"]
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        kwargs["anon"] = True
    return s3fs.S3FileSystem(**kwargs)


def normalize_s3_url(url: str) -> str:
    """Convert a GFZ HTTPS asset URL to the equivalent S3 URL."""
    if url.startswith("s3://"):
        return url.rstrip("/")
    parsed = urlsplit(url)
    endpoint = urlsplit(os.environ.get("AWS_S3_ENDPOINT", "https://s3.gfz-potsdam.de"))
    if parsed.scheme == "https" and parsed.hostname == endpoint.hostname:
        return f"s3://{parsed.path.lstrip('/').rstrip('/')}"
    raise ValueError(f"Expected an s3:// URL or GFZ S3 HTTPS URL, got: {url}")


def s3_path(url: str) -> str:
    return normalize_s3_url(url).removeprefix("s3://")


def s3_map(url: str, s3: s3fs.S3FileSystem, **kwargs: Any) -> s3fs.S3Map:
    return s3fs.S3Map(root=s3_path(url), s3=s3, **kwargs)


def detect_spatial_dims(ds: xr.Dataset) -> tuple[str, str]:
    for y_dim, x_dim in _SPATIAL_CANDIDATES:
        if y_dim in ds.dims and x_dim in ds.dims:
            return y_dim, x_dim
    raise ValueError(
        f"Cannot auto-detect spatial dims from {list(ds.dims)}. "
        "Pass --dims <y_dim> <x_dim> explicitly."
    )


def parse_reducers(values: list[str]) -> dict[str, str]:
    reducers: dict[str, str] = {}
    for value in values:
        try:
            variable, reducer = value.rsplit("=", 1)
        except ValueError as exc:
            raise ValueError(f"Reducer must use VARIABLE=METHOD syntax: {value}") from exc
        if reducer not in _REDUCERS:
            raise ValueError(f"Unsupported reducer {reducer!r}; choose from {sorted(_REDUCERS)}")
        reducers[variable] = reducer
    return reducers


def infer_reducer(name: str, attrs: Mapping[str, Any]) -> str:
    """Choose a conservative visualization reducer from variable metadata."""
    lowered = name.lower()
    if attrs.get("legend") or attrs.get("flag_values") or attrs.get("flag_meanings"):
        return "first"
    if "year" in lowered or any(token in lowered for token in ("gain", "loss")):
        return "max"
    if any(token in lowered for token in ("class", "category", "type", "mask")):
        return "first"
    return "mean"


def reducer_plan(
    ds: xr.Dataset,
    y_dim: str,
    x_dim: str,
    overrides: Mapping[str, str],
) -> dict[str, str]:
    unknown = set(overrides) - set(ds.data_vars)
    if unknown:
        raise ValueError(f"Reducer overrides reference unknown variables: {sorted(unknown)}")
    return {
        name: overrides.get(name, infer_reducer(name, variable.attrs))
        for name, variable in ds.data_vars.items()
        if y_dim in variable.dims and x_dim in variable.dims
    }


def coarsen_level(
    ds: xr.Dataset,
    y_dim: str,
    x_dim: str,
    reducers: Mapping[str, str],
    output_dtype: str | None,
) -> xr.Dataset:
    """Create one 2x overview level, retaining metadata and non-grid variables."""
    output_vars: dict[str, xr.DataArray] = {}
    with xr.set_options(keep_attrs=True):
        for name, variable in ds.data_vars.items():
            if y_dim not in variable.dims or x_dim not in variable.dims:
                output_vars[name] = variable
                continue

            coarsened = variable.coarsen({y_dim: 2, x_dim: 2}, boundary="pad", coord_func="mean")
            method = reducers[name]
            if method == "mean":
                result = coarsened.mean(skipna=True)
            elif method == "max":
                result = coarsened.max(skipna=True)
            else:
                result = coarsened.reduce(first_valid)

            if output_dtype:
                result = result.astype(output_dtype)
            result.attrs.update(variable.attrs)
            result.attrs["pyramid_reducer"] = method
            output_vars[name] = result

    result = xr.Dataset(output_vars, attrs=dict(ds.attrs))
    result.attrs.update(
        {
            "pyramid_kind": "visualization",
            "pyramid_factor_from_parent": 2,
        }
    )
    return result


def automatic_levels(ds: xr.Dataset, y_dim: str, x_dim: str, target_size: int) -> int:
    largest = max(ds.sizes[y_dim], ds.sizes[x_dim])
    return max(1, math.ceil(math.log2(largest / target_size)))


def open_zarr_store(store: s3fs.S3Map, group: str | None = None) -> xr.Dataset:
    try:
        return xr.open_zarr(store, group=group, consolidated=True, chunks={})
    except (KeyError, ValueError, zarr.errors.GroupNotFoundError):
        return xr.open_zarr(store, group=group, consolidated=False, chunks={})


def level_marker_path(output_url: str, level: int) -> str:
    return f"{s3_path(output_url)}/{level}/_SUCCESS"


def prepare_root(
    output_store: s3fs.S3Map,
    source_url: str,
    levels: int,
    reducers: Mapping[str, str],
) -> None:
    try:
        root = zarr.open_group(output_store, mode="a", zarr_format=2)
    except TypeError:  # Zarr 2 uses the older keyword.
        root = zarr.open_group(output_store, mode="a", zarr_version=2)
    root.attrs.update(
        {
            "multiscales": [
                {
                    "version": "0.4",
                    "name": "EOForestSTAC visualization pyramid",
                    "datasets": [{"path": str(level)} for level in range(1, levels + 1)],
                    "metadata": {
                        "native_source": source_url,
                        "native_level": 0,
                        "reducers": dict(reducers),
                    },
                }
            ]
        }
    )


def build_pyramid(args: argparse.Namespace) -> None:
    source_url = normalize_s3_url(args.url)
    output_url = normalize_s3_url(args.out or source_url.removesuffix(".zarr") + "_pyramid.zarr")
    if source_url == output_url:
        raise ValueError("Source and output stores must be different")

    s3 = make_s3()
    source_store = s3_map(source_url, s3)
    source = open_zarr_store(source_store)
    y_dim, x_dim = tuple(args.dims) if args.dims else detect_spatial_dims(source)
    overrides = parse_reducers(args.reducer)
    reducers = reducer_plan(source, y_dim, x_dim, overrides)
    levels = args.levels or automatic_levels(source, y_dim, x_dim, args.target_size)
    output_dtype = None if args.output_dtype == "source" else args.output_dtype

    print(f"Source: {source_url}")
    print(f"Output: {output_url}")
    print(f"Dimensions: {dict(source.sizes)}")
    print(f"Spatial dimensions: {y_dim}, {x_dim}")
    print(f"Reducers: {json.dumps(reducers, sort_keys=True)}")
    print(f"Output data dtype: {output_dtype or 'source'}")
    print(f"Levels: {levels} coarsened levels (native data remains level 0)")
    for level in range(1, levels + 1):
        factor = 2**level
        rows = math.ceil(source.sizes[y_dim] / factor)
        columns = math.ceil(source.sizes[x_dim] / factor)
        print(f"  {level}: {factor}x -> {rows:,} x {columns:,}")

    if args.dry_run:
        print("Dry run: nothing written.")
        return

    output_store = s3_map(output_url, s3, check=False)
    prepare_root(output_store, source_url, levels, reducers)

    parent = source
    for level in range(1, levels + 1):
        marker = level_marker_path(output_url, level)
        level_url = f"{output_url}/{level}"
        level_store = s3_map(level_url, s3, check=False)
        if s3.exists(marker):
            print(f"Level {level}: complete; resuming from existing level")
            parent.close()
            parent = open_zarr_store(level_store)
            continue

        level_prefix = f"{s3_path(output_url)}/{level}"
        if s3.exists(level_prefix):
            if not args.overwrite_incomplete:
                raise RuntimeError(
                    f"Level {level} exists without _SUCCESS. Inspect it, then rerun "
                    "with --overwrite-incomplete to replace that exact level."
                )
            print(f"Level {level}: removing incomplete prefix {level_prefix}")
            s3.rm(level_prefix, recursive=True)

        print(f"Level {level}: constructing 2x overview")
        overview = coarsen_level(parent, y_dim, x_dim, reducers, output_dtype=output_dtype)
        chunks = {y_dim: args.chunk_size, x_dim: args.chunk_size}
        for dim in overview.dims:
            if dim not in chunks:
                chunks[dim] = 1
        overview = overview.chunk(chunks)
        print(f"Level {level}: writing with chunks {chunks}")
        with dask.config.set(scheduler="threads", num_workers=args.workers):
            overview.to_zarr(
                level_store,
                mode="w",
                consolidated=True,
                zarr_version=2,
            )
        s3.touch(marker)
        parent.close()
        parent = open_zarr_store(level_store)
        print(f"Level {level}: complete")

    parent.close()
    print(f"Pyramid complete: {output_url}")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("url", help="Source s3:// or GFZ HTTPS Zarr URL")
    parser.add_argument("--out", help="Output URL; defaults to *_pyramid.zarr")
    parser.add_argument(
        "--levels",
        type=int,
        help="Number of coarsened levels; automatically calculated when omitted",
    )
    parser.add_argument(
        "--target-size",
        type=int,
        default=8192,
        help="Maximum width/height of the coarsest level (default: 8192)",
    )
    parser.add_argument("--dims", nargs=2, metavar=("Y_DIM", "X_DIM"))
    parser.add_argument(
        "--reducer",
        action="append",
        default=[],
        metavar="VARIABLE=METHOD",
        help="Per-variable mean, max, or first reducer; repeat as needed",
    )
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--output-dtype",
        choices=("float32", "float64", "source"),
        default="float32",
        help="Overview data dtype (default: float32)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--overwrite-incomplete",
        action="store_true",
        help="Delete and replace an incomplete level; completed levels are retained",
    )
    return parser


def main() -> None:
    try:
        build_pyramid(make_parser().parse_args())
    except (ValueError, RuntimeError) as exc:
        sys.exit(f"error: {exc}")


if __name__ == "__main__":
    main()
