import xarray as xr
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Sequence

from eoforeststac.writers.base import BaseZarrWriter


class EFDAWriter(BaseZarrWriter):
    """
    Writer for the European Forest Disturbance Atlas (EFDA).

    Assumes:
      - yearly disturbance mosaic GeoTIFFs
      - yearly disturbance agent GeoTIFFs

    Default filename patterns follow your EFDA naming:
      <year>_disturb_mosaic_v211_22_epsg3035.tif
      <year>_disturb_agent_v211_reclass_compv211_epsg3035.tif
    """

    def _open_year_mosaic(
        self,
        input_dir: str,
        year: int,
        pattern: str,
    ) -> xr.DataArray:
        tif_path = Path(input_dir) / pattern.format(year=year)
        da = xr.open_dataarray(tif_path, engine="rasterio")
        if "band" in da.dims:
            da = da.isel(band=0, drop=True)
        da = da.rename("efda_disturbance")
        da = da.assign_coords(time=np.datetime64(f"{year}-01-01"))
        da = da.expand_dims("time")
        return da

    def _open_year_agent(
        self,
        input_dir: str,
        year: int,
        pattern: str,
    ) -> xr.DataArray:
        tif_path = Path(input_dir) / pattern.format(year=year)
        da = xr.open_dataarray(tif_path, engine="rasterio")
        if "band" in da.dims:
            da = da.isel(band=0, drop=True)
        da = da.rename("efda_agent")
        da = da.assign_coords(time=np.datetime64(f"{year}-01-01"))
        da = da.expand_dims("time")
        return da

    def build_dataset(
        self,
        mosaic_dir: str,
        agent_dir: str,
        years: Sequence[int],
        mosaic_pattern: str = "{year}_disturb_mosaic_v211_22_epsg3035.tif",
        agent_pattern: str = "{year}_disturb_agent_v211_reclass_compv211_epsg3035.tif",
    ) -> xr.Dataset:

        mosaics = [
            self._open_year_mosaic(mosaic_dir, int(year), mosaic_pattern)
            for year in years
        ]
        agents = [
            self._open_year_agent(agent_dir, int(year), agent_pattern)
            for year in years
        ]

        da_mosaic = xr.concat(mosaics, dim="time")
        da_agent = xr.concat(agents, dim="time")

        ds = xr.Dataset(
            {
                "efda_disturbance": da_mosaic,
                "efda_agent": da_agent,
            }
        )

        return ds

    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:3035",
    ) -> xr.Dataset:
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int16")
        ds = self.set_crs(ds, crs=crs)

        ds["efda_disturbance"].attrs.update({
            "long_name": "EFDA disturbance mosaic",
            "description": "Annual disturbance fraction / class from EFDA.",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })

        ds["efda_agent"].attrs.update({
            "long_name": "EFDA disturbance agent",
            "description": "Disturbance agent classification (e.g., wind, bark beetle, harvest).",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })

        self.set_global_metadata(ds, {
            "product_name": "European Forest Disturbance Atlas (EFDA)",
            "created_by": "eoforeststac",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "_FillValue": fill_value,
            "crs": "EPSG:3035",
        })

        return ds

    def write(
        self,
        mosaic_dir: str,
        agent_dir: str,
        years: Sequence[int],
        output_zarr: str,
        mosaic_pattern: str = "{year}_disturb_mosaic_v211_22_epsg3035.tif",
        agent_pattern: str = "{year}_disturb_agent_v211_reclass_compv211_epsg3035.tif",
        chunks: dict | None = None,
    ) -> str:
        ds = self.build_dataset(
            mosaic_dir=mosaic_dir,
            agent_dir=agent_dir,
            years=years,
            mosaic_pattern=mosaic_pattern,
            agent_pattern=agent_pattern,
        )
        ds = self.process_dataset(ds)

        if chunks is None:
            chunks = {"time": len(years), "y": 1000, "x": 1000}

        ds = ds.chunk(chunks)

        encoding = {
            var: {"chunks": (chunks["time"], chunks["y"], chunks["x"])}
            for var in ds.data_vars
        }

        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
