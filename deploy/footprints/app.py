"""Spaceborne lidar footprints (GEDI, ICESat-2) for the explorer.

Footprints are read from the gediDB and icesat2DB TileDB databases on GFZ S3
(public, read-only) with their own Python packages. They are not part of the
STAC catalog: the explorer lists the sources from GET /sources.

- POST /tile {source, i, j}: the footprints of one 0.2 x 0.2 degree tile,
  thinned for display. Tiles are cached in memory.
- POST /analysis {source, geometry}: per-year statistics of every footprint
  in a drawn area (eoforeststac.analytics.footprint_statistics).
- GET /jobs/{id}: both run as background jobs; poll for the result.

Behind the explorer's nginx at /api/footprints/.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
import warnings
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import geopandas as gpd
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from shapely.geometry import box, shape

from eoforeststac.analytics import footprint_statistics

warnings.filterwarnings("ignore", category=FutureWarning)

S3_URL = os.getenv("FOOTPRINT_S3_URL", "https://s3.gfz.de")
GEDI_BUCKET = os.getenv("GEDI_BUCKET", "dog-ext.gedidb.gedi-l2-l4-v002.0")
ICESAT2_BUCKET = os.getenv("ICESAT2_BUCKET", "dog-ext.icesat2db.icesat2-atl08-v007")
TILE_DEG = 0.2
MAX_POINTS_PER_TILE = int(os.getenv("MAX_POINTS_PER_TILE", "25000"))
MAX_ANALYSIS_DEG2 = float(os.getenv("MAX_ANALYSIS_DEG2", "1.0"))
TILE_CACHE_SIZE = int(os.getenv("TILE_CACHE_SIZE", "64"))
JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))
WORKERS = int(os.getenv("FOOTPRINT_WORKERS", "3"))
# Each database refuses queries outside its own time bounds
START = {"gedi": "2019-01-01", "icesat2": "2018-10-01"}
END = "2030-12-31"

# gediDB and icesat2DB S3 defaults (10 GB budgets, 2 GiB initial buffers)
# suit a batch server, not a shared web container
SAFE_TILEDB = {
    "sm.memory_budget": str(512 * 1024**2),
    "sm.memory_budget_var": str(256 * 1024**2),
    "sm.mem.total_budget": str(2 * 1024**3),
    "py.init_buffer_bytes": str(64 * 1024**2),
    "sm.tile_cache_size": str(256 * 1024**2),
    "sm.num_reader_threads": "4",
    "sm.num_tiledb_threads": "4",
    "sm.compute_concurrency_level": "4",
    "sm.io_concurrency_level": "4",
}

DOCS = {
    "gedi": "https://gedidb.readthedocs.io/en/latest/user/tiledb_database.html",
    "icesat2": "https://icesat2db.readthedocs.io/en/latest/user/tiledb_database.html",
}

# What the explorer offers. `variable` is the database variable, `column` the
# resulting DataFrame column, `scale` converts stored values to `units`.
SOURCES: dict[str, dict[str, Any]] = {
    "GEDI_L4A_AGBD": {
        "provider": "gedi",
        "variable": "agbd",
        "column": "agbd",
        "scale": 1.0,
        "filters": {"l4_quality_flag": "== 1"},
        "title": "GEDI L4A aboveground biomass density (footprints)",
        "quantity": "Aboveground biomass",
        "units": "Mg/ha",
        "colormap": "greens",
        "description": "Aboveground biomass density of GEDI L4A footprints (~25 m), version 2, "
        "quality-filtered (l4_quality_flag = 1). From gediDB.",
    },
    "GEDI_L2A_RH98": {
        "provider": "gedi",
        "variable": "rh:98",
        "column": "rh_p98",
        "scale": 1.0,
        "filters": {"quality_flag": "== 1"},
        "title": "GEDI L2A canopy height, RH98 (footprints)",
        "quantity": "Canopy height (RH98)",
        "units": "m",
        "colormap": "viridis",
        "description": "98th percentile relative height of GEDI L2A waveforms (~25 m footprints), "
        "version 2, quality-filtered (quality_flag = 1). From gediDB.",
    },
    "GEDI_L2B_COVER": {
        "provider": "gedi",
        "variable": "cover",
        "column": "cover",
        "scale": 100.0,
        "filters": {"l2b_quality_flag": "== 1"},
        "title": "GEDI L2B canopy cover (footprints)",
        "quantity": "Canopy cover",
        "units": "%",
        "colormap": "greens",
        "description": "Total canopy cover of GEDI L2B footprints (~25 m), version 2, "
        "quality-filtered (l2b_quality_flag = 1). From gediDB.",
    },
    "ICESAT2_ATL08_HCANOPY": {
        "provider": "icesat2",
        "variable": "h_canopy",
        "column": "h_canopy",
        "scale": 1.0,
        "filters": {"layer_flag": "== 0"},
        "title": "ICESat-2 ATL08 canopy height (segments)",
        "quantity": "Canopy height (98th percentile)",
        "units": "m",
        "colormap": "viridis",
        "description": "98th percentile relative canopy height of ICESat-2 ATL08 version 7 land "
        "segments (100 m), without cloud or blowing snow (layer_flag = 0). "
        "From icesat2DB.",
    },
}

app = FastAPI(title="EOForestSTAC footprints", docs_url=None, redoc_url=None)

_providers: dict[str, Any] = {}
_providers_lock = threading.Lock()


def provider(kind: str):
    """One shared, lazily created provider per database."""
    with _providers_lock:
        if kind not in _providers:
            if kind == "gedi":
                import gedidb

                base, bucket = gedidb.GEDIProvider, GEDI_BUCKET
            else:
                import icesat2db

                base, bucket = icesat2db.IceSat2Provider, ICESAT2_BUCKET

            class SafeProvider(base):
                # GEDIProvider and IceSat2Provider do not pass
                # s3_config_overrides on to their TileDB base provider; set
                # them right before the TileDB context is built
                def _initialize_s3_context(self, *args, **kwargs):
                    self.s3_config_overrides = SAFE_TILEDB
                    return super()._initialize_s3_context(*args, **kwargs)

            _providers[kind] = SafeProvider(
                storage_type="s3", s3_bucket=bucket, url=S3_URL
            )
        return _providers[kind]


def query(source: str, geometry, polygon: bool) -> tuple[np.ndarray, ...]:
    """(lon, lat, time, value) of the quality-filtered footprints in a geometry."""
    cfg = SOURCES[source]
    roi = gpd.GeoDataFrame(geometry=[geometry], crs="EPSG:4326")
    df = provider(cfg["provider"]).get_data(
        variables=[cfg["variable"]],
        geometry=roi,
        start_time=START[cfg["provider"]],
        end_time=END,
        return_type="dataframe",
        query_type="bounding_box",
        use_polygon_filter=polygon,
        **cfg["filters"],
    )
    if df is None or len(df) == 0:
        empty = np.empty(0)
        return empty, empty, empty.astype("datetime64[ns]"), empty
    values = df[cfg["column"]].to_numpy(dtype="float64") * cfg["scale"]
    ok = np.isfinite(values)
    return (
        df["longitude"].to_numpy()[ok],
        df["latitude"].to_numpy()[ok],
        df["time"].to_numpy(dtype="datetime64[ns]")[ok],
        values[ok],
    )


# ── Jobs ────────────────────────────────────────────────────────────────


@dataclass
class Job:
    id: str
    created: float = field(default_factory=time.time)
    status: str = "running"  # running | done | error
    message: str = "Querying"
    result: dict[str, Any] | None = None


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="footprints")
_tiles: OrderedDict[tuple, dict] = OrderedDict()
_tiles_lock = threading.Lock()


def _submit(fn, *args) -> Job:
    with _jobs_lock:
        cutoff = time.time() - JOB_TTL_SECONDS
        for jid in [j.id for j in _jobs.values() if j.created < cutoff]:
            _jobs.pop(jid)
        job = Job(id=uuid.uuid4().hex)
        _jobs[job.id] = job

    def run():
        try:
            job.result = fn(*args)
            job.status, job.message = "done", "Done"
        except HTTPException as exc:
            job.status, job.message = "error", str(exc.detail)
        except Exception as exc:  # reported to the browser
            job.status, job.message = "error", str(exc)[:300]

    _executor.submit(run)
    return job


def _tile_result(source: str, i: int, j: int) -> dict:
    key = (source, i, j)
    with _tiles_lock:
        if key in _tiles:
            _tiles.move_to_end(key)
            return _tiles[key]
    w, s = -180 + i * TILE_DEG, -90 + j * TILE_DEG
    lon, lat, t, v = query(source, box(w, s, w + TILE_DEG, s + TILE_DEG), polygon=False)
    n = v.size
    keep = np.arange(n)
    if n > MAX_POINTS_PER_TILE:  # thin for display, uniformly
        keep = np.sort(
            np.random.default_rng(i * 100003 + j).choice(
                n, MAX_POINTS_PER_TILE, replace=False
            )
        )
    result = {
        "count": int(n),
        "shown": int(keep.size),
        "lon": np.round(lon[keep], 5).tolist(),
        "lat": np.round(lat[keep], 5).tolist(),
        "v": np.round(v[keep], 2).tolist(),
        "year": (t[keep].astype("datetime64[Y]").astype(int) + 1970).tolist(),
    }
    with _tiles_lock:
        _tiles[key] = result
        while len(_tiles) > TILE_CACHE_SIZE:
            _tiles.popitem(last=False)
    return result


def _analysis_result(source: str, geometry) -> dict:
    lon, lat, t, v = query(source, geometry, polygon=True)
    cfg = SOURCES[source]
    return {
        "name": source,
        "variable": cfg["variable"],
        "kind": "footprints",
        "units": cfg["units"],
        "count": int(v.size),
        "rows": footprint_statistics(t, v, by="year"),
    }


# ── Routes ──────────────────────────────────────────────────────────────


class TileRequest(BaseModel):
    source: str
    i: int = Field(..., ge=0, lt=int(360 / TILE_DEG))
    j: int = Field(..., ge=0, lt=int(180 / TILE_DEG))


class AnalysisRequest(BaseModel):
    source: str
    geometry: dict[str, Any]


def _source(name: str) -> str:
    if name not in SOURCES:
        raise HTTPException(404, f"Unknown source {name!r}")
    return name


@app.middleware("http")
async def no_store(request: Request, call_next):
    """Jobs and their results change; never let a browser reuse a poll."""
    response = await call_next(request)
    if request.url.path != "/sources":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/sources")
def sources():
    return {
        "tile_deg": TILE_DEG,
        "max_analysis_deg2": MAX_ANALYSIS_DEG2,
        "sources": [
            {
                "id": k,
                **{
                    f: v[f]
                    for f in ("title", "quantity", "units", "colormap", "description")
                },
                "provider": v["provider"],
                "docs": DOCS[v["provider"]],
                "filters": v["filters"],
            }
            for k, v in SOURCES.items()
        ],
    }


@app.post("/tile")
def tile(request: TileRequest):
    source = _source(request.source)
    with _tiles_lock:
        cached = _tiles.get((source, request.i, request.j))
    if cached is not None:
        return {"status": "done", "result": cached}
    job = _submit(_tile_result, source, request.i, request.j)
    return {"status": job.status, "id": job.id}


@app.post("/analysis")
def analysis(request: AnalysisRequest):
    source = _source(request.source)
    try:
        geometry = shape(request.geometry)
    except Exception as exc:
        raise HTTPException(
            400, "Geometry must be a GeoJSON Polygon or MultiPolygon"
        ) from exc
    if geometry.geom_type not in ("Polygon", "MultiPolygon") or geometry.is_empty:
        raise HTTPException(400, "Geometry must be a GeoJSON Polygon or MultiPolygon")
    w, s, e, n = geometry.bounds
    if (e - w) * (n - s) > MAX_ANALYSIS_DEG2:
        raise HTTPException(
            413,
            f"The area spans {(e - w) * (n - s):.1f} square degrees; footprints are "
            f"limited to {MAX_ANALYSIS_DEG2:g}. Draw a smaller area.",
        )
    job = _submit(_analysis_result, source, geometry)
    return {"status": job.status, "id": job.id}


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown or expired job")
    return {
        "id": job.id,
        "status": job.status,
        "message": job.message,
        "result": job.result,
    }
