"""Area-weighted statistics of a gridded product over a region.

The explorer's Analysis tab and notebooks share this module, so both report
the same numbers. It depends only on numpy, xarray, dask, rasterio and pyproj
(no STAC or S3 stack), so the tile server can import it without the rest of
the package.

Each variable is analysed according to its *kind*, declared per product in
the catalog (``eoforeststac:analytics`` on the collection):

``density``
    A quantity per unit area, e.g. biomass in Mg ha-1. Per step, the total is
    sum(value x pixel area) and the mean is the total over the valid area.

Pixel areas are exact on geographic grids (they shrink with latitude) and
taken from the resolution on projected grids, which is exact for equal-area
projections and within a fraction of a percent for UTM/transverse Mercator
national grids.

Example
-------
>>> from eoforeststac.providers.zarr import ZarrProvider
>>> from eoforeststac.analytics import region_statistics
>>> da = ZarrProvider(CATALOG_URL).open_dataset("CCI_BIOMASS", "7.0")["aboveground_biomass"]
>>> rows = region_statistics(da, geometry)       # geometry: GeoJSON in EPSG:4326
>>> rows[0]   # {'time': '2007-01-01', 'mean': 112.3, 'total': 4.1e8, ...}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import dask.array as dsa
import numpy as np
import rasterio.features
import xarray as xr
from affine import Affine
from pyproj import CRS, Geod
from rasterio.warp import transform_geom

WGS84 = CRS.from_epsg(4326)
# WGS84 ellipsoid: semi-major axis, first eccentricity, b^2
_A = 6_378_137.0
_E = np.sqrt((2 - 1 / 298.257223563) / 298.257223563)
_B2 = _A**2 * (1 - _E**2)
KINDS = ("density",)

_X_NAMES = ("x", "lon", "longitude")
_Y_NAMES = ("y", "lat", "latitude")


# ── Grid helpers ────────────────────────────────────────────────────────


def spatial_dims(da: xr.DataArray) -> Tuple[str, str]:
    """Return the (y, x) dimension names of a gridded DataArray."""
    y = next((d for d in _Y_NAMES if d in da.dims), None)
    x = next((d for d in _X_NAMES if d in da.dims), None)
    if y is None or x is None:
        raise ValueError(f"No spatial dimensions in {list(da.dims)}")
    return y, x


def _resolution(coord: np.ndarray) -> float:
    if coord.size < 2:
        raise ValueError("Need at least two coordinates to infer the resolution")
    return float(coord[1] - coord[0])


def pixel_area_ha(da: xr.DataArray, crs: Any) -> xr.DataArray:
    """
    Area of each pixel in hectares, broadcastable against ``da``.

    Geographic grids: the exact area on the WGS84 ellipsoid of a cell between
    latitudes p1 and p2 that is dlon wide, (b^2 / 2) * dlon * |g(p2) - g(p1)|
    with g(p) = sin p / (1 - e^2 sin^2 p) + atanh(e sin p) / e (radians); this
    matches geodesic polygon areas (a sphere is ~0.4 % off at 52 deg N).
    Projected grids: |dx * dy|. Web Mercator is refused: its pixel areas are
    not meaningful.
    """
    crs = CRS.from_user_input(crs)
    y, x = spatial_dims(da)
    ys, xs = da[y].values, da[x].values
    dy, dx = _resolution(ys), _resolution(xs)
    if crs.is_geographic:
        rows = (
            (_B2 / 2)
            * np.radians(abs(dx))
            * np.abs(_zone(ys + dy / 2) - _zone(ys - dy / 2))
        )
        return xr.DataArray(rows / 1e4, dims=(y,), coords={y: da[y]})
    if crs.to_epsg() in (3857, 900913):
        raise ValueError("Web Mercator pixel areas are not usable for statistics")
    return xr.DataArray(abs(dx * dy) / 1e4)


def _polygons(geometry: Dict[str, Any]) -> List[List[List[List[float]]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    return geometry["coordinates"]


def _zone(lat_deg: np.ndarray) -> np.ndarray:
    """g(p) of the ellipsoidal zone-area formula (see pixel_area_ha)."""
    s = np.sin(np.radians(np.clip(lat_deg, -90, 90)))
    return s / (1 - _E**2 * s**2) + np.arctanh(_E * s) / _E


def _densify(
    ring: Sequence[Sequence[float]], step_deg: float
) -> List[Tuple[float, float]]:
    """Insert points so no segment is longer than step_deg in lon or lat."""
    out: List[Tuple[float, float]] = []
    for (x0, y0), (x1, y1) in zip(ring[:-1], ring[1:]):
        n = max(1, int(np.ceil(max(abs(x1 - x0), abs(y1 - y0)) / step_deg)))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    out.append(tuple(ring[-1][:2]))
    return out


def geometry_area_ha(geometry: Dict[str, Any], step_deg: float = 0.05) -> float:
    """
    Area on the WGS84 ellipsoid of a GeoJSON (Multi)Polygon in EPSG:4326, in
    hectares, with edges taken as straight lines in lon/lat, i.e. as drawn on
    the map and as the pixel mask sees them. (A plain geodesic polygon joins
    vertices by great circles, which for a 25 x 18 degree box is 1.5 % larger.)
    """
    geod = Geod(ellps="WGS84")
    total = 0.0
    for rings in _polygons(geometry):
        for i, ring in enumerate(rings):
            lons, lats = zip(*_densify([p[:2] for p in ring], step_deg))
            area = abs(geod.polygon_area_perimeter(lons, lats)[0])
            total += area if i == 0 else -area  # later rings are holes
    return total / 1e4


# ── Clipping ────────────────────────────────────────────────────────────


def _bounds(geometry: Dict[str, Any]) -> Tuple[float, float, float, float]:
    coords = np.array(
        [p for poly in _polygons(geometry) for ring in poly for p in ring], dtype=float
    )
    return (
        coords[:, 0].min(),
        coords[:, 1].min(),
        coords[:, 0].max(),
        coords[:, 1].max(),
    )


def clip_to_geometry(
    da: xr.DataArray,
    geometry: Dict[str, Any],
    crs: Any,
    geometry_crs: Any = WGS84,
) -> Tuple[xr.DataArray, xr.DataArray]:
    """
    Cut ``da`` to the geometry's bounding box and rasterize the geometry.

    Returns (subset, mask): ``mask`` is a lazy boolean (y, x) array, True for
    pixels whose centre lies inside the geometry. Only coordinates are read.
    """
    if geometry.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError("Geometry must be a GeoJSON Polygon or MultiPolygon")
    crs = CRS.from_user_input(crs)
    geometry_crs = CRS.from_user_input(geometry_crs)
    if crs == geometry_crs:
        native = geometry
    else:
        try:
            native = transform_geom(geometry_crs.to_wkt(), crs.to_wkt(), geometry)
        except Exception as exc:  # e.g. GDAL refuses a region far outside the CRS
            raise ValueError("The area is outside this dataset") from exc
    minx, miny, maxx, maxy = _bounds(native)

    y, x = spatial_dims(da)
    xs, ys = da[x].values, da[y].values
    dx, dy = _resolution(xs), _resolution(ys)
    ix = np.nonzero((xs >= minx - abs(dx) / 2) & (xs <= maxx + abs(dx) / 2))[0]
    iy = np.nonzero((ys >= miny - abs(dy) / 2) & (ys <= maxy + abs(dy) / 2))[0]
    if ix.size == 0 or iy.size == 0:
        raise ValueError("The area is outside this dataset")
    sub = da.isel(
        {y: slice(int(iy[0]), int(iy[-1]) + 1), x: slice(int(ix[0]), int(ix[-1]) + 1)}
    )

    sx, sy = sub[x].values, sub[y].values
    chunks = sub.chunksizes if sub.chunks else {y: (sy.size,), x: (sx.size,)}
    template = dsa.zeros((sy.size, sx.size), chunks=(chunks[y], chunks[x]), dtype=bool)

    def block(_, block_info=None):
        (y0, y1), (x0, x1) = block_info[0]["array-location"]
        transform = Affine(dx, 0, sx[x0] - dx / 2, 0, dy, sy[y0] - dy / 2)
        return rasterio.features.geometry_mask(
            [native],
            out_shape=(y1 - y0, x1 - x0),
            transform=transform,
            invert=True,
            all_touched=False,  # pixel centres: all_touched would inflate areas
        )

    mask = xr.DataArray(
        dsa.map_blocks(block, template, dtype=bool),
        dims=(y, x),
        coords={y: sub[y], x: sub[x]},
    )
    return sub, mask


# ── Statistics ──────────────────────────────────────────────────────────


def _label(value: Any) -> Any:
    if isinstance(value, np.datetime64):
        return str(np.datetime_as_string(value, unit="D"))
    if isinstance(value, np.generic):
        return value.item()
    return value


def region_statistics(
    da: xr.DataArray,
    geometry: Dict[str, Any],
    kind: str = "density",
    crs: Optional[Any] = None,
    geometry_crs: Any = WGS84,
    compute: bool = True,
) -> List[Dict[str, Any]]:
    """
    Area-weighted statistics of ``da`` inside ``geometry``, per step of every
    non-spatial dimension (e.g. one row per year).

    Each row holds the step's coordinates and, for ``kind="density"``:

    - ``mean``: area-weighted mean over valid pixels (units of ``da``)
    - ``total``: sum of value x area (units of ``da`` x ha, e.g. Mg)
    - ``valid_area_ha``: area of valid (non-NaN) pixels inside the region
    - ``region_area_ha``: area of all pixels whose centre is in the region
    - ``coverage``: valid_area_ha / region_area_ha

    ``crs`` defaults to ``da.rio.crs``. With ``compute=False`` the dask
    arrays are returned unevaluated; compute them (e.g. with a progress
    callback) and pass the results to :func:`statistics_rows`.
    """
    if kind not in KINDS:
        raise ValueError(f"Unknown kind {kind!r}; expected one of {KINDS}")
    if crs is None:
        crs = getattr(da, "rio", None) and da.rio.crs
        if crs is None:
            raise ValueError("Pass crs=...: the DataArray has no CRS")

    sub, mask = clip_to_geometry(da, geometry, crs, geometry_crs)
    y, x = spatial_dims(sub)
    area = pixel_area_ha(sub, crs)

    inside = mask * area  # (y, x) hectares inside the region
    values = sub.astype("float64")
    # Undecoded integer stores keep their fill value; treat it as missing
    if np.issubdtype(sub.dtype, np.integer):
        for source in (sub.encoding, sub.attrs):
            fill = next(
                (
                    source[k]
                    for k in ("_FillValue", "missing_value", "nodata")
                    if source.get(k) is not None
                ),
                None,
            )
            if fill is not None:
                values = values.where(sub != fill)
                break
    valid = values.notnull() & mask
    parts = {
        "total": (values.fillna(0) * inside).sum((y, x)),
        "valid_area_ha": (valid * area).sum((y, x)),
        "region_area_ha": inside.sum((y, x)),
    }
    if not compute:
        return parts  # type: ignore[return-value]

    import dask

    total, valid_area, region_area = dask.compute(*parts.values())
    return statistics_rows(total, valid_area, region_area)


def statistics_rows(
    total: xr.DataArray, valid_area: xr.DataArray, region_area: Any
) -> List[Dict[str, Any]]:
    """Turn computed (total, valid_area, region_area) into one dict per step."""
    region = float(region_area)
    dims: Sequence[str] = total.dims
    rows = []
    for idx in np.ndindex(*total.shape) if dims else [()]:
        sel = dict(zip(dims, idx))
        t = float(total.isel(sel)) if dims else float(total)
        v = float(valid_area.isel(sel)) if dims else float(valid_area)
        row = {
            d: _label(total[d].values[i]) for d, i in sel.items() if d in total.coords
        }
        row.update(
            mean=t / v if v > 0 else None,
            total=t if v > 0 else None,
            valid_area_ha=v,
            region_area_ha=region,
            coverage=v / region if region > 0 else None,
        )
        rows.append(row)
    return rows
