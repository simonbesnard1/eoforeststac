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
import time
from collections.abc import Callable, Mapping, MutableMapping
from typing import Any

import dask
import fsspec
import xarray as xr
import zarr

from eoforeststac.core.zarr import add_display_range

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


class RetryingStore(MutableMapping):
    """A Zarr 2 store that retries failed chunk writes.

    One chunk upload dropped by a busy object store (Ceph answers 499 when a
    request stalls) otherwise fails the whole level, hours of work for a
    global product. Each write is retried with growing pauses; reads and
    deletes pass straight through.
    """

    def __init__(self, store: MutableMapping, attempts: int = 6, pause: float = 2.0):
        self.store, self.attempts, self.pause = store, attempts, pause

    def __setitem__(self, key, value):
        for attempt in range(self.attempts):
            try:
                self.store[key] = value
                return
            except OSError:
                if attempt == self.attempts - 1:
                    raise
                time.sleep(self.pause * 2**attempt)

    def __getitem__(self, key):
        return self.store[key]

    def __delitem__(self, key):
        del self.store[key]

    def __contains__(self, key):
        return key in self.store

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)


def _to_zarr(ds: xr.Dataset, mapper: Any, **kwargs: Any) -> None:
    # Zarr 2 (pinned) takes any mapping; Zarr 3 wants its own store types
    store = RetryingStore(mapper) if zarr.__version__.startswith("2") else mapper
    if "region" in kwargs:  # metadata exists already; only chunks are written
        ds.to_zarr(store, **kwargs)
        return
    kwargs = {"mode": "w", "consolidated": True, **kwargs}
    try:
        ds.to_zarr(store, zarr_format=2, **kwargs)
    except TypeError:  # older xarray
        ds.to_zarr(store, zarr_version=2, **kwargs)


def _write_level(
    fs: fsspec.AbstractFileSystem,
    parent: xr.Dataset,
    level_path: str,
    y_dim: str,
    x_dim: str,
    plan: Mapping[str, str],
    *,
    output_dtype: str | None,
    chunk_size: int,
    strip_chunks: int,
    workers: int,
    log: Callable[[str], None],
    label: str,
) -> None:
    """Write one overview level in strips of rows, each with a marker.

    Writing a whole level at once plans every chunk in one dask graph: for
    JRC TMF level 2 (built from ~1.6 M level-1 chunks) that exhausted mefe's
    memory and killed the run without an error. Each strip of
    ``strip_chunks`` chunk rows is planned from its own slice of the parent,
    so memory stays bounded, and a crash resumes from the first strip
    without a marker instead of redoing the level.
    """

    def overview(ds: xr.Dataset) -> xr.Dataset:
        result = coarsen_level(ds, y_dim, x_dim, plan, output_dtype)
        chunks = {dim: 1 for dim in result.dims}
        chunks.update({y_dim: chunk_size, x_dim: chunk_size})
        return result.chunk(chunks)

    mapper = fs.get_mapper(level_path)
    rows = chunk_size * strip_chunks
    # Even an unwritten overview of the whole level is costly: to_zarr builds
    # its full task graph (5.5 GB for one TMF variable). The metadata comes
    # from a stand-in instead: the first strip's variables, attributes and
    # encodings, with lazy zeros of the level's full size in one dask chunk
    # each (one task per variable; the Zarr chunks are set in the encoding).
    first = overview(parent.isel({y_dim: slice(0, 2 * rows)}))
    # The same window-centre coordinates the reducers produce
    full_y = parent[y_dim].coarsen({y_dim: 2}, boundary="pad").mean().values
    height, width = len(full_y), first.sizes[x_dim]
    data_vars = {}
    for name, var in first.data_vars.items():
        if y_dim not in var.dims:
            data_vars[name] = var
            continue
        shape = tuple(height if d == y_dim else var.sizes[d] for d in var.dims)
        stand_in = xr.DataArray(
            dask.array.zeros(shape, dtype=var.dtype, chunks=-1),
            dims=var.dims,
            attrs=var.attrs,
        )
        stand_in.encoding = {
            **{k: v for k, v in var.encoding.items() if k != "preferred_chunks"},
            "chunks": tuple(chunk_size if d in (y_dim, x_dim) else 1 for d in var.dims),
        }
        data_vars[name] = stand_in
    coords = {k: c for k, c in first.coords.items() if y_dim not in c.dims}
    template = xr.Dataset(
        data_vars, coords={**coords, y_dim: full_y}, attrs=first.attrs
    )
    strips = math.ceil(height / rows)
    done = {
        int(p.rsplit("_", 1)[-1])
        for p in fs.glob(f"{level_path}/_strip_*")
        if p.rsplit("_", 1)[-1].isdigit()
    }
    if done and fs.exists(f"{level_path}/.zmetadata"):
        log(f"  {label}: resuming, {len(done)}/{strips} strips done")
    else:
        if fs.exists(level_path):
            log(f"  {label}: replacing an unfinished level")
            fs.rm(level_path, recursive=True)
        done = set()
        # Metadata and the small non-gridded variables only; no chunks yet
        _to_zarr(template, mapper, compute=False)
    log(f"  {label}: writing {height:,} x {width:,} px in {strips} strip(s)")

    for i in range(strips):
        if i in done:
            continue
        start, stop = i * rows, min((i + 1) * rows, height)
        # Overview row r comes from parent rows 2r and 2r+1
        strip = overview(parent.isel({y_dim: slice(2 * start, 2 * stop)}))
        strip = strip.drop_vars(
            [n for n, v in strip.variables.items() if y_dim not in v.dims]
        )
        with dask.config.set(scheduler="threads", num_workers=workers):
            _to_zarr(strip, mapper, region={y_dim: slice(start, stop)})
        fs.touch(f"{level_path}/_strip_{i}")
        if strips > 1:
            log(f"  {label}: strip {i + 1}/{strips} done")
    for p in fs.glob(f"{level_path}/_strip_*"):
        fs.rm(p)


def build_pyramid(
    fs: fsspec.AbstractFileSystem,
    source: str,
    reducers: Mapping[str, str] | None = None,
    *,
    target_size: int = 8192,
    chunk_size: int = 512,
    strip_chunks: int = 16,
    workers: int = 4,
    output_dtype: str | None = "float32",
    log: Callable[[str], None] = print,
) -> str:
    """Build (or finish) the pyramid of the store at ``source`` (bucket/key).

    Completed levels are kept; a level left unfinished by an interrupted run
    resumes from its last completed strip of ``strip_chunks`` chunk rows.
    Returns the pyramid's path.
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
        _write_level(
            fs,
            parent,
            level_path,
            y_dim,
            x_dim,
            plan,
            output_dtype=output_dtype,
            chunk_size=chunk_size,
            strip_chunks=strip_chunks,
            workers=workers,
            log=log,
            label=f"level {level}",
        )
        fs.touch(f"{level_path}/_SUCCESS")
        parent = open_store(fs, level_path)
    log(f"  complete: {output}")
    return output


def add_store_display_ranges(
    fs: fsspec.AbstractFileSystem,
    source: str,
    reducers: Mapping[str, str],
    *,
    pyramid: str | None = None,
    overwrite: bool = False,
    log: Callable[[str], None] = print,
) -> dict[str, list]:
    """Measure continuous-variable display ranges and store them everywhere.

    A completed pyramid's coarsest level is the cheapest representative sample
    and is also what the explorer previously measured at runtime. The resulting
    p2-p98 range is copied to the native store and every completed overview so
    any client can read it directly from variable metadata. Small stores without
    a pyramid are sampled directly. Only variables whose reducer (configured or
    inferred) is ``mean`` are treated as continuous; integer classes and
    event-year rasters are left alone.
    """
    source = source.rstrip("/")
    pyramid = (pyramid or pyramid_path(source)).rstrip("/")
    # Configured reducers only name the exceptions; infer the rest as the
    # pyramid build does (ULS, Xu and GAMI age classes configure none)
    ds = open_store(fs, source)
    plan = reducer_plan(ds, *detect_spatial_dims(ds.dims), reducers)
    variables = [name for name, method in plan.items() if method == "mean"]
    if not variables:
        log("  display ranges: no continuous variables")
        return {}

    complete_levels: list[str] = []
    try:
        multiscales = json.loads(fs.cat(f"{pyramid}/.zattrs"))["multiscales"][0]
        complete_levels = [
            str(item["path"])
            for item in multiscales.get("datasets", [])
            if fs.exists(f"{pyramid}/{item['path']}/_SUCCESS")
        ]
    except (FileNotFoundError, KeyError, IndexError, TypeError, ValueError):
        pass

    sample = f"{pyramid}/{complete_levels[-1]}" if complete_levels else source
    log(f"  display ranges: sampling {sample}")
    ranges = add_display_range(
        sample,
        variables=variables,
        fs=fs,
        overwrite=overwrite,
    )
    if not ranges:
        log("  display ranges: no valid samples")
        return {}

    method = "2nd-98th percentile of valid values, sampled from " + (
        f"visualization pyramid level {complete_levels[-1]}"
        if complete_levels
        else "the native store"
    )
    targets = [source] + [f"{pyramid}/{level}" for level in complete_levels]
    for target in targets:
        group = zarr.open_group(fs.get_mapper(target), mode="r+")
        changed = False
        for name, display_range in ranges.items():
            if name not in group:
                continue
            group[name].attrs.update(
                {"display_range": display_range, "display_range_method": method}
            )
            changed = True
        if changed:
            zarr.consolidate_metadata(fs.get_mapper(target))
    log(f"  display ranges: {json.dumps(ranges, sort_keys=True)}")
    return ranges
