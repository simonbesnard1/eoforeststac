import xarray as xr
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Sequence

from eoforeststac.writers.base import BaseZarrWriter


class TMFWriter(BaseZarrWriter):
    """
    Writer for TMF (Tropical Moist Forest) product.

    Assumes yearly GeoTIFF files, e.g.
      <input_dir>/<year>_tmf_disturb.tif

    You can easily adapt the file pattern in _open_year().
    """

    def _open_year(self, input_dir: str, year: int, pattern: str) -> xr.DataArray:
        """
        Open a single year's disturbance GeoTIFF as a DataArray.
        pattern should contain '{year}'.
        """
        tif_path = Path(input_dir) / pattern.format(year=year)
        da = xr.open_dataarray(tif_path, engine="rasterio")  # (band, y, x)
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

    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
    ) -> xr.Dataset:
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int16")
        ds = self.set_crs(ds, crs=crs)

        ds["tmf_disturbance"].attrs.update({
            "long_name": "TMF disturbance class",
            "description": "Disturbance class or mask from the TMF product.",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })

        self.set_global_metadata(ds, {
            "product_name": "Tropical Moist Forest (TMF) Disturbance",
            "created_by": "eoforeststac",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "_FillValue": fill_value,
        })

        return ds

    def write(
        self,
        input_dir: str,
        years: Sequence[int],
        output_zarr: str,
        pattern: str = "{year}_tmf_disturb.tif",
        chunks: dict | None = None,
    ) -> str:
        # Build + process
        ds = self.build_dataset(input_dir=input_dir, years=years, pattern=pattern)
        ds = self.process_dataset(ds)

        if chunks is None:
            chunks = {"time": -1, "y": 1000, "x": 1000}

        ds = ds.chunk(chunks)

        encoding = {
            var: {"chunks": (chunks["time"], chunks["y"], chunks["x"])}
            for var in ds.data_vars
        }

        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
