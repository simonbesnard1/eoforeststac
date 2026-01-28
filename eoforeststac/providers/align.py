# eoforeststac/analysis/align.py
# Copyright (c) 2024–2025
# Licensed under the MIT License

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple, Union

import numpy as np
import xarray as xr
import rioxarray  # noqa: F401
from affine import Affine
from rasterio.enums import Resampling


# -----------------------------------------------------------------------------
# Resampling registry
# -----------------------------------------------------------------------------

_RESAMPLING_MAP: dict[str, Resampling] = {
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

# Coarsen aggregation methods, xcube-like
_COARSEN_AGG_METHODS = {
    "first",
    "min",
    "max",
    "mean",
    "median",
    "mode",
    "sum",
}


# -----------------------------------------------------------------------------
# Grid spec
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class GridSpec:
    """Immutable grid definition used as a spatial contract."""

    crs: str
    transform: Affine
    shape: Tuple[int, int]  # (height, width)
    x_dim: str = "longitude"
    y_dim: str = "latitude"

    @property
    def height(self) -> int:
        return int(self.shape[0])

    @property
    def width(self) -> int:
        return int(self.shape[1])

    @property
    def res(self) -> Tuple[float, float]:
        # Affine: a = xres, e = yres (negative for north-up rasters)
        return (float(self.transform.a), float(abs(self.transform.e)))

    def hash(self, ndigits: int = 9) -> str:
        """Stable-ish hash for caching / diagnostics (rounded floats)."""
        a, b, c, d, e, f = self.transform[:6]
        vals = (
            self.crs,
            int(self.height),
            int(self.width),
            round(float(a), ndigits),
            round(float(b), ndigits),
            round(float(c), ndigits),
            round(float(d), ndigits),
            round(float(e), ndigits),
            round(float(f), ndigits),
        )
        return "grid:" + str(abs(hash(vals)))


# -----------------------------------------------------------------------------
# CRS & dimension utilities
# -----------------------------------------------------------------------------


def _infer_crs(obj: xr.Dataset | xr.DataArray) -> Optional[str]:
    """Infer CRS from rioxarray or CF grid-mapping metadata."""
    if isinstance(obj, xr.DataArray):
        obj = obj.to_dataset(name="_tmp")

    if hasattr(obj, "rio"):
        try:
            crs = obj.rio.crs
            if crs:
                return crs.to_string()
        except Exception:
            pass

    for name in ("spatial_ref", "crs"):
        if name in obj.variables:
            var = obj[name]
            wkt = var.attrs.get("crs_wkt") or var.attrs.get("spatial_ref")
            if wkt:
                return wkt

    crs_attr = obj.attrs.get("crs")
    if isinstance(crs_attr, str):
        return crs_attr

    return None


def _require_crs(ds: xr.Dataset, name: str) -> str:
    if not isinstance(ds, xr.Dataset):
        raise TypeError(
            f"Expected an xarray.Dataset for '{name}', got {type(ds).__name__}"
        )
    crs = _infer_crs(ds)
    if crs is None:
        raise ValueError(
            f"Could not infer CRS for dataset '{name}'.\n"
            "Dataset must define a CRS via:\n"
            "  - rioxarray (.rio.crs)\n"
            "  - CF grid-mapping variable (crs / spatial_ref)"
        )
    return crs


def _infer_x_dim(da: xr.DataArray) -> str:
    for name in ("x", "longitude", "lon"):
        if name in da.dims:
            return name
    raise ValueError("Could not infer x-dimension name.")


def _infer_y_dim(da: xr.DataArray) -> str:
    for name in ("y", "latitude", "lat"):
        if name in da.dims:
            return name
    raise ValueError("Could not infer y-dimension name.")


def _parse_resampling(method: Union[str, Resampling], *, what: str) -> Resampling:
    if isinstance(method, Resampling):
        return method
    if isinstance(method, str):
        try:
            return _RESAMPLING_MAP[method.lower()]
        except KeyError:
            raise ValueError(
                f"Invalid resampling method '{method}' for {what}. "
                f"Valid options: {sorted(_RESAMPLING_MAP)}"
            )
    raise TypeError(
        f"Invalid resampling method type for {what}: {type(method).__name__}"
    )


# -----------------------------------------------------------------------------
# Resolution snapping
# -----------------------------------------------------------------------------


def _snap_resolution(
    target_res: Tuple[float, float],
    src_res: Tuple[float, float],
    *,
    mode: str = "auto",
    tol: float = 1e-6,
) -> Tuple[float, float]:
    """
    Snap a requested target resolution to a 'nice' multiple of the source resolution.

    mode:
      - "off": return target_res unchanged
      - "auto": if target_res is within tol of k*src_res (k integer), snap to exact
      - "nearest_multiple": always snap to nearest integer multiple of src_res
    """
    if mode == "off":
        return target_res
    if mode not in {"auto", "nearest_multiple"}:
        raise ValueError("snap mode must be one of {'off','auto','nearest_multiple'}")

    def snap_one(t, s):
        if s <= 0:
            return t
        k = max(1, int(round(t / s)))
        snapped = k * s
        if mode == "nearest_multiple":
            return snapped
        # auto: only snap if close enough
        return snapped if abs(snapped - t) <= tol * max(1.0, abs(t)) else t

    return (snap_one(target_res[0], src_res[0]), snap_one(target_res[1], src_res[1]))


# -----------------------------------------------------------------------------
# Optional coarsening (fast-downsampling before reprojection)
# -----------------------------------------------------------------------------


def _coarsen_dataset(
    ds: xr.Dataset,
    *,
    x_dim: str,
    y_dim: str,
    factor: int,
    agg: Union[str, Mapping[str, str]] = "auto",
) -> xr.Dataset:
    """
    Coarsen spatial dims by integer factor prior to reprojection (xcube-style).
    Uses xarray.coarsen(boundary='pad', coord_func='min').

    agg:
      - "auto": integers -> "first", floats -> "mean"
      - str: one of _COARSEN_AGG_METHODS
      - mapping: per-variable aggregation method
    """
    if factor <= 1:
        return ds

    if isinstance(agg, str):
        agg_map: Mapping[str, str] = {"*": agg}
    else:
        agg_map = agg

    def pick_agg(var_name: str, da: xr.DataArray) -> str:
        method = None
        for pat, m in agg_map.items():
            if pat == var_name or (pat == "*" and method is None):
                method = m
        if method in (None, "auto"):
            return "first" if np.issubdtype(da.dtype, np.integer) else "mean"
        if method not in _COARSEN_AGG_METHODS:
            raise ValueError(
                f"Invalid coarsen agg '{method}' for variable '{var_name}'. "
                f"Valid options: {sorted(_COARSEN_AGG_METHODS)}"
            )
        return method

    out_vars = {}
    new_coords = None

    for name, da in ds.data_vars.items():
        if x_dim in da.dims or y_dim in da.dims:
            dim = {}
            if y_dim in da.dims:
                dim[y_dim] = factor
            if x_dim in da.dims:
                dim[x_dim] = factor

            co = da.coarsen(dim=dim, boundary="pad", coord_func="min")
            method = pick_agg(name, da)

            if method == "mode":
                # xarray has no builtin mode reducer; use apply_ufunc on blocks
                def _mode_np(x, axis=-1):
                    # flatten along coarsen reduction dims handled by coarsen.reduce, so axis provided
                    # simple, robust-ish fallback: nan-safe mode using unique counts
                    x = np.asarray(x)
                    x = x[~np.isnan(x)] if np.issubdtype(x.dtype, np.floating) else x
                    if x.size == 0:
                        return np.nan
                    vals, counts = np.unique(x, return_counts=True)
                    return vals[np.argmax(counts)]

                da2 = co.reduce(_mode_np)
            else:
                da2 = getattr(co, method)()

            if da2.dtype != da.dtype:
                da2 = da2.astype(da.dtype)

            da2.attrs.update(da.attrs)
            da2.encoding.update(da.encoding)

            if new_coords is None:
                new_coords = dict(da2.coords)
            else:
                new_coords.update(da2.coords)

            out_vars[name] = da2
        else:
            out_vars[name] = da

    out = xr.Dataset(out_vars, attrs=ds.attrs)

    if new_coords:
        out = xr.Dataset(
            {
                k: v.assign_coords(
                    {d: new_coords[d] for d in v.dims if d in new_coords}
                )
                for k, v in out.data_vars.items()
            },
            attrs=out.attrs,
        )

    # Re-attach CRS if present
    if ds.rio.crs:
        out = out.rio.write_crs(ds.rio.crs, inplace=False)

    return out


# -----------------------------------------------------------------------------
# Dataset aligner
# -----------------------------------------------------------------------------

ResamplingSpec = Union[str, Mapping[str, Union[str, Mapping[str, str]]]]


class DatasetAligner:
    """
    Align multiple xarray Datasets onto a common spatial grid.

    Features
    --------
    - GridSpec contract (CRS + transform + shape + hash)
    - Automatic resolution snapping (optional)
    - Per-dataset and per-variable resampling overrides
    - Optional coarsening before reprojection (fast-downsample)
    - Strict merge semantics
    """

    def __init__(
        self,
        *,
        target: Optional[str] = None,
        crs: Optional[str] = None,
        resolution: Optional[float | Tuple[float, float]] = None,
        resampling: Union[str, Mapping[str, Union[str, Mapping[str, str]]]] = "nearest",
        snap_resolution: str = "auto",
        snap_tolerance: float = 1e-6,
        coarsen_factor: int = 1,
        coarsen_agg: Union[str, Mapping[str, str]] = "auto",
        canonical_spatial_dims: Tuple[str, str] = ("longitude", "latitude"),
    ):
        if target is None and crs is None:
            raise ValueError("Either 'target' or 'crs' must be provided.")

        self.target_key = target
        self.target_crs = crs
        self.target_resolution = resolution

        self.resampling = resampling

        self.snap_resolution_mode = snap_resolution
        self.snap_tolerance = snap_tolerance

        self.coarsen_factor = int(coarsen_factor)
        self.coarsen_agg = coarsen_agg

        self.x_out, self.y_out = canonical_spatial_dims

        # Cached for diagnostics / reuse
        self._grid: Optional[GridSpec] = None

    # -------------------------------------------------------------------------
    # Target grid resolution
    # -------------------------------------------------------------------------

    def _resolve_target_grid(self, datasets: Dict[str, xr.Dataset]) -> GridSpec:
        if self.target_key is None:
            raise NotImplementedError(
                "Explicit grid definition without a reference dataset "
                "is not implemented yet."
            )

        if self.target_key not in datasets:
            raise KeyError(
                f"Target dataset '{self.target_key}' not found. "
                f"Available datasets: {list(datasets)}"
            )

        ref = datasets[self.target_key]
        crs = _require_crs(ref, self.target_key)

        if not hasattr(ref, "rio"):
            raise ValueError(f"Dataset '{self.target_key}' is not rioxarray-enabled.")

        try:
            transform = Affine(*ref.rio.transform()[:6])
            shape = tuple(ref.rio.shape)  # (height, width)
        except Exception as exc:
            raise ValueError(
                f"Failed to extract spatial grid from '{self.target_key}'."
            ) from exc

        # Optional override of CRS
        if self.target_crs is not None:
            crs = self.target_crs

        # Optional override of resolution: rebuild transform and shape
        if self.target_resolution is not None:
            # Normalize resolution spec
            if isinstance(self.target_resolution, (int, float)):
                req_res = (float(self.target_resolution), float(self.target_resolution))
            else:
                req_res = (
                    float(self.target_resolution[0]),
                    float(self.target_resolution[1]),
                )

            # Snap requested resolution to ref resolution if desired
            ref_res = (float(transform.a), float(abs(transform.e)))
            req_res = _snap_resolution(
                req_res,
                ref_res,
                mode=self.snap_resolution_mode,
                tol=self.snap_tolerance,
            )

            # Keep same extent as reference grid; recompute width/height
            # Extent from affine + shape
            x0, y0 = transform.c, transform.f
            x1 = x0 + transform.a * shape[1]
            y1 = y0 + transform.e * shape[0]

            width = int(round(abs((x1 - x0) / req_res[0])))
            height = int(round(abs((y1 - y0) / req_res[1])))
            width = max(2, width)
            height = max(2, height)

            # North-up assumption: e negative
            new_transform = Affine(req_res[0], 0.0, x0, 0.0, -req_res[1], y0)
            transform = new_transform
            shape = (height, width)

        grid = GridSpec(
            crs=crs,
            transform=transform,
            shape=(int(shape[0]), int(shape[1])),
            x_dim=self.x_out,
            y_dim=self.y_out,
        )
        self._grid = grid
        return grid

    @property
    def grid(self) -> Optional[GridSpec]:
        """The last resolved target GridSpec (after calling align())."""
        return self._grid

    # -------------------------------------------------------------------------
    # Resampling resolution
    # -------------------------------------------------------------------------

    def _get_dataset_resampling(
        self, key: str
    ) -> Tuple[Resampling, Mapping[str, Resampling]]:
        """
        Returns:
          (dataset_default, per_variable_overrides)
        """
        per_var: dict[str, Resampling] = {}

        if isinstance(self.resampling, str):
            return _parse_resampling(self.resampling, what=f"dataset '{key}'"), per_var

        if not isinstance(self.resampling, Mapping):
            raise TypeError("resampling must be a string or a mapping")

        spec = self.resampling.get(key, "nearest")

        # dataset-level string or enum
        if isinstance(spec, (str, Resampling)):
            return _parse_resampling(spec, what=f"dataset '{key}'"), per_var

        # dataset-level dict like {"default": "average", "vars": {"biomass": "bilinear"}}
        if isinstance(spec, Mapping):
            default = spec.get("default", "nearest")
            vars_map = spec.get("vars", {})
            default_r = _parse_resampling(default, what=f"dataset '{key}' default")

            if not isinstance(vars_map, Mapping):
                raise TypeError(f"resampling['{key}']['vars'] must be a mapping")

            for vname, vmethod in vars_map.items():
                per_var[str(vname)] = _parse_resampling(vmethod, what=f"{key}.{vname}")

            return default_r, per_var

        raise TypeError(f"Invalid resampling spec for dataset '{key}': {spec!r}")

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def align(self, datasets: Dict[str, xr.Dataset]) -> xr.Dataset:
        if not datasets:
            raise ValueError("No datasets provided for alignment.")

        grid = self._resolve_target_grid(datasets)

        aligned: list[xr.Dataset] = []

        for key, ds in datasets.items():

            if not isinstance(ds, xr.Dataset):
                raise TypeError(
                    f"Expected xr.Dataset for '{key}', got {type(ds).__name__}"
                )

            ds_crs = _require_crs(ds, key)

            if not ds.rio.crs:
                ds = ds.rio.write_crs(ds_crs, inplace=False)

            # infer spatial dims once
            sample = next(iter(ds.data_vars.values()))
            x_dim = _infer_x_dim(sample)
            y_dim = _infer_y_dim(sample)
            ds = ds.rio.set_spatial_dims(x_dim=x_dim, y_dim=y_dim, inplace=False)

            # Ensure CRS is written on every spatial variable
            for name, da in ds.data_vars.items():
                if da.rio.crs is None:
                    ds[name] = da.rio.write_crs(ds.rio.crs, inplace=False)

            # optional pre-coarsening (fast downsample)
            if self.coarsen_factor and self.coarsen_factor > 1:
                ds = _coarsen_dataset(
                    ds,
                    x_dim=x_dim,
                    y_dim=y_dim,
                    factor=self.coarsen_factor,
                    agg=self.coarsen_agg,
                )

            # resampling: dataset default + per-variable overrides
            ds_default_resampling, per_var = self._get_dataset_resampling(key)

            # 1) reproject dataset with default resampling
            ds_reproj = ds.rio.reproject(
                grid.crs,
                transform=grid.transform,
                shape=grid.shape,
                resampling=ds_default_resampling,
            )

            # 2) optionally override some variables with different resampling
            # (reproject only those variables and then replace)
            if per_var:
                for var_name, var_resampling in per_var.items():
                    if var_name not in ds.data_vars:
                        continue
                    da = ds[var_name]
                    da_reproj = da.rio.reproject(
                        grid.crs,
                        transform=grid.transform,
                        shape=grid.shape,
                        resampling=var_resampling,
                    )
                    ds_reproj[var_name] = da_reproj

            # canonical naming
            ds_reproj = ds_reproj.rename(
                {
                    ds_reproj.rio.x_dim: grid.x_dim,
                    ds_reproj.rio.y_dim: grid.y_dim,
                }
            )

            ds_reproj = ds_reproj.rio.write_crs(grid.crs)
            aligned.append(ds_reproj)

        return xr.merge(aligned, compat="no_conflicts")
