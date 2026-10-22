"""Area-weighted statistics of a gridded product over a region.

The explorer's Analysis tab and notebooks share this module, so both report
the same numbers. It depends only on numpy, xarray, dask, rasterio and pyproj
(no STAC or S3 stack), so the tile server can import it without the rest of
the package.

Each variable is analysed according to its *kind*, declared per product in
the catalog (``eoforeststac:analytics`` on the collection):

``density`` amount per area (biomass, Mg ha-1): mean and total
``mean`` a property without a meaningful total (height, age): mean
``amount`` amount per pixel (kg): total and total per hectare
``cover`` share of each pixel (tree cover %): mean and equivalent area
``class_area`` categorical (land use, agents): area per class
``event_year`` year of an event (forest loss year): area per year

See :func:`region_statistics` for the fields of each.

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
import xarray as xr
from pyproj import CRS, Geod

# rasterio (and affine) are imported where grids are rasterized, so the
# footprint statistics also work where only the lidar readers are installed

WGS84 = CRS.from_epsg(4326)
# WGS84 ellipsoid: semi-major axis, first eccentricity, b^2
_A = 6_378_137.0
_E = np.sqrt((2 - 1 / 298.257223563) / 298.257223563)
_B2 = _A**2 * (1 - _E**2)
KINDS = ("density", "mean", "amount", "cover", "class_area", "event_year")

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


def pixel_area_ha(
    da: xr.DataArray, crs: Any, resolution: Optional[Tuple[float, float]] = None
) -> xr.DataArray:
    """
    Area of each pixel in hectares, broadcastable against ``da``.

    Geographic grids: the exact area on the WGS84 ellipsoid of a cell between
    latitudes p1 and p2 that is dlon wide, (b^2 / 2) * dlon * |g(p2) - g(p1)|
    with g(p) = sin p / (1 - e^2 sin^2 p) + atanh(e sin p) / e (radians); this
    matches geodesic polygon areas (a sphere is ~0.4 % off at 52 deg N).
    Projected grids: |dx * dy|. Web Mercator is refused: its pixel areas are
    not meaningful. ``resolution`` = (dy, dx) is for a subset too small to
    infer it from (e.g. one row of pixels).
    """
    crs = CRS.from_user_input(crs)
    y, x = spatial_dims(da)
    ys, xs = da[y].values, da[x].values
    dy, dx = resolution or (_resolution(ys), _resolution(xs))
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
    import rasterio.features
    from affine import Affine
    from rasterio.warp import transform_geom

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


def _masked_values(sub: xr.DataArray) -> xr.DataArray:
    """Values as float64 with the fill value (if still encoded) as NaN."""
    values = sub.astype("float64")
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
                return values.where(sub != fill)
    return values


def class_labels(da: xr.DataArray) -> Dict[int, str]:
    """
    Class values and labels from CF ``flag_values``/``flag_meanings`` or an
    explorer-style ``legend`` attribute ({value: label}).
    """
    attrs = da.attrs
    legend = attrs.get("legend")
    if isinstance(legend, str):
        import ast

        try:
            legend = ast.literal_eval(legend)
        except (ValueError, SyntaxError):
            legend = None
    if isinstance(legend, dict):
        return {int(k): str(v) for k, v in legend.items()}
    values = attrs.get("flag_values")
    if isinstance(values, str):
        import ast

        values = ast.literal_eval(values)
    if values is not None:
        meanings = str(attrs.get("flag_meanings", "")).split()
        return {
            int(v): (meanings[i].replace("_", " ") if i < len(meanings) else str(v))
            for i, v in enumerate(np.atleast_1d(values))
        }
    return {}


def _event_years(values: xr.DataArray, encoding: str) -> xr.DataArray:
    """Map event codes to calendar years (NaN where there is no event)."""
    if encoding == "year":
        return values.where(values > 0)
    if encoding == "yyddd":  # e.g. RADD: 23145 = 2023, day 145
        return (2000 + np.floor(values / 1000)).where(values > 0)
    raise ValueError(f"Unknown event encoding {encoding!r}")


def region_statistics(
    da: xr.DataArray,
    geometry: Dict[str, Any],
    kind: str = "density",
    crs: Optional[Any] = None,
    geometry_crs: Any = WGS84,
    compute: bool = True,
    classes: Optional[Dict[Any, str]] = None,
    exclude: Sequence[int] = (),
    years: Optional[Sequence[int]] = None,
    encoding: str = "year",
    scale: Optional[float] = None,
) -> Any:
    """
    Area-weighted statistics of ``da`` inside ``geometry``, one row per step
    of every non-spatial dimension (e.g. per year), and per class or year for
    the counting kinds.

    Kinds and the fields of each row (besides the step's coordinates):

    ``density`` (amount per area, e.g. Mg ha-1)
        ``mean``, ``total`` (value x area, e.g. Mg)
    ``mean`` (a property with no meaningful total, e.g. height, age)
        ``mean``
    ``amount`` (amount per pixel, e.g. kg)
        ``total`` (sum), ``mean`` (total per hectare)
    ``cover`` (share of each pixel, % or fraction; ``scale`` converts to a
    fraction and defaults from the units)
        ``mean`` (in the data's units), ``cover_area_ha`` (cover x area)
    ``class_area`` (categorical; ``classes`` {value: label}, default from the
    variable's attributes; values in ``exclude`` are skipped)
        ``class``, ``label``, ``area_ha``, ``share`` (of the region)
    ``event_year`` (the value is the year of an event; ``years`` = [first,
    last]; ``encoding`` "year" or "yyddd")
        ``year``, ``area_ha``, ``share`` (of the region)

    Every row also has ``valid_area_ha`` (pixels with data in the region),
    ``region_area_ha`` (all pixels whose centre is in the region) and
    ``coverage`` (their ratio). For products that store "no event" as missing
    (e.g. a loss year), valid area is the event area, so read ``share``
    rather than ``coverage``. ``crs`` defaults to ``da.rio.crs``.

    With ``compute=False`` the lazy parts are returned as a dict; compute it
    (e.g. with a progress callback) and pass it to :func:`statistics_rows`
    with the same ``kind``.
    """
    if kind not in KINDS:
        raise ValueError(f"Unknown kind {kind!r}; expected one of {KINDS}")
    if crs is None:
        crs = getattr(da, "rio", None) and da.rio.crs
        if crs is None:
            raise ValueError("Pass crs=...: the DataArray has no CRS")

    sub, mask = clip_to_geometry(da, geometry, crs, geometry_crs)
    y, x = spatial_dims(sub)
    resolution = (_resolution(da[y].values), _resolution(da[x].values))
    area = pixel_area_ha(sub, crs, resolution)
    inside = mask * area  # (y, x) hectares inside the region
    values = _masked_values(sub)
    valid = values.notnull() & mask
    parts: Dict[str, Any] = {
        "valid_area_ha": (valid * area).sum((y, x)),
        "region_area_ha": inside.sum((y, x)),
    }

    if kind in ("density", "mean"):
        parts["total"] = (values.fillna(0) * inside).sum((y, x))
    elif kind == "amount":
        parts["total"] = (values.fillna(0) * mask).sum((y, x))
    elif kind == "cover":
        if scale is None:
            units = str(sub.attrs.get("units", "")).strip().lower()
            scale = 0.01 if units in ("percent", "%", "pct") else 1.0
        parts["total"] = (values.fillna(0) * scale * inside).sum((y, x))
        parts["scale"] = scale
    else:  # class_area, event_year
        if kind == "event_year":
            if not years or len(years) != 2:
                raise ValueError("event_year needs years=[first, last]")
            values = _event_years(values, encoding)
            keys = list(range(int(years[0]), int(years[1]) + 1))
            dim, labels = "year", {k: str(k) for k in keys}
        else:
            labels = {int(k): str(v) for k, v in (classes or class_labels(sub)).items()}
            keys = [k for k in sorted(labels) if k not in set(exclude)]
            if not keys:
                raise ValueError("No classes: pass classes={value: label}")
            dim = "class"
        per_key = [((values == k) * inside).sum((y, x)) for k in keys]
        parts["area_ha"] = xr.concat(per_key, dim=dim).assign_coords({dim: keys})
        parts["labels"] = labels

    if not compute:
        return parts

    import dask

    lazy = {k: v for k, v in parts.items() if isinstance(v, xr.DataArray)}
    computed = dict(zip(lazy, dask.compute(*lazy.values())))
    return statistics_rows({**parts, **computed}, kind)


def statistics_rows(
    parts: Dict[str, Any], kind: str = "density"
) -> List[Dict[str, Any]]:
    """Turn computed parts of :func:`region_statistics` into one dict per row."""
    region = float(parts["region_area_ha"])
    if region <= 0:
        raise ValueError(
            "The area contains no pixel of this dataset; draw a larger area"
        )
    key = "area_ha" if "area_ha" in parts else "total"
    main = parts[key]
    valid_area = parts["valid_area_ha"]
    if isinstance(valid_area, xr.DataArray) and isinstance(main, xr.DataArray):
        main, valid_area = xr.broadcast(main, valid_area)
    dims: Sequence[str] = main.dims
    rows = []
    for idx in np.ndindex(*main.shape) if dims else [()]:
        sel = dict(zip(dims, idx))
        value = float(main.isel(sel)) if dims else float(main)
        v = float(valid_area.isel(sel)) if dims else float(valid_area)
        row: Dict[str, Any] = {
            d: _label(main[d].values[i]) for d, i in sel.items() if d in main.coords
        }
        has_data = v > 0
        if kind == "density":
            row.update(
                mean=value / v if has_data else None, total=value if has_data else None
            )
        elif kind == "mean":
            row.update(mean=value / v if has_data else None)
        elif kind == "amount":
            row.update(
                total=value if has_data else None, mean=value / v if has_data else None
            )
        elif kind == "cover":
            row.update(
                mean=value / v / parts["scale"] if has_data else None,
                cover_area_ha=value if has_data else None,
            )
        elif kind == "class_area":
            row.update(label=parts["labels"].get(row["class"], str(row["class"])))
            row.update(area_ha=value, share=value / region if region > 0 else None)
        elif kind == "event_year":
            row.update(area_ha=value, share=value / region if region > 0 else None)
        row.update(
            valid_area_ha=v,
            region_area_ha=region,
            coverage=v / region if region > 0 else None,
        )
        rows.append(row)
    return rows


# ── Footprints (GEDI, ICESat-2) ──────────────────────────────────────────


def footprint_statistics(
    times: Sequence[Any], values: Sequence[float], by: str = "year"
) -> List[Dict[str, Any]]:
    """
    Distribution of footprint values (lidar shots or segments) per year or
    month: ``count``, ``mean``, ``median``, ``p25``, ``p75``, ``min``, ``max``.

    Footprints are samples, not a wall-to-wall grid, so there is no area
    weighting and no total: report the distribution and the sample size.
    ``times`` are datetimes (anything numpy can parse); NaN values are dropped.
    """
    import pandas as pd

    if by not in ("year", "month"):
        raise ValueError("by must be 'year' or 'month'")
    frame = pd.DataFrame(
        {
            "time": pd.to_datetime(np.asarray(times)),
            "value": np.asarray(values, dtype="float64"),
        }
    ).dropna()
    if frame.empty:
        return []
    period = frame["time"].dt.to_period("Y" if by == "year" else "M")
    rows = []
    for key, group in frame.groupby(period)["value"]:
        v = group.to_numpy()
        rows.append(
            {
                "time": str(key.start_time.date()),
                "count": int(v.size),
                "mean": float(v.mean()),
                "median": float(np.median(v)),
                "p25": float(np.percentile(v, 25)),
                "p75": float(np.percentile(v, 75)),
                "min": float(v.min()),
                "max": float(v.max()),
            }
        )
    return rows
