"""
Spatio-temporal subsetting utilities for eoforeststac.

Assumptions
-----------
- Input geometries are ALWAYS provided in EPSG:4326
- Dataset CRS is inferred automatically
- Geometry is reprojected to dataset CRS internally

Design principles
-----------------
- Lazy by default (xarray / dask friendly)
- Explicit CRS logic, implicit user API
- Bounding-box first, masking optional
"""

from __future__ import annotations

from typing import Optional, Tuple
import warnings

import xarray as xr

try:
    import geopandas as gpd
    from shapely.geometry.base import BaseGeometry
except ImportError:  # optional dependency
    gpd = None
    BaseGeometry = None


# ---------------------------------------------------------------------
# CRS utilities
# ---------------------------------------------------------------------


def infer_dataset_crs(ds: xr.Dataset) -> str:
    """
    Infer CRS from an xarray Dataset.

    Precedence:
      1. rioxarray CRS
      2. CF grid-mapping variable (spatial_ref / crs)
      3. global attribute 'crs'

    Returns
    -------
    CRS string (e.g. 'EPSG:4326')

    Raises
    ------
    ValueError if CRS cannot be inferred.
    """
    # 1. rioxarray
    if hasattr(ds, "rio"):
        try:
            crs = ds.rio.crs
            if crs is not None:
                return crs.to_string()
        except Exception:
            pass

    # 2. CF grid mapping
    for name in ("spatial_ref", "crs"):
        if name in ds.variables:
            var = ds[name]
            wkt = var.attrs.get("crs_wkt") or var.attrs.get("spatial_ref")
            if wkt:
                return wkt

    # 3. global attribute fallback
    crs_attr = ds.attrs.get("crs")
    if crs_attr:
        return str(crs_attr)

    raise ValueError(
        "Could not infer dataset CRS. "
        "Dataset must define CRS via rioxarray, CF grid_mapping, or global 'crs' attribute."
    )


# ---------------------------------------------------------------------
# Coordinate utilities
# ---------------------------------------------------------------------


def _get_xy_names(
    ds: xr.Dataset,
    lon: Optional[str] = None,
    lat: Optional[str] = None,
) -> tuple[str, str]:
    """
    Infer horizontal coordinate names.
    """
    if lon and lat:
        return lon, lat

    for cand_lon, cand_lat in [
        ("longitude", "latitude"),
        ("lon", "lat"),
        ("x", "y"),
    ]:
        if cand_lon in ds.coords and cand_lat in ds.coords:
            return cand_lon, cand_lat

    raise ValueError(
        "Could not infer horizontal coordinates. " "Specify lon= and lat= explicitly."
    )


def _latitude_slice(lat_coord, miny, maxy):
    """
    Handle descending vs ascending latitude safely.
    """
    if lat_coord[0] > lat_coord[-1]:
        return slice(maxy, miny)
    return slice(miny, maxy)


# ---------------------------------------------------------------------
# Bounding-box subsetting
# ---------------------------------------------------------------------


def subset_bbox(
    ds: xr.Dataset,
    bbox: Tuple[float, float, float, float],
    *,
    lon: Optional[str] = None,
    lat: Optional[str] = None,
) -> xr.Dataset:
    """
    Subset dataset by bounding box (in dataset CRS).
    """
    minx, miny, maxx, maxy = bbox
    lon_name, lat_name = _get_xy_names(ds, lon, lat)

    lat_slice = _latitude_slice(ds[lat_name], miny, maxy)

    return ds.sel(
        {
            lon_name: slice(minx, maxx),
            lat_name: lat_slice,
        }
    )


# ---------------------------------------------------------------------
# Geometry-based subsetting
# ---------------------------------------------------------------------


def subset_geometry(
    ds: xr.Dataset,
    geometry,
    *,
    lon: Optional[str] = None,
    lat: Optional[str] = None,
    mask: bool = False,
) -> xr.Dataset:
    """
    Subset dataset using a geometry provided in EPSG:4326.

    Steps:
      1. Infer dataset CRS
      2. Reproject geometry → dataset CRS
      3. Bounding-box subset
      4. Optional exact mask
    """
    if gpd is None:
        raise ImportError("subset_geometry requires geopandas")

    # Normalize geometry input
    if hasattr(geometry, "geometry"):
        geom = geometry.geometry.unary_union
    else:
        geom = geometry

    # Infer dataset CRS
    ds_crs = infer_dataset_crs(ds)

    # Reproject geometry (INPUT IS ALWAYS EPSG:4326)
    geom_proj = gpd.GeoSeries([geom], crs="EPSG:4326").to_crs(ds_crs).iloc[0]

    # Bounding-box subset (cheap, lazy)
    ds = subset_bbox(ds, geom_proj.bounds, lon=lon, lat=lat)

    # Optional exact mask (expensive)
    if mask:
        if not hasattr(ds, "rio"):
            raise RuntimeError("Exact masking requires rioxarray-enabled Dataset")
        ds = ds.rio.clip([geom_proj], crs=ds_crs)

    return ds


# ---------------------------------------------------------------------
# Temporal subsetting
# ---------------------------------------------------------------------
def subset_time(
    ds: xr.Dataset,
    time: Optional[Tuple[str, str]] = None,
    *,
    time_dim: str = "time",
) -> xr.Dataset:
    """
    Subset dataset along time dimension.

    If the dataset has no time dimension and a time subset is requested,
    the dataset is returned unchanged with a warning.
    """
    if time is None:
        return ds

    if time_dim not in ds.dims:
        warnings.warn(
            f"Time subsetting requested, but dataset has no '{time_dim}' dimension. "
            f"Returning dataset unchanged. Available dimensions: {list(ds.dims)}",
            UserWarning,
        )
        return ds

    start, end = time
    return ds.sel({time_dim: slice(start, end)})


# ---------------------------------------------------------------------
# Convenience orchestration
# ---------------------------------------------------------------------


def subset(
    ds: xr.Dataset,
    *,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    geometry=None,
    time: Optional[Tuple[str, str]] = None,
    lon: Optional[str] = None,
    lat: Optional[str] = None,
    mask: bool = False,
) -> xr.Dataset:
    """
    Combined spatial + temporal subsetting.

    Notes
    -----
    - Geometry is assumed to be in EPSG:4326
    - CRS handling is automatic
    """
    if bbox is not None:
        ds = subset_bbox(ds, bbox, lon=lon, lat=lat)

    if geometry is not None:
        ds = subset_geometry(ds, geometry, lon=lon, lat=lat, mask=mask)

    if time is not None:
        ds = subset_time(ds, time=time)

    return ds
