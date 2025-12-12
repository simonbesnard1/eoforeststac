import xarray as xr
from eoforeststac.providers.base import BaseProvider

class GAMIProvider(BaseProvider):
    def load_data(self, version: str) -> xr.Dataset:
        item_id = f"GAMI_v{version}"
        item = self.get_item("GAMI", item_id)

        if "zarr" not in item.assets:
            raise KeyError(f"No 'zarr' asset found for item {item_id} in collection GAMI")

        zarr_href = item.assets["zarr"].href
        store = self.s3_fs.get_mapper(zarr_href)
        return xr.open_zarr(store, consolidated=True)
