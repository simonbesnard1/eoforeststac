# eoforeststac/analysis/align.py

from __future__ import annotations

from typing import Dict, Optional, Mapping

import xarray as xr

import rioxarray  # noqa
from rasterio.enums import Resampling

_RESAMPLING_MAP = {
    "nearest": Resampling.nearest,
    "bilinear": Resampling.bilinear,
    "cubic": Resampling.cubic,
    "cubic_spline": Resampling.cubic_spline,
    "lanczos": Resampling.lanczos,
    "average": Resampling.average,
    "mode": Resampling.mode,
    "max": Resampling.max,
    "min": Resampling.min,
    "med": Resampling.med,
    "q1": Resampling.q1,
    "q3": Resampling.q3,
    "sum": Resampling.sum,
    "rms": Resampling.rms,
}



# ---------------------------------------------------------------------
# CRS utilities
# ---------------------------------------------------------------------

def _infer_crs(obj) -> Optional[str]:
    """
    Infer CRS from xarray Dataset or DataArray.
    """
    if isinstance(obj, xr.DataArray):
        ds = obj.to_dataset(name="_tmp")
    elif isinstance(obj, xr.Dataset):
        ds = obj
    else:
        return None

    # 1. rioxarray (preferred)
    if hasattr(ds, "rio"):
        try:
            crs = ds.rio.crs
            if crs:
                return crs.to_string()
        except Exception:
            pass

    # 2. CF grid mapping variables
    for name in ("spatial_ref", "crs"):
        if name in ds.variables:
            var = ds[name]
            wkt = var.attrs.get("crs_wkt") or var.attrs.get("spatial_ref")
            if wkt:
                return wkt

    # 3. Fallback: global attribute
    crs_attr = ds.attrs.get("crs")
    if isinstance(crs_attr, str):
        return crs_attr

    return None


def _require_crs(ds, name: str) -> str:
    if not isinstance(ds, xr.Dataset):
        raise TypeError(
            f"DatasetAligner expected an xarray.Dataset for '{name}', "
            f"but received {type(ds)}.\n"
            "Make sure you pass a mapping of {name: xr.Dataset}."
        )

    crs = _infer_crs(ds)
    if crs is None:
        raise ValueError(
            f"Could not infer CRS for dataset '{name}'. "
            "Dataset must have either:\n"
            "  - rioxarray CRS\n"
            "  - a CF grid_mapping variable (crs or spatial_ref)"
        )
    return crs

def _infer_x_dim(da):
    for d in ("x", "longitude"):
        if d in da.dims:
            return d
    raise ValueError("Could not infer x dimension.")

def _infer_y_dim(da):
    for d in ("y", "latitude"):
        if d in da.dims:
            return d
    raise ValueError("Could not infer y dimension.")


# ---------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------

class DatasetAligner:
    """
    Align multiple xarray Datasets onto a common spatial grid.

    Design principles
    -----------------
    - Explicit reference grid (no silent guessing)
    - CRS-aware reprojection using rioxarray
    - Variable-specific resampling
    - Lazy (Dask-safe)
    """

    def __init__(
        self,
        *,
        target: Optional[str] = None,
        crs: Optional[str] = None,
        resolution: Optional[float | tuple[float, float]] = None,
        resampling: str | Mapping[str, str] = "nearest",
    ):
        """
        Parameters
        ----------
        target : str, optional
            Key of reference dataset (used as target grid).
        crs : str, optional
            Target CRS (e.g. "EPSG:3035").
        resolution : float or (xres, yres), optional
            Target resolution in CRS units.
        resampling : str or dict
            Resampling strategy per dataset key or a global default.
            Examples: "nearest", "average", "bilinear", "sum"
        """
        self.target_key = target
        self.target_crs = crs
        self.target_resolution = resolution
        self.resampling = resampling

        if target is None and crs is None:
            raise ValueError(
                "Either 'target' or 'crs' must be provided."
            )

    # -----------------------------------------------------------------
    # Core logic
    # -----------------------------------------------------------------

    def _resolve_target_grid(
        self,
        datasets: Dict[str, xr.Dataset],
    ):
        """
        Determine the full target grid definition:
          - CRS
          - affine transform
          - raster shape (height, width)
    
        This guarantees pixel-perfect alignment.
        """
        if self.target_key is not None:
            if self.target_key not in datasets:
                raise KeyError(
                    f"Target dataset '{self.target_key}' not found. "
                    f"Available datasets: {list(datasets)}"
                )
    
            ref = datasets[self.target_key]
    
            # --- CRS (required) ---
            crs = _require_crs(ref, self.target_key)
    
            # --- Spatial metadata (required) ---
            if not hasattr(ref, "rio"):
                raise ValueError(
                    f"Dataset '{self.target_key}' is not rioxarray-enabled."
                )
    
            try:
                transform = ref.rio.transform()
                shape = ref.rio.shape
            except Exception as exc:
                raise ValueError(
                    f"Failed to extract spatial grid from dataset '{self.target_key}'."
                ) from exc
    
        else:
            # User-defined grid (advanced use)
            if self.target_crs is None or self.target_transform is None or self.target_shape is None:
                raise ValueError(
                    "When no target dataset is provided, "
                    "target_crs, target_transform, and target_shape must be set."
                )
    
            crs = self.target_crs
            transform = self.target_transform
            shape = self.target_shape
    
        return crs, transform, shape



    def _get_resampling(self, key: str):
        method = self.resampling.get(key)

        if isinstance(method, Resampling):
            return method

        if isinstance(method, str):
            try:
                return _RESAMPLING_MAP[method.lower()]
            except KeyError:
                raise ValueError(
                    f"Invalid resampling method '{method}' for dataset '{key}'. "
                    f"Valid options are: {list(_RESAMPLING_MAP)}"
                )

        raise TypeError(
            f"Resampling for dataset '{key}' must be a string or "
            f"rasterio.enums.Resampling, got {type(method)}."
        )

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def align(
        self,
        datasets: Dict[str, xr.Dataset],
    ) -> xr.Dataset:
        """
        Align datasets onto a common grid and merge them.
    
        All outputs will share:
          - identical CRS
          - identical transform
          - identical shape
          - identical spatial dimension names
        """
        if not datasets:
            raise ValueError("No datasets provided for alignment.")
    
        target_crs, target_transform, target_shape = self._resolve_target_grid(datasets)
    
        aligned_datasets = []
    
        for key, ds in datasets.items():
            if not isinstance(ds, xr.Dataset):
                raise TypeError(
                    f"DatasetAligner expected an xarray.Dataset for '{key}', "
                    f"but received {type(ds)}."
                )
    
            ds_crs = _require_crs(ds, key)
            method = self._get_resampling(key)
    
            # --------------------------------------------------
            # Normalize CRS
            # --------------------------------------------------
            if ds_crs != target_crs:
                ds = ds.rio.write_crs(ds_crs, inplace=False)
    
            # --------------------------------------------------
            # Reproject VARIABLE BY VARIABLE
            # --------------------------------------------------
            reproj_vars = {}
    
            for var in ds.data_vars:
                da = ds[var]
    
                # ensure rioxarray spatial dims are set
                da = da.rio.set_spatial_dims(
                    x_dim=_infer_x_dim(da),
                    y_dim=_infer_y_dim(da),
                    inplace=False,
                )
    
                # enforce canonical order
                expected = tuple(d for d in ("time", da.rio.y_dim, da.rio.x_dim) if d in da.dims)
                da = da.transpose(*expected)
    
                da_reproj = da.rio.reproject(
                    target_crs,
                    transform=target_transform,
                    shape=target_shape,
                    resampling=method,
                )
    
                # rename spatial dims AFTER reprojection
                da_reproj = da_reproj.rename({
                    da_reproj.rio.x_dim: "longitude",
                    da_reproj.rio.y_dim: "latitude",
                })
    
                reproj_vars[var] = da_reproj
    
            # rebuild dataset cleanly
            ds_aligned = xr.Dataset(reproj_vars)
    
            # propagate CRS metadata once
            ds_aligned = ds_aligned.rio.write_crs(target_crs)
    
            aligned_datasets.append(ds_aligned)
    
        # --------------------------------------------------
        # Merge strictly (no silent broadcasting)
        # --------------------------------------------------
        try:
            return xr.merge(aligned_datasets, join="exact")
        except Exception as exc:
            raise RuntimeError(
                "Failed to merge aligned datasets.\n"
                "Likely causes:\n"
                "- incompatible time coordinates\n"
                "- inconsistent variable naming\n"
                "- failed reprojection on one dataset"
            ) from exc
    
