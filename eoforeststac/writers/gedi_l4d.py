from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

import numpy as np
import xarray as xr
import rioxarray  # noqa: F401

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR

# Ordered list of variables and their expected VRT filename stems.
# Each entry: (variable_name, vrt_stem, units, description)
GEDI_VARIABLES: List[tuple] = [
    ("rh10", "rh10", "m", "Relative height at 10th percentile"),
    ("rh20", "rh20", "m", "Relative height at 20th percentile"),
    ("rh30", "rh30", "m", "Relative height at 30th percentile"),
    ("rh40", "rh40", "m", "Relative height at 40th percentile"),
    ("rh50", "rh50", "m", "Relative height at 50th percentile (median)"),
    ("rh60", "rh60", "m", "Relative height at 60th percentile"),
    ("rh70", "rh70", "m", "Relative height at 70th percentile"),
    ("rh80", "rh80", "m", "Relative height at 80th percentile"),
    ("rh90", "rh90", "m", "Relative height at 90th percentile"),
    ("rh95", "rh95", "m", "Relative height at 95th percentile"),
    ("rh98", "rh98", "m", "Relative height at 98th percentile"),
]


class GEDIL4DWriter(BaseZarrWriter):
    """
    Writer for the GEDI L4D imputed forest structure product.

    Expects one VRT per variable in a common directory:
      vrt_dir/
        rh10.vrt, rh20.vrt, ..., rh98.vrt

    All VRTs must share the same grid (extent, resolution, CRS).
    Output is a single Zarr store with one variable per RH percentile
    plus canopy cover and AGBD (no time dimension — static product).
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
        # Map caller's lat/lon chunk keys to rioxarray's native x/y keys so
        # chunks are applied at read time and no rechunking is needed later.
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
        """Load all variable VRTs and merge into a single Dataset."""
        arrays = {}
        for var_name, stem, _, _ in GEDI_VARIABLES:
            vrt_path = os.path.join(vrt_dir, f"{stem}.vrt")
            if not os.path.exists(vrt_path):
                raise FileNotFoundError(
                    f"Expected VRT not found for variable '{var_name}': {vrt_path}"
                )
            arrays[var_name] = self.load_variable(vrt_path, var_name, chunks=chunks)

        ds = xr.Dataset(arrays)
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
        dtype: str = "float32",
    ) -> xr.Dataset:
        """Apply fill values, dtype, CRS, and CF metadata."""
        ds = self.set_crs(ds, crs=crs)
        ds = self.apply_fillvalue(ds, fill_value=fill_value)

        # Per-variable attrs
        for var_name, _, units, description in GEDI_VARIABLES:
            if var_name in ds:
                ds[var_name] = ds[var_name].astype(dtype)
                ds[var_name].attrs.update(
                    {
                        "long_name": description,
                        "units": units,
                        "grid_mapping": "spatial_ref",
                        "_FillValue": fill_value,
                        "source": (
                            "Seo, E., S.P. Healey, Z. Yang, R.O. Dubayah, T. De Conto, and J. Armston. "
                            "2025. GEDI L4D Imputed Waveforms, Version 2. ORNL DAAC, Oak Ridge, "
                            "Tennessee, USA. https://doi.org/10.3334/ORNLDAAC/2455"
                        ),
                    }
                )

        # Global metadata
        meta = {
            "title": f"GEDI L4D Imputed Forest Structure v{version}",
            "version": version,
            "institution": "NASA / ORNL DAAC",
            "created_by": "Seo et al.",
            "contact": "ORNL DAAC (https://daac.ornl.gov)",
            "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "description": (
                "Spatially complete 30-metre imputation of GEDI waveform-based forest structure "
                "metrics (RH percentiles, canopy cover, AGBD) using nearest-neighbour models "
                "trained on Landsat time series. Coverage: ±51.6° latitude."
            ),
            "spatial_resolution": "30 m",
            "temporal_coverage": "2019-04-18 to 2023-03-16",
            "citation": (
                "Seo, E., S.P. Healey, Z. Yang, R.O. Dubayah, T. De Conto, and J. Armston. "
                "2025. GEDI L4D Imputed Waveforms, Version 2. ORNL DAAC, Oak Ridge, "
                "Tennessee, USA. https://doi.org/10.3334/ORNLDAAC/2455"
            ),
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
            Directory containing one VRT per variable
            (rh10.vrt, …, rh98.vrt, cover.vrt, agbd.vrt).
        output_zarr:
            S3 or local path for the output Zarr store.
        version:
            Product version string (e.g. "2.0").
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
                "chunks": (chunks["latitude"], chunks["longitude"]),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }

        print("Writing Zarr…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
