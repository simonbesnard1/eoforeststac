import xarray as xr
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Sequence, Optional, Dict

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR

class TMFWriter(BaseZarrWriter):
    """
    Writer for the Tropical Moist Forest (TMF) disturbance product.

    Assumes yearly GeoTIFF files, e.g.
      <input_dir>/<year>_tmf_disturb.tif
    """

    # ------------------------------------------------------------------
    # IO
    # ------------------------------------------------------------------
    def _open_year(
        self,
        input_dir: str,
        year: int,
        pattern: str,
    ) -> xr.DataArray:
        tif_path = Path(input_dir) / pattern.format(year=year)

        da = xr.open_dataarray(tif_path, engine="rasterio")  # (band?, y, x)
        if "band" in da.dims:
            da = da.isel(band=0, drop=True)

        da = da.rename("tmf_disturbance")
        da = da.assign_coords(time=np.datetime64(f"{year}-01-01"))
        da = da.expand_dims("time")

        return da

    def build_dataset(
        self,
        input_dir: str,
        years: Sequence[int],
        pattern: str = "{year}_tmf_disturb.tif",
    ) -> xr.Dataset:
        das = [
            self._open_year(input_dir, int(year), pattern)
            for year in years
        ]

        da = xr.concat(das, dim="time")
        ds = da.to_dataset(name="tmf_disturbance")
        return ds

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Apply fill values, CRS, coordinate harmonization,
        chunking, and metadata.
        """

        # --- Fill values + dtype ---
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int16")

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)

        # ------------------------------------------------------------------
        # Rename y/x → latitude/longitude
        # ------------------------------------------------------------------
        rename_dims = {}
        if "y" in ds.dims:
            rename_dims["y"] = "latitude"
        if "x" in ds.dims:
            rename_dims["x"] = "longitude"

        if rename_dims:
            ds = ds.rename(rename_dims)
            for old, new in rename_dims.items():
                if old in ds.coords:
                    ds = ds.rename({old: new})

        # --- Coordinate metadata ---
        if "latitude" in ds.coords:
            ds["latitude"].attrs.update({
                "long_name": "Latitude",
                "standard_name": "latitude",
                "units": "degrees_north",
                "axis": "Y",
            })

        if "longitude" in ds.coords:
            ds["longitude"].attrs.update({
                "long_name": "Longitude",
                "standard_name": "longitude",
                "units": "degrees_east",
                "axis": "X",
            })

        # --- Chunking ---
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --- Variable metadata ---
        ds["tmf_disturbance"].attrs.update({
            "long_name": "Tropical Moist Forest disturbance",
            "description": (
                "Annual disturbance class or mask from the "
                "Tropical Moist Forest (TMF) product."
            ),
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })

        # --- Global metadata ---
        meta = {
            "title": "Tropical Moist Forest (TMF) Disturbance",
            "product_name": "TMF Disturbance",
            "institution": "Joint Research Centre (JRC)",
            "created_by": "TMF consortium",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "spatial_resolution": "30 m / 90 m (native TMF)",
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
        input_dir: str,
        years: Sequence[int],
        output_zarr: str,
        pattern: str = "{year}_tmf_disturb.tif",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:

        if chunks is None:
            chunks = {
                "time": -1,
                "latitude": 1000,
                "longitude": 1000,
            }

        ds = self.build_dataset(
            input_dir=input_dir,
            years=years,
            pattern=pattern,
        )

        ds = self.process_dataset(
            ds,
            chunks=chunks,
        )

        # Zarr encoding derived from actual Dask chunks
        encoding = {
            var: {
                "chunks": ds[var].chunksize,
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }

        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
