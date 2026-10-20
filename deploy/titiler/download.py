"""Area downloads: clip the explorer's active layers to a drawn geometry.

The browser posts a GeoJSON geometry (EPSG:4326) plus the layers it shows.
Each layer is cut to the geometry's bounding box in its own CRS at native
resolution, masked to the polygon, and written chunk by chunk with dask, so
memory stays bounded by the chunk size rather than the request size:
GeoTIFF for 2-D selections, NetCDF when extra dimensions remain. The files
are zipped with a README carrying each dataset's license and citation.

Requests of up to MAX_DOWNLOAD_BYTES (uncompressed) can take minutes, so they
run as background jobs: POST /download returns a job id, the browser polls
GET /download/{id} and finally fetches GET /download/{id}/file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import dask
import dask.array as dsa
import numpy as np
import obstore
import rasterio.features
import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr
from affine import Affine
from dask.callbacks import Callback
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from rasterio.crs import CRS
from rasterio.warp import transform_geom
from titiler.xarray.io import X_DIM_NAMES, Y_DIM_NAMES
from zarr.storage import ObjectStore

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "/downloads"))
MAX_DOWNLOAD_BYTES = int(float(os.getenv("MAX_DOWNLOAD_BYTES", str(5e9))))
MAX_DOWNLOAD_LAYERS = int(os.getenv("MAX_DOWNLOAD_LAYERS", "12"))
DOWNLOAD_TTL_SECONDS = int(os.getenv("DOWNLOAD_TTL_SECONDS", str(2 * 3600)))
DOWNLOAD_DASK_WORKERS = int(os.getenv("DOWNLOAD_DASK_WORKERS", "4"))
MAX_GEOMETRY_VERTICES = 20_000
# Keep this much disk free beyond the request itself.
DISK_HEADROOM_BYTES = 2 * 1024**3

WGS84 = CRS.from_epsg(4326)
X_NAMES = ("x", *X_DIM_NAMES)
Y_NAMES = ("y", *Y_DIM_NAMES)
JOB_ID = re.compile(r"^[0-9a-f]{32}$")

# One job at a time: each already uses DOWNLOAD_DASK_WORKERS threads, and
# serialising keeps the worst-case disk use at one request.
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="download")


class LayerRequest(BaseModel):
    url: str
    variable: str = Field(..., max_length=200)
    sel: list[str] = Field(default_factory=list, max_length=8)
    name: str = Field("layer", max_length=120)
    title: str = Field("", max_length=500)
    license: str = Field("", max_length=200)
    citation: str = Field("", max_length=1000)
    providers: str = Field("", max_length=1000)


class DownloadRequest(BaseModel):
    geometry: dict[str, Any]
    layers: list[LayerRequest] = Field(
        ..., min_length=1, max_length=MAX_DOWNLOAD_LAYERS
    )


@dataclass
class Job:
    id: str
    created: float = field(default_factory=time.time)
    status: str = "queued"  # queued | running | done | error
    progress: float = 0.0
    message: str = "Queued"
    path: Path | None = None
    size: int = 0


_JOBS: dict[str, Job] = {}
_JOBS_LOCK = threading.Lock()


# ── Geometry ────────────────────────────────────────────────────────────


def _rings(geometry: dict[str, Any]) -> list[list[list[float]]]:
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Polygon":
        return list(coords or [])
    if kind == "MultiPolygon":
        return [ring for polygon in coords or [] for ring in polygon]
    raise HTTPException(400, "Geometry must be a Polygon or MultiPolygon")


def validate_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    rings = _rings(geometry)
    vertices = sum(len(ring) for ring in rings)
    if not rings or vertices < 4:
        raise HTTPException(400, "Geometry has no area")
    if vertices > MAX_GEOMETRY_VERTICES:
        raise HTTPException(
            400, f"Geometry has more than {MAX_GEOMETRY_VERTICES} vertices"
        )
    for ring in rings:
        for point in ring:
            if (
                len(point) < 2
                or not all(isinstance(v, (int, float)) for v in point[:2])
                or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90)
            ):
                raise HTTPException(
                    400, "Geometry coordinates must be lon/lat in EPSG:4326"
                )
    return {"type": geometry["type"], "coordinates": geometry["coordinates"]}


def _bounds(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    points = np.array([p[:2] for ring in _rings(geometry) for p in ring], dtype=float)
    return (*points.min(axis=0), *points.max(axis=0))


def _is_bbox(geometry: dict[str, Any]) -> bool:
    """True for a single axis-aligned rectangle (no polygon mask needed)."""
    if geometry["type"] != "Polygon" or len(geometry["coordinates"]) != 1:
        return False
    ring = {tuple(p[:2]) for p in geometry["coordinates"][0]}
    xs = {p[0] for p in ring}
    ys = {p[1] for p in ring}
    return len(ring) == 4 and len(xs) == 2 and len(ys) == 2


# ── Layer preparation ───────────────────────────────────────────────────


@lru_cache(maxsize=8)
def open_lazy(url: str) -> xr.Dataset:
    """Open a Zarr store with dask chunks matching its own chunking."""
    store = ObjectStore(store=obstore.store.from_url(url), read_only=True)
    return xr.open_dataset(store, engine="zarr", chunks={}, decode_coords="all")


def _spatial_dims(da: xr.DataArray) -> tuple[str, str]:
    y_dim = next((d for d in Y_NAMES if d in da.dims), None)
    x_dim = next((d for d in X_NAMES if d in da.dims), None)
    if not y_dim or not x_dim:
        raise HTTPException(400, f"No spatial dimensions in {list(da.dims)}")
    return y_dim, x_dim


def _apply_sel(da: xr.DataArray, selections: list[str]) -> xr.DataArray:
    """Apply the explorer's `dim=value` / `dim=nearest::value` selections."""
    for item in selections:
        dim, _, raw = item.partition("=")
        method = None
        if raw.startswith("nearest::"):
            method, raw = "nearest", raw.removeprefix("nearest::")
        if dim not in da.dims:
            raise HTTPException(400, f"Unknown dimension in selection: {dim}")
        if dim not in da.coords:  # labels were positions
            da = da.isel({dim: int(raw)})
            continue
        dtype = da[dim].dtype
        if np.issubdtype(dtype, np.datetime64):
            value: Any = np.datetime64(raw)
        elif np.issubdtype(dtype, np.integer):
            value = int(float(raw))
        elif np.issubdtype(dtype, np.floating):
            value = float(raw)
        else:
            value = raw
        da = da.sel({dim: value}, method=method)
    return da


def _nodata_for(da: xr.DataArray) -> float | int:
    if np.issubdtype(da.dtype, np.floating):
        return float("nan")
    for source in (da.encoding, da.attrs):
        for key in ("_FillValue", "missing_value", "nodata"):
            if source.get(key) is not None:
                return source[key]
    info = np.iinfo(da.dtype)
    return info.max if info.min == 0 else info.min


@dataclass
class PreparedLayer:
    request: LayerRequest
    data: xr.DataArray
    crs: CRS
    y_dim: str
    x_dim: str
    nodata: float | int

    @property
    def nbytes(self) -> int:
        return int(self.data.size * self.data.dtype.itemsize)

    @property
    def extension(self) -> str:
        return "tif" if self.data.ndim == 2 else "nc"


def prepare_layer(layer: LayerRequest, geometry: dict[str, Any]) -> PreparedLayer:
    """Lazily cut one layer to the geometry; nothing is read but coordinates."""
    try:
        ds = open_lazy(layer.url)
    except Exception as exc:
        raise HTTPException(404, f"Could not open {layer.name}") from exc
    if layer.variable not in ds.data_vars:
        raise HTTPException(404, f"{layer.name}: unknown variable {layer.variable}")

    da = _apply_sel(ds[layer.variable], layer.sel)
    y_dim, x_dim = _spatial_dims(da)
    da = da.transpose(..., y_dim, x_dim)
    crs = da.rio.crs or ds.rio.crs or WGS84

    native = geometry if crs == WGS84 else transform_geom(WGS84, crs, geometry)
    minx, miny, maxx, maxy = _bounds(native)

    xs = da[x_dim].values
    ys = da[y_dim].values
    resx = float(xs[1] - xs[0]) if xs.size > 1 else 0.0
    resy = float(ys[1] - ys[0]) if ys.size > 1 else 0.0
    ix = np.nonzero((xs >= minx - abs(resx) / 2) & (xs <= maxx + abs(resx) / 2))[0]
    iy = np.nonzero((ys >= miny - abs(resy) / 2) & (ys <= maxy + abs(resy) / 2))[0]
    if ix.size == 0 or iy.size == 0:
        raise HTTPException(400, f"{layer.name}: the area is outside this dataset")
    sub = da.isel(
        {
            y_dim: slice(int(iy[0]), int(iy[-1]) + 1),
            x_dim: slice(int(ix[0]), int(ix[-1]) + 1),
        }
    )

    nodata = _nodata_for(sub)
    if not (crs == WGS84 and _is_bbox(geometry)):
        mask = _polygon_mask(sub, native, y_dim, x_dim, resx, resy)
        # xr.where orders dims by its first argument (the 2-D mask); restore
        # (..., y, x) so writers see the extra dimensions first.
        masked = xr.where(mask, sub, nodata, keep_attrs=True).astype(sub.dtype)
        sub = masked.transpose(*sub.dims)
    return PreparedLayer(layer, sub, crs, y_dim, x_dim, nodata)


def _polygon_mask(
    sub: xr.DataArray,
    geometry: dict[str, Any],
    y_dim: str,
    x_dim: str,
    resx: float,
    resy: float,
) -> xr.DataArray:
    """Rasterize the geometry lazily, one block per spatial chunk."""
    xs = sub[x_dim].values
    ys = sub[y_dim].values
    chunks = sub.chunksizes
    template = dsa.zeros(
        (ys.size, xs.size), chunks=(chunks[y_dim], chunks[x_dim]), dtype=bool
    )

    def block(_, block_info=None):
        (y0, y1), (x0, x1) = block_info[0]["array-location"]
        transform = Affine(resx, 0, xs[x0] - resx / 2, 0, resy, ys[y0] - resy / 2)
        return rasterio.features.geometry_mask(
            [geometry],
            out_shape=(y1 - y0, x1 - x0),
            transform=transform,
            invert=True,
            all_touched=True,
        )

    mask = dsa.map_blocks(block, template, dtype=bool)
    return xr.DataArray(
        mask, dims=(y_dim, x_dim), coords={y_dim: sub[y_dim], x_dim: sub[x_dim]}
    )


# ── Writers ─────────────────────────────────────────────────────────────


def _clean_attrs(attrs: dict[str, Any]) -> dict[str, Any]:
    """NetCDF/GeoTIFF tags take scalars, strings and flat numeric lists."""
    clean = {}
    for key, value in attrs.items():
        if isinstance(value, (str, int, float, np.number)):
            clean[key] = value
        elif isinstance(value, bool):
            clean[key] = int(value)
        elif isinstance(value, (list, tuple)) and all(
            isinstance(v, (int, float, np.number)) and not isinstance(v, bool)
            for v in value
        ):
            clean[key] = list(value)
        else:
            clean[key] = json.dumps(value, default=str)
    return clean


def write_layer(prepared: PreparedLayer, path: Path) -> None:
    out = prepared.data.rio.set_spatial_dims(x_dim=prepared.x_dim, y_dim=prepared.y_dim)
    out = out.rio.write_crs(prepared.crs)
    out.attrs = _clean_attrs(out.attrs)
    if prepared.extension == "tif":
        out.rio.write_nodata(prepared.nodata, encoded=False, inplace=True)
        out.rio.to_raster(
            path,
            tiled=True,
            blockxsize=512,
            blockysize=512,
            compress="DEFLATE",
            BIGTIFF="IF_SAFER",
            lock=threading.Lock(),
        )
        return

    name = prepared.request.variable
    ds = out.to_dataset(name=name)
    ds.attrs = {"source": prepared.request.url, "title": prepared.request.title}
    for variable in ds.variables.values():
        variable.encoding = {}
        variable.attrs = _clean_attrs(variable.attrs)
    chunks = tuple(min(512, n) for n in ds[name].shape)
    encoding = {
        name: {"compression": "gzip", "compression_opts": 4, "chunksizes": chunks}
    }
    if np.issubdtype(ds[name].dtype, np.floating):
        encoding[name]["_FillValue"] = np.nan
    ds.to_netcdf(path, engine="h5netcdf", encoding=encoding)


def _readme(prepared: list[PreparedLayer], files: list[str]) -> str:
    created = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "EOForestSTAC area download",
        f"Created: {created}",
        "Area: area.geojson (EPSG:4326). Each layer is cut to the area at its native",
        "resolution and CRS; cells outside the polygon are set to nodata.",
        "",
    ]
    for item, filename in zip(prepared, files):
        req = item.request
        lines += [
            req.title or req.name,
            f"  file:      {filename}",
            f"  variable:  {req.variable}"
            + (f"  ({', '.join(req.sel)})" if req.sel else ""),
            f"  CRS:       {item.crs.to_string()}",
            f"  shape:     {dict(zip(item.data.dims, item.data.shape))}",
        ]
        for label, value in (
            ("license", req.license),
            ("cite", req.citation),
            ("provider", req.providers),
        ):
            if value:
                lines.append(f"  {label + ':':<10} {value}")
        lines += [f"  source:    {req.url}", ""]
    return "\n".join(lines)


class _Progress(Callback):
    """Map dask task completion onto a slice of the job's progress bar."""

    def __init__(self, job: Job, start: float, span: float):
        super().__init__()
        self.job, self.start, self.span, self.total = job, start, span, 1

    def _start_state(self, dsk, state):
        self.total = max(
            1, sum(len(state[k]) for k in ("ready", "waiting", "running", "finished"))
        )

    def _posttask(self, key, result, dsk, state, worker_id):
        self.job.progress = self.start + self.span * len(state["finished"]) / self.total


def _safe_stem(name: str, used: set[str]) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "layer"
    candidate, n = stem, 2
    while candidate in used:
        candidate, n = f"{stem}_{n}", n + 1
    used.add(candidate)
    return candidate


def _run(job: Job, geometry: dict[str, Any], layers: list[LayerRequest]) -> None:
    job.status = "running"
    zip_path = DOWNLOAD_DIR / f"{job.id}.zip"
    try:
        prepared = [prepare_layer(layer, geometry) for layer in layers]
        files: list[str] = []
        used: set[str] = set()
        with zipfile.ZipFile(
            zip_path, "w", zipfile.ZIP_STORED, allowZip64=True
        ) as archive:
            for index, item in enumerate(prepared):
                filename = f"{_safe_stem(item.request.name, used)}.{item.extension}"
                job.message = f"Writing {filename} ({index + 1}/{len(prepared)})"
                part = DOWNLOAD_DIR / f"{job.id}_{index}.{item.extension}"
                try:
                    with dask.config.set(
                        scheduler="threads", num_workers=DOWNLOAD_DASK_WORKERS
                    ):
                        with _Progress(job, index / len(prepared), 1 / len(prepared)):
                            write_layer(item, part)
                    archive.write(part, arcname=filename)
                finally:
                    part.unlink(missing_ok=True)
                files.append(filename)
            for arcname, text in (
                ("area.geojson", json.dumps(geometry)),
                ("README.txt", _readme(prepared, files)),
            ):
                info = zipfile.ZipInfo(arcname, time.localtime()[:6])
                info.external_attr = 0o644 << 16  # writestr defaults to 0600
                archive.writestr(info, text)
        job.path, job.size = zip_path, zip_path.stat().st_size
        job.status, job.progress, job.message = "done", 1.0, "Ready"
    except Exception as exc:  # reported to the browser, never raised
        zip_path.unlink(missing_ok=True)
        detail = exc.detail if isinstance(exc, HTTPException) else str(exc)
        job.status, job.message = "error", str(detail)[:400]


def _expire_jobs() -> None:
    cutoff = time.time() - DOWNLOAD_TTL_SECONDS
    with _JOBS_LOCK:
        for job_id in [
            j.id for j in _JOBS.values() if j.created < cutoff and j.status != "running"
        ]:
            job = _JOBS.pop(job_id)
            if job.path:
                job.path.unlink(missing_ok=True)


def _summary(prepared: PreparedLayer) -> dict[str, Any]:
    data = prepared.data
    return {
        "name": prepared.request.name,
        "bytes": prepared.nbytes,
        "format": "GeoTIFF" if prepared.extension == "tif" else "NetCDF",
        "dims": dict(zip(data.dims, (int(n) for n in data.shape))),
        "crs": prepared.crs.to_string(),
        "y_dim": prepared.y_dim,
        "x_dim": prepared.x_dim,
        "y_range": [float(data[prepared.y_dim][0]), float(data[prepared.y_dim][-1])],
        "x_range": [float(data[prepared.x_dim][0]), float(data[prepared.x_dim][-1])],
    }


# ── Routes ──────────────────────────────────────────────────────────────


def create_router(validate_url: Callable[[str], str]) -> APIRouter:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for leftover in DOWNLOAD_DIR.glob("*"):  # jobs do not survive a restart
        if leftover.is_file():
            leftover.unlink(missing_ok=True)

    router = APIRouter(prefix="/download", include_in_schema=False)

    def checked(request: DownloadRequest) -> dict[str, Any]:
        for layer in request.layers:
            validate_url(layer.url)
        return validate_geometry(request.geometry)

    @router.post("/estimate")
    def estimate(request: DownloadRequest):
        geometry = checked(request)
        layers, total = [], 0
        for layer in request.layers:
            try:
                summary = _summary(prepare_layer(layer, geometry))
                total += summary["bytes"]
            except HTTPException as exc:
                summary = {"name": layer.name, "error": exc.detail}
            layers.append(summary)
        return {"layers": layers, "total_bytes": total, "max_bytes": MAX_DOWNLOAD_BYTES}

    @router.post("")
    def start(request: DownloadRequest):
        geometry = checked(request)
        total = sum(prepare_layer(layer, geometry).nbytes for layer in request.layers)
        if total > MAX_DOWNLOAD_BYTES:
            raise HTTPException(
                413,
                f"Request is {total / 1e9:.1f} GB; the limit is {MAX_DOWNLOAD_BYTES / 1e9:.0f} GB",
            )
        if shutil.disk_usage(DOWNLOAD_DIR).free < total + DISK_HEADROOM_BYTES:
            raise HTTPException(
                507, "Not enough disk space for this download right now"
            )
        _expire_jobs()
        job = Job(id=uuid.uuid4().hex)
        with _JOBS_LOCK:
            _JOBS[job.id] = job
        _EXECUTOR.submit(_run, job, geometry, request.layers)
        return {"id": job.id}

    def lookup(job_id: str) -> Job:
        job = _JOBS.get(job_id) if JOB_ID.match(job_id) else None
        if job is None:
            raise HTTPException(404, "Unknown or expired download")
        return job

    @router.get("/{job_id}")
    def status(job_id: str):
        _expire_jobs()
        job = lookup(job_id)
        return {
            "status": job.status,
            "progress": round(job.progress, 3),
            "message": job.message,
            "size": job.size,
        }

    @router.get("/{job_id}/file")
    def file(job_id: str):
        job = lookup(job_id)
        if job.status != "done" or not job.path or not job.path.exists():
            raise HTTPException(409, "Download is not ready")
        stamp = datetime.fromtimestamp(job.created, timezone.utc).strftime(
            "%Y%m%d-%H%M"
        )
        return FileResponse(
            job.path, media_type="application/zip", filename=f"eoforeststac_{stamp}.zip"
        )

    return router
