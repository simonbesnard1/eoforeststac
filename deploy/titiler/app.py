"""Production wrapper around TiTiler Xarray for EOForestSTAC."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import anyio.to_thread
import httpx
import numpy as np
import rio_tiler.colormap


def _register_transparent_zero_colormaps() -> None:
    """Add '<name>_z' for every colormap: the same, with its lowest entry
    transparent. Biomass, height and cover stores hold 0 on treeless land and
    open water (CCI covers the oceans with 0); drawn in the ramp's palest
    colour they paint whole oceans. Must run before TiTiler is imported: its
    colormap_name parameter only accepts names known at that point.
    """
    registry = rio_tiler.colormap.cmap
    for name in list(registry.list()):
        if name.endswith("_z"):
            continue
        colors = dict(registry.get(name))
        colors[0] = (0, 0, 0, 0)
        registry.data[f"{name}_z"] = colors


_register_transparent_zero_colormaps()

from fastapi import HTTPException, Query, Request  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402
from titiler.xarray import io as xarray_io  # noqa: E402
from titiler.xarray.main import app  # noqa: E402

from analysis import create_router as create_analysis_router
from download import create_router


def _csv_env(name: str, default: str) -> frozenset[str]:
    return frozenset(
        value.strip().lower()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    )


ALLOWED_DATA_HOSTS = _csv_env("ALLOWED_DATA_HOSTS", "s3.gfz.de")
ALLOWED_PATH_PREFIXES = tuple(
    value.strip()
    for value in os.getenv(
        "ALLOWED_DATA_PATH_PREFIXES",
        "/dog.atlaseo-glm.eo-gridded-data/",
    ).split(",")
    if value.strip()
)
MAX_PROXY_BYTES = int(os.getenv("MAX_PROXY_BYTES", str(5 * 1024 * 1024)))
# Each tile read can hold a few hundred MB while it resamples, so cap how many
# run at once (anyio's default is 40) and let the rest queue.
MAX_READ_THREADS = int(os.getenv("MAX_READ_THREADS", "8"))
# titiler.xarray memoises open_zarr() without a bound, and every opened store
# keeps its coordinate indexes in memory (tens to hundreds of MB for global
# 10-30 m grids). Reset the memo once it holds this many datasets.
MAX_OPEN_DATASETS = int(os.getenv("MAX_OPEN_DATASETS", "12"))


@app.on_event("startup")
async def limit_read_concurrency() -> None:
    anyio.to_thread.current_default_thread_limiter().total_tokens = MAX_READ_THREADS


def _bound_dataset_cache() -> None:
    if xarray_io.open_zarr.cache_info().currsize > MAX_OPEN_DATASETS:
        xarray_io.open_zarr.cache_clear()


_titiler_get_variable = xarray_io.get_variable


def _trim_overlapping_longitudes(ds, variable: str):
    """Drop longitude columns outside [-180, 180] on grids spanning > 360 degrees.

    TiTiler maps longitudes > 180 to -180..180 and sorts, then derives the
    transform from the first coordinate and the spacing. On a grid that
    overlaps itself (SAATCHI runs -176.5..196.5, all-empty beyond 180) that
    breaks the regular spacing and shifts every pixel east (12.9 degrees for
    SAATCHI). Trimming first keeps the grid regular; 0..360 grids without
    overlap and projected grids are left to TiTiler.
    """
    da = ds[variable]
    x_dim = next((d for d in ("x", *xarray_io.X_DIM_NAMES) if d in da.dims), None)
    if x_dim is None or x_dim not in ds.coords or ds[x_dim].size < 2:
        return ds
    try:
        crs = da.rio.crs
    except Exception:  # unreadable grid mapping: treat as TiTiler does
        crs = None
    if crs is not None and not crs.is_geographic:
        return ds
    xs = ds[x_dim].values
    span = abs(float(xs[-1] - xs[0])) + abs(float(xs[1] - xs[0]))
    if span <= 360 + 1e-6 or (xs.min() >= -180 and xs.max() <= 180):
        return ds
    inside = np.nonzero((xs >= -180) & (xs <= 180))[0]
    return ds.isel({x_dim: slice(int(inside[0]), int(inside[-1]) + 1)})


def _avoid_unit_origin(ds, variable: str):
    """Nudge 1-degree grids by 1e-9 degrees so no window starts at exactly 0/0.

    A window of a 1-degree grid whose corner is at longitude 0, latitude 0
    has the transform (1, 0, 0, 0, -1, 0), which GDAL's warper (3.10, via
    rasterio) treats as ungeoreferenced: tiles there came back empty (GAMI
    age classes at 1 degree lost everything from 0-90 E south of the
    equator). The shift is far below any pixel, so nothing visibly moves.
    """
    da = ds[variable]
    x_dim = next((d for d in ("x", *xarray_io.X_DIM_NAMES) if d in da.dims), None)
    y_dim = next((d for d in ("y", *xarray_io.Y_DIM_NAMES) if d in da.dims), None)
    if not x_dim or not y_dim or x_dim not in ds.coords or y_dim not in ds.coords:
        return ds
    xs, ys = ds[x_dim].values, ds[y_dim].values
    if xs.size < 2 or ys.size < 2 or not np.issubdtype(xs.dtype, np.floating):
        return ds
    if not (
        np.isclose(abs(xs[1] - xs[0]), 1.0) and np.isclose(abs(ys[1] - ys[0]), 1.0)
    ):
        return ds
    return ds.assign_coords({x_dim: xs + 1e-9, y_dim: ys + 1e-9})


def get_variable(ds, variable, sel=None):
    ds = _avoid_unit_origin(_trim_overlapping_longitudes(ds, variable), variable)
    return _titiler_get_variable(ds, variable, sel=sel)


# Reader resolves get_variable from the module at call time.
xarray_io.get_variable = get_variable


def validate_remote_url(value: str) -> str:
    """Return an approved public data URL or raise an HTTP 400 response."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid data URL") from exc

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.hostname.lower() not in ALLOWED_DATA_HOSTS
        or not any(parsed.path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)
    ):
        raise HTTPException(status_code=400, detail="Data URL is not allowed")
    return value


@app.middleware("http")
async def restrict_dataset_urls(request: Request, call_next):
    """Prevent TiTiler's remote dataset argument from becoming an SSRF vector."""
    source_url = request.query_params.get("url")
    if source_url:
        try:
            validate_remote_url(source_url)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        _bound_dataset_cache()
    return await call_next(request)


@app.middleware("http")
async def no_store_for_jobs(request: Request, call_next):
    """
    Job status must never be cached. TiTiler marks every GET
    "public, max-age=3600", so browsers answered progress polls from cache
    and a running analysis or download looked frozen at its first poll.
    """
    response = await call_next(request)
    if request.url.path.startswith(("/analysis", "/download")):
        response.headers["Cache-Control"] = "no-store"
    return response


SPATIAL_DIMS = frozenset(["x", "y", *xarray_io.X_DIM_NAMES, *xarray_io.Y_DIM_NAMES])
MAX_DIM_LABELS = 1000


def _dim_label(value) -> str:
    if isinstance(value, np.datetime64):
        return str(np.datetime_as_string(value))
    value = value.item() if isinstance(value, np.generic) else value
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


@app.get("/dataset/dims", include_in_schema=False)
def dataset_dims(
    url: str = Query(..., description="Allowlisted Zarr store URL"),
    variable: str = Query(..., description="Variable name"),
):
    """List a variable's non-spatial dimensions and their coordinate labels.

    TiTiler's /info only handles 2-D/3-D arrays; for 4-D variables (e.g. GAMI's
    members x time) the browser needs these labels to pin all but one extra
    dimension with `sel`.
    """
    validate_remote_url(url)
    try:
        ds = xarray_io.open_zarr(url)
    except Exception as exc:
        raise HTTPException(
            status_code=404, detail="Dataset could not be opened"
        ) from exc
    if variable not in ds.data_vars:
        raise HTTPException(status_code=404, detail="Unknown variable")
    da = ds[variable]
    dims = []
    for name in da.dims:
        if name in SPATIAL_DIMS:
            continue
        size = int(da.sizes[name])
        values = (
            ds[name].values[:MAX_DIM_LABELS]
            if name in ds.coords
            else range(min(size, MAX_DIM_LABELS))
        )
        dims.append(
            {"name": name, "size": size, "values": [_dim_label(v) for v in values]}
        )
    return {"dims": dims}


app.include_router(create_router(validate_remote_url))
app.include_router(create_analysis_router(validate_remote_url))


@app.get("/proxy/fetch", include_in_schema=False)
async def proxy_catalog_json(
    url: str = Query(..., description="Allowlisted GFZ catalog URL"),
):
    """Fetch allowlisted catalog JSON for browsers that cannot access S3 directly."""
    validate_remote_url(url)
    timeout = httpx.Timeout(15.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        try:
            upstream = await client.get(url, headers={"Accept": "application/json"})
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502, detail="Catalog upstream is unavailable"
            ) from exc

    if upstream.is_redirect:
        raise HTTPException(
            status_code=502, detail="Catalog redirects are not permitted"
        )
    if upstream.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Catalog upstream returned {upstream.status_code}",
        )
    if len(upstream.content) > MAX_PROXY_BYTES:
        raise HTTPException(status_code=413, detail="Catalog response is too large")
    content_type = upstream.headers.get("content-type", "").lower()
    if "json" not in content_type:
        raise HTTPException(
            status_code=502, detail="Catalog upstream did not return JSON"
        )

    return Response(
        content=upstream.content,
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=300"},
    )
