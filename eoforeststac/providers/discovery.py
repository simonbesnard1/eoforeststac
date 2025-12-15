# eoforeststac/providers/discovery.py

from typing import Dict, List, Optional
import pandas as pd
from eoforeststac.providers.base import BaseProvider


class DiscoveryProvider(BaseProvider):
    """
    STAC-based discovery utilities for EOForestSTAC catalogs.
    """

    def collections_table(self) -> pd.DataFrame:
        """
        Return a product-level discovery table.

        Columns
        -------
        - collection_id
        - title
        - description
        - versions (list[str])
        - n_versions
        """
        records = []

        for collection in self.catalog.get_children():
            collection_id = collection.id

            versions = self.list_versions(collection_id)

            records.append(
                {
                    "collection_id": collection_id,
                    "title": collection.title or "",
                    "description": collection.description or "",
                    "versions": versions,
                    "n_versions": len(versions),
                }
            )

        return pd.DataFrame(records)
    
    # ------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------
    def list_collections(self) -> Dict[str, str]:
        """
        List all collections in the catalog.

        Returns
        -------
        dict
            {collection_id: collection_title}
        """
        return {
            col.id: col.title or ""
            for col in self.catalog.get_children()
        }

    # ------------------------------------------------------------
    # Versions
    # ------------------------------------------------------------
    def list_versions(
        self,
        collection_id: str,
        asset_key: Optional[str] = None,
    ) -> List[str]:
        """
        List available versions for a collection.

        Parameters
        ----------
        collection_id : str
            STAC collection ID
        asset_key : str, optional
            Only return versions that contain this asset (e.g. 'zarr')

        Returns
        -------
        list[str]
            Sorted list of versions
        """
        collection = self.get_collection(collection_id)

        versions = []

        for item in collection.get_items():

            # 1️⃣ preferred: explicit version property
            version = item.properties.get("version")

            # 2️⃣ fallback: parse from item ID
            if version is None:
                version = self._parse_version_from_item_id(
                    item.id,
                    collection_id,
                )

            if version is None:
                continue

            if asset_key is not None and asset_key not in item.assets:
                continue

            versions.append(version)

        return sorted(set(versions), key=self._version_key)

    # ------------------------------------------------------------
    # Items (optional, power users)
    # ------------------------------------------------------------
    def list_items(
        self,
        collection_id: str,
        asset_key: Optional[str] = None,
    ) -> List[str]:
        """
        List item IDs for a collection.

        Parameters
        ----------
        collection_id : str
            STAC collection ID
        asset_key : str, optional
            Filter by asset presence

        Returns
        -------
        list[str]
            Item IDs
        """
        collection = self.get_collection(collection_id)

        items = []
        for item in collection.get_items():
            if asset_key is not None and asset_key not in item.assets:
                continue
            items.append(item.id)

        return sorted(items)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    @staticmethod
    def _parse_version_from_item_id(item_id: str, collection_id: str) -> Optional[str]:
        """
        Parse version from item ID of the form:
            {collection_id}_vX.Y[.Z]
        """
        prefix = f"{collection_id}_v"
        if item_id.startswith(prefix):
            return item_id[len(prefix):]
        return None

    @staticmethod
    def _version_key(v: str):
        """
        Sort versions numerically where possible.
        """
        try:
            return tuple(int(p) for p in v.split("."))
        except ValueError:
            return v
