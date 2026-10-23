"""Build a resumable visualization pyramid for one Zarr store.

The native store stays where it is and acts as level 0. Only coarsened levels
1..N are written, to ``<store>_pyramid.zarr``. Each level is derived from the
one before and gets a ``_SUCCESS`` marker once written completely, so an
interrupted build continues from the first unfinished level.

These are visualization overviews, not scientifically interchangeable
aggregates: ``mean`` for continuous variables, ``max`` for event and presence
layers, ``first`` for categorical classes.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping
from typing import Any

import dask
import fsspec
import xarray as xr

SPATIAL_DIMS = (("latitude", "longitude"), ("lat", "lon"), ("y", "x"))
REDUCERS = {"mean", "max", "first"}


def pyramid_path(store_path: str) -> str:
    return store_path.rstrip("/").removesuffix(".zarr") + "_pyramid.zarr"


def first_valid_2x2(coarsened: Any, y_dim: str, x_dim: str) -> xr.DataArray:
    """The first non-null value of each 2x2 window, in row-major order.

    Built from element-wise ``where`` so it stays lazy and chunk-local under
    dask; a generic ``Coarsen.reduce`` with ``np.take_along_axis`` has no dask
    implementation and loads the whole variable into memory.
    """
    windows = coarsened.construct({y_dim: (y_dim, "_wy"), x_dim: (x_dim, "_wx")})
    result = windows.isel(_wy=0, _wx=0, drop=True)
    for wy, wx in ((0, 1), (1, 0), (1, 1)):
        result = result.where(result.notnull(), windows.isel(_wy=wy, _wx=wx, drop=True))
    # construct() reshapes the spatial coordinates into windows; use the
    # window-centre coordinates that the mean/max reducers produce
    return result.drop_vars([y_dim, x_dim], errors="ignore").assign_coords(
        {
            dim: coarsened.obj[dim].coarsen({dim: 2}, boundary="pad").mean().values
            for dim in (y_dim, x_dim)
        }
    )


def detect_spatial_dims(dims: Any) -> tuple[str, str]:
    for y_dim, x_dim in SPATIAL_DIMS:
        if y_dim in dims and x_dim in dims:
            return y_dim, x_dim
    raise ValueError(f"Cannot find spatial dimensions in {list(dims)}")


def infer_reducer(name: str, attrs: Mapping[str, Any]) -> str:
    """A conservative reducer from the variable's name and metadata."""
    lowered = name.lower()
    if attrs.get("legend") or attrs.get("flag_values") or attrs.get("flag_meanings"):
        return "first"
    if "year" in lowered or any(token in lowered for token in ("gain", "loss")):
        return "max"
    if any(token in lowered for token in ("class", "category", "type", "mask")):
        return "first"
    return "mean"


def reducer_plan(
    ds: xr.Dataset, y_dim: str, x_dim: str, overrides: Mapping[str, str]
) -> dict[str, str]:
    """Reducer for every gridded variable: configured, else inferred."""
    bad = {k: v for k, v in overrides.items() if v not in REDUCERS}
    if bad:
        raise ValueError(f"Unknown reducers {bad}; choose from {sorted(REDUCERS)}")
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
    """One 2x overview level, keeping metadata and non-gridded variables."""
    output_vars: dict[str, xr.DataArray] = {}
    with xr.set_options(keep_attrs=True):
        for name, variable in ds.data_vars.items():
            if y_dim not in variable.dims or x_dim not in variable.dims:
                output_vars[name] = variable
                continue
            coarsened = variable.coarsen(
                {y_dim: 2, x_dim: 2}, boundary="pad", coord_func="mean"
            )
            method = reducers[name]
            if method == "mean":
                result = coarsened.mean(skipna=True)
            elif method == "max":
                result = coarsened.max(skipna=True)
            else:
                result = first_valid_2x2(coarsened, y_dim, x_dim)
            if output_dtype:
                result = result.astype(output_dtype)
            result.attrs.update(variable.attrs)
            result.attrs["pyramid_reducer"] = method
            output_vars[name] = result

    result = xr.Dataset(output_vars, attrs=dict(ds.attrs))
    result.attrs.update(
        {"pyramid_kind": "visualization", "pyramid_factor_from_parent": 2}
    )
    return result


def level_count(height: int, width: int, target_size: int) -> int:
    """Levels until the coarsest one is at most ``target_size`` pixels wide."""
    return max(1, math.ceil(math.log2(max(height, width) / target_size)))


def open_store(fs: fsspec.AbstractFileSystem, path: str) -> xr.Dataset:
    mapper = fs.get_mapper(path)
    try:
        return xr.open_zarr(mapper, consolidated=True, chunks={})
    except (KeyError, ValueError, FileNotFoundError):
        return xr.open_zarr(mapper, consolidated=False, chunks={})


def _write_root(
    fs: fsspec.AbstractFileSystem,
    output: str,
    source: str,
    levels: int,
    reducers: Mapping[str, str],
) -> None:
    attrs = {
        "multiscales": [
            {
                "version": "0.4",
                "name": "EOForestSTAC visualization pyramid",
                "datasets": [{"path": str(level)} for level in range(1, levels + 1)],
                "metadata": {
                    "native_source": source,
                    "native_level": 0,
                    "reducers": dict(reducers),
                },
            }
        ]
    }
    fs.pipe(f"{output}/.zgroup", json.dumps({"zarr_format": 2}).encode())
    fs.pipe(f"{output}/.zattrs", json.dumps(attrs, indent=4).encode())


def _to_zarr(ds: xr.Dataset, mapper: Any) -> None:
    try:
        ds.to_zarr(mapper, mode="w", consolidated=True, zarr_format=2)
    except TypeError:  # older xarray
        ds.to_zarr(mapper, mode="w", consolidated=True, zarr_version=2)


def build_pyramid(
    fs: fsspec.AbstractFileSystem,
    source: str,
    reducers: Mapping[str, str] | None = None,
    *,
    target_size: int = 8192,
    chunk_size: int = 512,
    workers: int = 4,
    output_dtype: str | None = "float32",
    log: Callable[[str], None] = print,
) -> str:
    """Build (or finish) the pyramid of the store at ``source`` (bucket/key).

    Completed levels are kept; a level left unfinished by an interrupted run
    is replaced. Returns the pyramid's path.
    """
    source = source.rstrip("/")
    output = pyramid_path(source)
    ds = open_store(fs, source)
    y_dim, x_dim = detect_spatial_dims(ds.dims)
    plan = reducer_plan(ds, y_dim, x_dim, reducers or {})
    levels = level_count(ds.sizes[y_dim], ds.sizes[x_dim], target_size)
    log(
        f"{source}: {ds.sizes[y_dim]:,} x {ds.sizes[x_dim]:,} px, {levels} levels, "
        f"reducers {json.dumps(plan, sort_keys=True)}"
    )
    _write_root(fs, output, source, levels, plan)

    parent = ds
    for level in range(1, levels + 1):
        level_path = f"{output}/{level}"
        if fs.exists(f"{level_path}/_SUCCESS"):
            log(f"  level {level}: already complete")
            parent = open_store(fs, level_path)
            continue
        if fs.exists(level_path):
            log(f"  level {level}: replacing an unfinished level")
            fs.rm(level_path, recursive=True)
        overview = coarsen_level(parent, y_dim, x_dim, plan, output_dtype)
        chunks = {dim: 1 for dim in overview.dims}
        chunks.update({y_dim: chunk_size, x_dim: chunk_size})
        overview = overview.chunk(chunks)
        log(
            f"  level {level}: writing {overview.sizes[y_dim]:,} x {overview.sizes[x_dim]:,} px"
        )
        with dask.config.set(scheduler="threads", num_workers=workers):
            _to_zarr(overview, fs.get_mapper(level_path))
        fs.touch(f"{level_path}/_SUCCESS")
        parent = open_store(fs, level_path)
    log(f"  complete: {output}")
    return output
