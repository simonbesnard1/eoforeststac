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
        """
        Open a Zarr dataset referenced by a STAC Item asset.

        Parameters
        ----------
        collection_id : str
            STAC collection ID (e.g. 'GAMI')
        version : str
            Dataset version (e.g. '3.1')
        asset_key : str
            Asset key pointing to the Zarr store (default: 'zarr')
        variables : list[str], optional
            Subset of variables to load
        """

        # ----------------------------------------------------------
        # Derive item ID (single source of truth)
        # ----------------------------------------------------------
        item_id = f"{collection_id}_v{version}"

        item = self.get_item(collection_id, item_id)

        if asset_key not in item.assets:
            raise KeyError(
                f"No asset '{asset_key}' found for item '{item_id}' "
                f"in collection '{collection_id}'. "
                f"Available assets: {list(item.assets.keys())}"
            )

        href = item.assets[asset_key].href
        store = self.s3_fs.get_mapper(href)

        # ----------------------------------------------------------
        # Robust consolidated-metadata handling
        # ----------------------------------------------------------
        try:
            ds = xr.open_zarr(store=store, consolidated=True)
        except (KeyError, FileNotFoundError):
            ds = xr.open_zarr(store=store, consolidated=False)

        if variables is not None:
            ds = ds[variables]

        return ds
