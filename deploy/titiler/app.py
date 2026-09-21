"""Production wrapper around TiTiler Xarray for EOForestSTAC."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, Query, Request
from fastapi.responses import Response
from starlette.responses import JSONResponse
from titiler.xarray.main import app


def _csv_env(name: str, default: str) -> frozenset[str]:
    return frozenset(
        value.strip().lower()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    )


ALLOWED_DATA_HOSTS = _csv_env("ALLOWED_DATA_HOSTS", "s3.gfz-potsdam.de")
ALLOWED_PATH_PREFIXES = tuple(
    value.strip()
    for value in os.getenv(
        "ALLOWED_DATA_PATH_PREFIXES",
        "/dog.atlaseo-glm.eo-gridded-data/",
    ).split(",")
    if value.strip()
)
MAX_PROXY_BYTES = int(os.getenv("MAX_PROXY_BYTES", str(5 * 1024 * 1024)))


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
    return await call_next(request)


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
