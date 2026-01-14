# eoforeststac/writers/potapov_height.py

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Optional, Union, List

import numpy as np
import xarray as xr
import rioxarray  # noqa: F401  (needed for .rio accessor)

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class PotapovHeightWriter(BaseZarrWriter):
    """
    Writer for Potapov canopy height product distributed as one VRT per reference year.

    Input layout (example):
      /path/to/vrt_dir/
        2000.vrt
        2005.vrt
        2010.vrt
        2015.vrt
        2020.vrt

    Output:
      single Zarr with variable 'canopy_height' and dimension (time, latitude, longitude)
    """
    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(self, vrt_path: str) -> xr.DataArray:
        """
        Load one VRT lazily as a DataArray with dims (y, x).
        """
        da = rioxarray.open_rasterio(
            vrt_path,
            masked=True,          # nodata -> NaN where possible
            chunks="auto",        # lazy dask chunks
            cache=False,
        )

        # Usually comes as (band, y, x). Squeeze band away if single-band.
        if "band" in da.dims and da.sizes.get("band", 1) == 1:
            da = da.isel(band=0, drop=True)

        # Standardize dim names; rioxarray uses y/x
        da = da.rename({"y": "latitude", "x": "longitude"})

        return da

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def build_time_stack(
        self,
        vrt_files: Dict[int, str],
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None
    ) -> xr.Dataset:
        """
        Load and stack VRTs across years into a Dataset with time dimension.
        """
        # Determine years order
        years = [2000, 2005, 2010, 2015, 2020]
        if not years:
            raise ValueError("No years provided / found for VRT stacking.")

        # Load first as reference grid
        ref = self.load_dataset(vrt_files[years[0]])
        ref = self.set_crs(ref.to_dataset(name='canopy_height'), crs=crs)['canopy_height']

        arrays: List[xr.DataArray] = []
        for y in years:
            da = self.load_dataset(vrt_files[y])

            # Enforce CRS in metadata (data may already be in the VRT)
            da = da.rio.write_crs(crs, inplace=False)

            # Attach time coordinate for stacking
            da = da.expand_dims(time=[np.datetime64(f"{y}-01-01")])

            arrays.append(da)

        stacked = xr.concat(arrays, dim="time")

        # Chunking (optional override)
        if chunks is not None:
            stacked = stacked.chunk(chunks)

        ds = stacked.to_dataset(name="canopy_height")

        return ds

    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: Union[int, float] = -9999,
        crs: str = "EPSG:4326",
        version: str = "1.0",
        dtype: str = "float32",
        clamp_min: Optional[float] = 0.0,
    ) -> xr.Dataset:
        """
        Apply conventions, fill values, dtype, and metadata.
        """
        # Ensure CRS variable exists as in your other products
        ds = self.set_crs(ds, crs=crs)

        # Replace zeros with NaN if product uses 0 as "no data" (optional)
        # Only do this if you're sure; otherwise comment it out.
        ds["canopy_height"] = ds["canopy_height"].where(ds["canopy_height"] != 0)

        # Clamp physically impossible negatives (optional)
        if clamp_min is not None:
            ds["canopy_height"] = ds["canopy_height"].where(ds["canopy_height"] >= clamp_min)

        # Apply fill value (turn NaN -> fill_value) and dtype
        ds = self.apply_fillvalue(ds, fill_value=fill_value)
        ds["canopy_height"] = ds["canopy_height"].astype(dtype)

        # Variable attrs (CF-ish)
        ds["canopy_height"].attrs.update({
            "long_name": "Canopy height",
            "description": "Canopy top height for discrete reference years (stacked from annual/epoch VRTs).",
            "units": "m",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
            "valid_min": 0.0 if clamp_min is not None else None,
            "source": "Potapov et al., University of Maryland / GLAD",
        })
        # Remove None attrs to keep metadata clean
        ds["canopy_height"].attrs = {k: v for k, v in ds["canopy_height"].attrs.items() if v is not None}

        # Global metadata
        meta = {
            "title": "Global Canopy Height (Potapov et al.)",
            "version": version,
            "product_name": "Global Canopy Height",
            "institution": "University of Maryland / GLAD",
            "created_by": "Potapov et al.",
            "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "spatial_resolution": "30m",
            "crs": crs,
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
        version: str = "1.0",
        fill_value: Union[int, float] = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Build a time stack from VRTs and write to Zarr.
        """
        # Discover vrt files
        yrs = [2000, 2005, 2010, 2015, 2020]
        if yrs is None:
            # auto-discover *.vrt files with year stem
            vrt_files = {}
            for fn in os.listdir(vrt_dir):
                if not fn.endswith(".vrt"):
                    continue
                stem = os.path.splitext(fn)[0]
                if stem.isdigit():
                    vrt_files[int(stem)] = os.path.join(vrt_dir, fn)
            if not vrt_files:
                raise FileNotFoundError(f"No year-named .vrt files found in {vrt_dir}")
        else:
            vrt_files = {int(y): os.path.join(vrt_dir, f"{int(y)}.vrt") for y in yrs}
            missing = [y for y, p in vrt_files.items() if not os.path.exists(p)]
            if missing:
                raise FileNotFoundError(f"Missing VRT files for years: {missing}")

        print("Loading and stacking VRTs…")
        ds = self.build_time_stack(
            vrt_files=vrt_files,
            crs=crs,
            chunks=chunks
        )

        print("Processing dataset…")
        ds = self.process_dataset(
            ds,
            fill_value=fill_value,
            crs=crs,
            version=version,
        )

        # Encoding: derive from actual dask chunks
        encoding = {
               var: {
                   "chunks": (
                       chunks["time"],
                       chunks["latitude"],
                       chunks["longitude"],
                   ),
                   "compressor": DEFAULT_COMPRESSOR,
               }
               for var in ds.data_vars
           }

        print("Writing Zarr…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
