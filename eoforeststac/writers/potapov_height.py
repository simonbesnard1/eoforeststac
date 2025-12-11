import xarray as xr
from datetime import datetime

from eoforeststac.writers.base import BaseZarrWriter


class PotapovHeightWriter(BaseZarrWriter):
    """
    Writer for global canopy height product (Potapov et al.).

    Assumes a single global GeoTIFF, e.g.
      canopy_height_potapov_2020.tif
    """

    def build_dataset(
        self,
        geotiff_path: str,
        var_name: str = "canopy_height",
    ) -> xr.Dataset:
        da = xr.open_dataarray(geotiff_path, engine="rasterio")
        if "band" in da.dims:
            da = da.isel(band=0, drop=True)
        da = da.rename(var_name)
        ds = da.to_dataset(name=var_name)
        return ds

    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        var_name: str = "canopy_height",
        reference_year: int | None = 2020,
    ) -> xr.Dataset:
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int16")
        ds = self.set_crs(ds, crs=crs)

        ds[var_name].attrs.update({
            "long_name": "Canopy top height",
            "units": "m",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })

        meta = {
            "product_name": "Global Canopy Height (Potapov et al.)",
            "created_by": "eoforeststac",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "_FillValue": fill_value,
            "crs": crs,
        }
        if reference_year is not None:
            meta["reference_year"] = reference_year

        self.set_global_metadata(ds, meta)
        return ds

    def write(
        self,
        geotiff_path: str,
        output_zarr: str,
        var_name: str = "canopy_height",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: dict | None = None,
        reference_year: int | None = 2020,
    ) -> str:
        ds = self.build_dataset(geotiff_path=geotiff_path, var_name=var_name)
        ds = self.process_dataset(
            ds,
            fill_value=fill_value,
            crs=crs,
            var_name=var_name,
            reference_year=reference_year,
        )

        if chunks is None:
            # no time dim here: (y, x)
            chunks = {"y": 1000, "x": 1000}

        ds = ds.chunk(chunks)

        encoding = {
            var: {"chunks": (chunks["y"], chunks["x"])}
            for var in ds.data_vars
        }

        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
