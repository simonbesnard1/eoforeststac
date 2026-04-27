from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Optional, Union

import numpy as np
import xarray as xr
import rioxarray  # noqa: F401

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR

# (variable_name, vrt_stem, description)
WANG_VARIABLES = [
    (
        "natural_forest_age",
        "natural",
        "Age of natural forests as of 2024, defined as years since the last disturbance "
        "detected in the Landsat CCDC time series (1985-2024). Forests undisturbed since "
        "before 1985 are assigned the maximum observable age (~39 years).",
    ),
    (
        "planted_forest_age",
        "planted",
        "Age of planted forests as of 2024, defined as years since the last disturbance "
        "detected in the Landsat CCDC time series (1985-2024).",
    ),
]

CITATION = (
    "Wang, Y., Wang, H., Liang, C., Li, X., Liu, Z., Zhang, X., Li, S., and Zhao, Y. "
    "2026. A global map of forest age for natural and planted forests at a fine spatial "
    "resolution of 30 meters. Earth System Science Data (preprint). "
    "https://doi.org/10.5194/essd-2025-674. "
    "Data: https://doi.org/10.17632/yfm4sw8h25.2"
)


class WangForestAgeWriter(BaseZarrWriter):
    """
    Writer for the Wang et al. Global 30m Forest Age product.

    Expects one VRT per forest type in a common directory:
      vrt_dir/
        natural.vrt   ← natural forest age
        planted.vrt   ← planted forest age

    Output is a single static Zarr store (no time dimension) with
    variables natural_forest_age and planted_forest_age.
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_variable(
        self,
        vrt_path: str,
        var_name: str,
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.DataArray:
        """Load one VRT as a named DataArray with dims (latitude, longitude)."""
        rio_chunks: Optional[Dict[str, int]] = None
        if chunks is not None:
            rio_chunks = {
                "x": chunks.get("longitude", chunks.get("x", "auto")),
                "y": chunks.get("latitude", chunks.get("y", "auto")),
            }

        da = rioxarray.open_rasterio(
            vrt_path,
            masked=True,
            chunks=rio_chunks if rio_chunks is not None else "auto",
            cache=False,
        )
        if "band" in da.dims and da.sizes.get("band", 1) == 1:
            da = da.isel(band=0, drop=True)

        # Tiles may be in mixed UTM projections — reproject to EPSG:4326
        da = da.rename({"y": "latitude", "x": "longitude"})
        return da.rename(var_name)

    # ------------------------------------------------------------------
    # Build dataset
    # ------------------------------------------------------------------
    def build_dataset(
        self,
        vrt_dir: str,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """Load natural and planted VRTs and merge into a single Dataset."""
        arrays = {}
        for var_name, stem, _ in WANG_VARIABLES:
            vrt_path = os.path.join(vrt_dir, f"{stem}.vrt")
            if not os.path.exists(vrt_path):
                raise FileNotFoundError(
                    f"Expected VRT not found for variable '{var_name}': {vrt_path}"
                )
            arrays[var_name] = self.load_variable(vrt_path, var_name, chunks=chunks)

        ds = xr.Dataset(arrays)

        # Add time dimension — age is as of 2024
        ds = ds.expand_dims(time=[np.datetime64("2024-01-01", "ns")])

        ds = self.set_crs(ds, crs=crs)
        return ds

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: Union[int, float] = -9999,
        crs: str = "EPSG:4326",
        version: str = "2.0",
        dtype: str = "int16",
    ) -> xr.Dataset:
        """Apply fill values, dtype, CRS, and CF metadata."""
        ds = self.set_crs(ds, crs=crs)
        ds = self.apply_fillvalue(ds, fill_value=fill_value)

        for var_name, _, description in WANG_VARIABLES:
            if var_name in ds:
                ds[var_name] = ds[var_name].astype(dtype)
                ds[var_name].attrs.update(
                    {
                        "long_name": description,
                        "units": "years",
                        "grid_mapping": "spatial_ref",
                        "valid_min": 0,
                        "valid_max": 200,
                        "_FillValue": fill_value,
                        "source": CITATION,
                    }
                )

        meta = {
            "title": f"Global 30m Forest Age Map v{version} – Wang et al.",
            "version": version,
            "institution": "China Agricultural University",
            "created_by": "Wang et al.",
            "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "description": (
                "Global 30m forest age for natural and planted forests derived from "
                "Landsat time-series CCDC change detection (1985–2024)."
            ),
            "spatial_resolution": "30 m",
            "temporal_coverage": "1985–2024 (static product)",
            "citation": CITATION,
            "spatial_ref": crs,
            "_FillValue": fill_value,
        }
        self.set_global_metadata(ds, meta)

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        vrt_dir: str,
        output_zarr: str,
        version: str = "2.0",
        fill_value: Union[int, float] = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Build dataset from per-variable VRTs and write to Zarr.

        Parameters
        ----------
        vrt_dir:
            Directory containing natural.vrt and planted.vrt.
        output_zarr:
            S3 or local path for the output Zarr store.
        version:
            Product version string (default "2.0").
        fill_value:
            Fill value applied to all variables.
        crs:
            CRS string (default EPSG:4326).
        chunks:
            Dask chunk sizes. Defaults to {"latitude": 500, "longitude": 500}.
        """
        if chunks is None:
            chunks = {"latitude": 500, "longitude": 500}

        print("Loading VRTs…")
        ds = self.build_dataset(vrt_dir=vrt_dir, crs=crs, chunks=chunks)

        print("Processing dataset…")
        ds = self.process_dataset(ds, fill_value=fill_value, crs=crs, version=version)

        encoding = {
            var: {
                "chunks": (1, chunks["latitude"], chunks["longitude"]),
                "compressor": DEFAULT_COMPRESSOR,
                "_FillValue": fill_value,
            }
            for var in ds.data_vars
        }

        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
