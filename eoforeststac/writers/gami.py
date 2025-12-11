from eoforeststac.writers.base import BaseZarrWriter
import xarray as xr
import datetime

class GAMIWriter(BaseZarrWriter):

    def load_native(self, input_path):
        return xr.open_zarr(input_path, chunks={'time': 5, 'lat': 500, 'lon': 500})

    def process(self, ds):
        fill_value = -9999
        ds = self.apply_fillvalue(ds, fill_value).astype("int16")
        ds = self.write_crs(ds)

        ds["forest_age"].attrs.update({
            "long_name": "Forest age using ML + LTSD fusion",
            "units": "years",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })

        self.set_global_metadata(ds, {
            "product_name": "Global Age Mapping Integration (GAMI)",
            "created_by": "Simon Besnard",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "_FillValue": fill_value,
        })

        return ds

    def write(self, input_path, output_zarr):
        ds = self.load_native(input_path)
        ds = self.process(ds)
        encoding = {var: {"chunks": (5, 500, 500)} for var in ds.data_vars}
        return self.write_to_zarr(ds, output_zarr, encoding)
