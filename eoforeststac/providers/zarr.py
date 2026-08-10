# eoforeststac/providers/zarr.py

import fsspec
import xarray as xr
from typing import Dict, List, Optional, Sequence

from eoforeststac.providers.base import BaseProvider


class ZarrProvider(BaseProvider):
    """
    Generic STAC-driven Zarr provider.

    Most collections have one item per version (e.g. GAMI_v2.1).
    Multi-region collections (ALS_PRODUCTS, ULS_PRODUCTS) have one item per
    region+version (e.g. ALS_SPAIN_PNOA_v1.0). Use the ``region`` parameter
    to select a specific region for those collections.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _items_for_version(self, collection_id: str, version: str):
        """Return all items in a collection whose ID ends with _v{version}."""
        collection = self.get_collection(collection_id)
        if collection is None:
            return []
        suffix = f"_v{version}"
        return [i for i in collection.get_items() if i.id.endswith(suffix)]

    def list_regions(self, collection_id: str, version: str) -> List[str]:
        """
        List region identifiers available for a multi-region collection.

        Returns the item-ID prefix (everything before ``_v{version}``), which
        can be passed directly as ``region`` to :meth:`open_dataset`.
        """
        suffix = f"_v{version}"
        return sorted(
            i.id[: -len(suffix)]
            for i in self._items_for_version(collection_id, version)
        )

    def _resolve_item(self, collection_id: str, version: str, region: Optional[str]):
        """
        Locate a pystac.Item for (collection, version, region).

        Raises ValueError with actionable hints if nothing is found.
        """
        collection = self.get_collection(collection_id)
        if collection is None:
            available = sorted(c.id for c in self.list_collections())
            raise ValueError(
                f"Collection '{collection_id}' not found. "
                f"Available collections: {', '.join(available)}"
            )

        suffix = f"_v{version}"

        if region is None:
            # Standard single-item pattern: COLLECTION_v{version}
            item = collection.get_item(f"{collection_id}{suffix}")
            if item is not None:
                return item

            # Not found — check whether this is a multi-region collection
            regions = self.list_regions(collection_id, version)
            if regions:
                raise ValueError(
                    f"Collection '{collection_id}' contains multiple regions. "
                    f"Use region='...' with one of: {', '.join(regions)}"
                )

            # No items at all with this version — maybe wrong version?
            all_versions = sorted(
                {
                    i.id.rsplit("_v", 1)[-1]
                    for i in collection.get_items()
                    if "_v" in i.id
                }
            )
            if all_versions:
                raise ValueError(
                    f"Version '{version}' not found for collection '{collection_id}'. "
                    f"Available version(s): {', '.join(all_versions)}"
                )
            raise ValueError(f"No items found for collection '{collection_id}'.")

        else:
            # Multi-region: try exact match first (region == zarr_name, e.g. ALS_SPAIN_PNOA)
            item = collection.get_item(f"{region}{suffix}")
            if item is not None:
                return item

            # Fuzzy: search all versioned items for a case-insensitive substring match
            needle = region.upper()
            versioned = [i for i in collection.get_items() if i.id.endswith(suffix)]
            matches = [i for i in versioned if needle in i.id.upper()]

            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise ValueError(
                    f"Region '{region}' is ambiguous for collection '{collection_id}'. "
                    f"Matches: {', '.join(i.id for i in matches)}. Be more specific."
                )

            available = sorted(i.id[: -len(suffix)] for i in versioned)
            raise ValueError(
                f"Region '{region}' not found in collection '{collection_id}' v{version}. "
                f"Available regions: {', '.join(available) or 'none'}"
            )

    @staticmethod
    def _open_zarr_store(href: str, s3_fs) -> xr.Dataset:
        store = (
            fsspec.get_mapper(href)
            if href.startswith("https://")
            else s3_fs.get_mapper(href)
        )
        try:
            return xr.open_zarr(store=store, consolidated=True)
        except (KeyError, FileNotFoundError):
            return xr.open_zarr(store=store, consolidated=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_dataset(
        self,
        collection_id: str,
        version: str,
        asset_key: str = "zarr",
        resolution: Optional[str] = None,
        variables: Optional[Sequence[str]] = None,
        region: Optional[str] = None,
    ) -> xr.Dataset:
        """
        Open a single Zarr dataset from the catalog.

        Parameters
        ----------
        collection_id : str
            STAC collection ID (e.g. ``"GAMI"``, ``"ALS_PRODUCTS"``).
        version : str
            Dataset version (e.g. ``"2.1"``, ``"1.0"``).
        asset_key : str
            Asset key to open. Defaults to ``"zarr"``.
        resolution : str, optional
            Resolution suffix — shorthand for ``asset_key="zarr_{resolution}"``
            (e.g. ``resolution="1m"`` → ``asset_key="zarr_1m"``).
        variables : sequence of str, optional
            Subset of variables to keep after opening.
        region : str, optional
            Region identifier for multi-region collections such as
            ``ALS_PRODUCTS`` or ``ULS_PRODUCTS``.  Pass the zarr-name prefix
            (e.g. ``"ALS_SPAIN_PNOA"``) or a case-insensitive substring
            (e.g. ``"spain"``).  Use :meth:`list_regions` to see what is
            available.
        """
        item = self._resolve_item(collection_id, version, region)

        # ----------------------------------------------------------
        # Asset lookup
        # ----------------------------------------------------------
        if resolution is not None:
            asset_key = f"zarr_{resolution}"

        if asset_key not in item.assets:
            available = list(item.assets.keys())
            zarr_keys = [k for k in available if k.startswith("zarr_")]
            hint = (
                f" Use resolution='{zarr_keys[0].removeprefix('zarr_')}' or one of: "
                f"{', '.join(k.removeprefix('zarr_') for k in zarr_keys)}"
                if zarr_keys
                else ""
            )
            raise ValueError(
                f"Asset '{asset_key}' not found for item '{item.id}'.{hint} "
                f"Available assets: {', '.join(available)}"
            )

        ds = self._open_zarr_store(item.assets[asset_key].href, self.s3_fs)

        if variables is not None:
            ds = ds[variables]

        return ds

    def open_all_regions(
        self,
        collection_id: str,
        version: str,
        asset_key: str = "zarr",
        resolution: Optional[str] = None,
        variables: Optional[Sequence[str]] = None,
    ) -> Dict[str, xr.Dataset]:
        """
        Open all regions of a multi-region collection at once.

        Returns a dict keyed by region name (the item-ID prefix, e.g.
        ``"ALS_SPAIN_PNOA"``).
        """
        regions = self.list_regions(collection_id, version)
        if not regions:
            raise ValueError(
                f"No regions found for collection '{collection_id}' v{version}. "
                f"Use open_dataset() for single-item collections."
            )
        return {
            r: self.open_dataset(
                collection_id,
                version,
                asset_key=asset_key,
                resolution=resolution,
                variables=variables,
                region=r,
            )
            for r in regions
        }
