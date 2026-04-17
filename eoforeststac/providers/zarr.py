# eoforeststac/providers/zarr.py

import fsspec
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
        resolution: Optional[str] = None,
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
        # If resolution is given, build the resolution-specific key (e.g. zarr_0.25deg)
        if resolution is not None:
            asset_key = f"zarr_{resolution}"

        if asset_key not in item.assets:
            available = list(item.assets.keys())
            # Suggest resolution keys if this looks like a multi-resolution product
            zarr_keys = [k for k in available if k.startswith("zarr_")]
            hint = (
                f" Use resolution='{zarr_keys[0].removeprefix('zarr_')}' or one of: "
                f"{', '.join(k.removeprefix('zarr_') for k in zarr_keys)}"
                if zarr_keys
                else ""
            )
            raise ValueError(
                f"Asset '{asset_key}' not found for item '{item_id}'.{hint} "
                f"Available assets: {', '.join(available)}"
            )

        href = item.assets[asset_key].href
        if href.startswith("https://"):
            store = fsspec.get_mapper(href)
        else:
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
