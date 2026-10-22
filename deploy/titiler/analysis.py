"""Region analytics: area-weighted time series of the explorer's layers.

The browser posts a GeoJSON geometry (EPSG:4326) and the layers to analyse,
each with the *kind* its catalog recipe declares. The statistics themselves
come from ``eoforeststac.analytics`` (shared with the Python package); this
module only chooses what to read and runs it as a background job:

- the native store when the clipped area fits MAX_ANALYSIS_PIXELS, otherwise
  the finest *finished* pyramid level (``_SUCCESS``) that fits, provided the
  variable's pyramid reducer is a mean; results from a pyramid are flagged
  as approximate;
- POST /analysis returns a job id, GET /analysis/{id} reports progress and,
  once done, the rows.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import dask
import obstore
import xarray as xr
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from download import JOB_ID, _Progress, _apply_sel, open_lazy, validate_geometry
from eoforeststac.analytics import (
    KINDS,
    clip_to_geometry,
    geometry_area_ha,
    region_statistics,
    spatial_dims,
    statistics_rows,
)

# Pixels x steps one analysis may read at native resolution or from a level
MAX_ANALYSIS_PIXELS = int(float(os.getenv("MAX_ANALYSIS_PIXELS", "1.5e9")))
MAX_ANALYSIS_LAYERS = int(os.getenv("MAX_ANALYSIS_LAYERS", "6"))
ANALYSIS_DASK_WORKERS = int(os.getenv("ANALYSIS_DASK_WORKERS", "4"))
ANALYSIS_TTL_SECONDS = int(os.getenv("ANALYSIS_TTL_SECONDS", str(2 * 3600)))
MAX_PYRAMID_LEVELS = 10

# Kinds whose values can be averaged into coarser cells; counts and
# per-pixel amounts must be computed at native resolution
PYRAMID_KINDS = frozenset({"density", "mean", "cover"})

# One job at a time, like downloads: each uses ANALYSIS_DASK_WORKERS threads
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="analysis")


class AnalysisOptions(BaseModel):
    """Recipe options passed through to eoforeststac.analytics."""

    classes: dict[int, str] | None = Field(None, max_length=200)
    exclude: list[int] = Field(default_factory=list, max_length=200)
    years: list[int] | None = Field(None, min_length=2, max_length=2)
    encoding: str = Field("year", pattern="^(year|yyddd)$")
    scale: float | None = None


class AnalysisLayer(BaseModel):
    url: str
    variable: str = Field(..., max_length=200)
    kind: str = Field(..., max_length=40)
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)
    # Pins for extra dimensions other than time (e.g. an ensemble member)
    sel: list[str] = Field(default_factory=list, max_length=8)
    name: str = Field("layer", max_length=120)


class AnalysisRequest(BaseModel):
    geometry: dict[str, Any]
    layers: list[AnalysisLayer] = Field(
        ..., min_length=1, max_length=MAX_ANALYSIS_LAYERS
    )


@dataclass
class AnalysisJob:
    id: str
    created: float = field(default_factory=time.time)
    status: str = "queued"  # queued | running | done | error
    progress: float = 0.0
    message: str = "Queued"
    result: dict[str, Any] | None = None


_JOBS: dict[str, AnalysisJob] = {}
_JOBS_LOCK = threading.Lock()


# ── Choosing what to read ───────────────────────────────────────────────


def _read_json(url: str) -> dict[str, Any] | None:
    root, _, key = url.rpartition("/")
    try:
        store = obstore.store.from_url(root)
        return json.loads(bytes(obstore.get(store, key).bytes()))
    except Exception:
        return None


def _exists(url: str) -> bool:
    root, _, key = url.rpartition("/")
    try:
        obstore.head(obstore.store.from_url(root), key)
        return True
    except Exception:
        return False


def _pyramid_levels(url: str, variable: str) -> list[str]:
    """Finished pyramid levels (finest first) whose reducer is a mean."""
    pyramid = url.removesuffix("/").removesuffix(".zarr") + "_pyramid.zarr"
    attrs = _read_json(f"{pyramid}/.zattrs") or {}
    meta = (attrs.get("multiscales") or [{}])[0].get("metadata", {})
    if meta.get("reducers", {}).get(variable) != "mean":
        return []
    levels = []
    for level in range(1, MAX_PYRAMID_LEVELS + 1):
        if not _exists(f"{pyramid}/{level}/_SUCCESS"):
            break
        levels.append(f"{pyramid}/{level}")
    return levels


def _cost(da: xr.DataArray, geometry: dict[str, Any]) -> int:
    """Pixels x steps the clipped read would touch (coordinates only)."""
    sub, _ = clip_to_geometry(da, geometry, da.rio.crs)
    return int(sub.size)


def _open(layer: AnalysisLayer, url: str) -> xr.DataArray:
    ds = open_lazy(url)
    if layer.variable not in ds.data_vars:
        raise HTTPException(404, f"{layer.name}: unknown variable {layer.variable}")
    da = _apply_sel(ds[layer.variable], layer.sel)
    if da.rio.crs is None and ds.rio.crs is not None:
        da = da.rio.write_crs(ds.rio.crs)
    spatial_dims(da)
    return da


def choose_source(
    layer: AnalysisLayer, geometry: dict[str, Any]
) -> tuple[xr.DataArray, int, str]:
    """Return (data, pyramid level or 0 for native, url) for one layer."""
    try:
        native = _open(layer, layer.url)
    except HTTPException:
        raise  # already a clear message (e.g. unknown variable)
    except Exception as exc:
        raise HTTPException(404, f"Could not open {layer.name}") from exc
    try:
        cost = _cost(native, geometry)
    except ValueError as exc:
        raise HTTPException(400, f"{layer.name}: {exc}") from exc
    if cost <= MAX_ANALYSIS_PIXELS:
        return native, 0, layer.url
    levels = (
        _pyramid_levels(layer.url, layer.variable)
        if layer.kind in PYRAMID_KINDS
        else []
    )
    for level, url in enumerate(levels, start=1):
        da = _open(layer, url)
        if _cost(da, geometry) <= MAX_ANALYSIS_PIXELS:
            return da, level, url
    raise HTTPException(
        413,
        f"{layer.name}: the area is too large to analyse "
        f"({cost / 1e9:.1f} billion pixel-steps at native resolution); draw a smaller area",
    )


def _resolution_m(da: xr.DataArray) -> float:
    y, x = spatial_dims(da)
    step = abs(float(da[x].values[1] - da[x].values[0]))
    return step * 111_320 if da.rio.crs.is_geographic else step


# ── Job ─────────────────────────────────────────────────────────────────


def _run(
    job: AnalysisJob, geometry: dict[str, Any], layers: list[AnalysisLayer]
) -> None:
    job.status = "running"
    try:
        results = []
        for index, layer in enumerate(layers):
            job.message = f"Analysing {layer.name} ({index + 1}/{len(layers)})"
            try:
                da, level, url = choose_source(layer, geometry)
                parts = region_statistics(
                    da,
                    geometry,
                    kind=layer.kind,
                    crs=da.rio.crs,
                    compute=False,
                    **layer.options.model_dump(exclude_none=True),
                )
                lazy = {k: v for k, v in parts.items() if isinstance(v, xr.DataArray)}
                with dask.config.set(
                    scheduler="threads", num_workers=ANALYSIS_DASK_WORKERS
                ):
                    with _Progress(job, index / len(layers), 1 / len(layers)):
                        computed = dict(zip(lazy, dask.compute(*lazy.values())))

                results.append(
                    {
                        "name": layer.name,
                        "variable": layer.variable,
                        "kind": layer.kind,
                        "units": da.attrs.get("units", ""),
                        "level": level,
                        "approximate": level > 0,
                        "resolution_m": round(_resolution_m(da), 1),
                        "rows": statistics_rows({**parts, **computed}, layer.kind),
                    }
                )
            except HTTPException as exc:
                results.append({"name": layer.name, "error": exc.detail})
            except Exception as exc:  # one layer failing must not lose the others
                results.append({"name": layer.name, "error": str(exc)[:300]})
        job.result = {"region_area_ha": geometry_area_ha(geometry), "layers": results}
        job.status, job.progress, job.message = "done", 1.0, "Done"
    except Exception as exc:  # reported to the browser, never raised
        job.status, job.message = "error", str(exc)[:400]


def _expire_jobs() -> None:
    cutoff = time.time() - ANALYSIS_TTL_SECONDS
    with _JOBS_LOCK:
        for job_id in [
            j.id for j in _JOBS.values() if j.created < cutoff and j.status != "running"
        ]:
            _JOBS.pop(job_id)


# ── Routes ──────────────────────────────────────────────────────────────


def create_router(validate_url: Callable[[str], str]) -> APIRouter:
    router = APIRouter(prefix="/analysis", include_in_schema=False)

    @router.post("")
    def start(request: AnalysisRequest):
        geometry = validate_geometry(request.geometry)
        for layer in request.layers:
            validate_url(layer.url)
            if layer.kind not in KINDS:
                raise HTTPException(
                    400, f"{layer.name}: unsupported kind {layer.kind!r}"
                )
        _expire_jobs()
        job = AnalysisJob(id=uuid.uuid4().hex)
        with _JOBS_LOCK:
            _JOBS[job.id] = job
        _EXECUTOR.submit(_run, job, geometry, request.layers)
        return {"id": job.id}

    @router.get("/{job_id}")
    def status(job_id: str):
        _expire_jobs()
        job = _JOBS.get(job_id) if JOB_ID.match(job_id) else None
        if job is None:
            raise HTTPException(404, "Unknown or expired analysis")
        return {
            "status": job.status,
            "progress": round(job.progress, 3),
            "message": job.message,
            "result": job.result,
        }

    return router
