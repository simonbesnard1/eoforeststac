# eoforeststac/providers/zarr.py

import xarray as xr
from typing import Optional, Sequence

from eoforeststac.providers.base import BaseProvider


class ZarrProvider(BaseProvider):
    """
    Generic STAC-driven Zarr provider.
    """

    def open_dataset(
        self,
        collection_id: str,
        version: str,
        asset_key: str = "zarr",
        variables: Optional[Sequence[str]] = None,
    ) -> xr.Dataset:
    
        # ----------------------------------------------------------
        # 0. Collection existence check
        # ----------------------------------------------------------
        collection = self.get_collection(collection_id)
    
        if collection is None:
            available = sorted(c.id for c in self.list_collections())
            raise ValueError(
                f"Collection '{collection_id}' not found. "
                f"Available collections: {', '.join(available)}"
            )
    
        # ----------------------------------------------------------
        # 1. Derive item ID
        # ----------------------------------------------------------
        item_id = f"{collection_id}_v{version}"
    
        item = collection.get_item(item_id)
    
        # ----------------------------------------------------------
        # 2. Version existence check
        # ----------------------------------------------------------
        if item is None:
            versions = sorted(
                i.id.replace(f"{collection_id}_v", "")
                for i in collection.get_items()
                if i.id.startswith(f"{collection_id}_v")
            )
    
            if versions:
                raise ValueError(
                    f"Version '{version}' not found for collection '{collection_id}'. "
                    f"Available version(s): {', '.join(versions)}"
                )
            else:
                raise ValueError(
                    f"No versioned items found for collection '{collection_id}'."
                )
    
        # ----------------------------------------------------------
        # 3. Asset existence check
        # ----------------------------------------------------------
        if asset_key not in item.assets:
            raise ValueError(
                f"Asset '{asset_key}' not found for item '{item_id}'. "
                f"Available assets: {', '.join(item.assets.keys())}"
            )
    
        href = item.assets[asset_key].href
        store = self.s3_fs.get_mapper(href)
    
        # ----------------------------------------------------------
        # 4. Open Zarr
        # ----------------------------------------------------------
        try:
            ds = xr.open_zarr(store=store, consolidated=True)
        except (KeyError, FileNotFoundError):
            ds = xr.open_zarr(store=store, consolidated=False)
    
        if variables is not None:
            ds = ds[variables]
    
        return ds


