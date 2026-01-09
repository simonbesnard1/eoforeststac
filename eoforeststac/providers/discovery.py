# eoforeststac/providers/discovery.py

from __future__ import annotations

from typing import Dict, List, Optional
import pandas as pd
import pystac

from eoforeststac.providers.base import BaseProvider


class DiscoveryProvider(BaseProvider):
    """
    STAC-based discovery utilities for EOForestSTAC catalogs (themed).
    """

    # ------------------------------------------------------------
    # Themes
    # ------------------------------------------------------------
    def list_themes(self) -> Dict[str, str]:
        """
        List theme catalogs at the root level.

        Returns
        -------
        dict
            {theme_id: theme_title}
        """
        themes: Dict[str, str] = {}
        for child in self.catalog.get_children():
            if isinstance(child, pystac.Catalog) and not isinstance(child, pystac.Collection):
                themes[child.id] = child.title or child.id
        return themes

    def get_theme(self, theme_id: str) -> Optional[pystac.Catalog]:
        for child in self.catalog.get_children():
            if isinstance(child, pystac.Catalog) and not isinstance(child, pystac.Collection):
                if child.id == theme_id:
                    return child
        return None

    # ------------------------------------------------------------
    # Collections (require theme)
    # ------------------------------------------------------------
    def list_collections(self, theme: Optional[str] = None) -> Dict[str, str]:
        """
        List collections within a theme.

        Parameters
        ----------
        theme : str
            Theme catalog id (required). Use list_themes() to discover options.

        Returns
        -------
        dict
            {collection_id: collection_title}
        """
        if theme is None:
            themes = self.list_themes()
            raise ValueError(
                "This catalog is organized by themes. Please provide theme=...\n"
                f"Available themes: {', '.join([f'{k} ({v})' for k, v in themes.items()])}"
            )

        theme_cat = self.get_theme(theme)
        if theme_cat is None:
            themes = self.list_themes()
            raise KeyError(
                f"Theme '{theme}' not found.\n"
                f"Available themes: {', '.join([f'{k} ({v})' for k, v in themes.items()])}"
            )

        # Note: under a theme, get_collections() is usually reliable if self_href resolves.
        cols = list(theme_cat.get_collections())
        return {c.id: (c.title or c.id) for c in cols}

    def collections_table(self, theme: Optional[str] = None) -> pd.DataFrame:
        """
        Product-level discovery table for a given theme.
        """
        if theme is None:
            themes = self.list_themes()
            raise ValueError(
                "Please provide theme=... to build a discovery table.\n"
                f"Available themes: {', '.join([f'{k} ({v})' for k, v in themes.items()])}"
            )

        theme_cat = self.get_theme(theme)
        if theme_cat is None:
            themes = self.list_themes()
            raise KeyError(
                f"Theme '{theme}' not found.\n"
                f"Available themes: {', '.join([f'{k} ({v})' for k, v in themes.items()])}"
            )

        records = []
        for col in theme_cat.get_collections():
            versions = self.list_versions(col.id)
            records.append(
                {
                    "collection_id": col.id,
                    "title": col.title or "",
                    "description": col.description or "",
                    "versions": versions,
                    "n_versions": len(versions),
                }
            )

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values(["collection_id"]).reset_index(drop=True)
        return df

    # ------------------------------------------------------------
    # Versions (unchanged)
    # ------------------------------------------------------------
    def list_versions(self, collection_id: str, asset_key: Optional[str] = None) -> List[str]:
        collection = self.get_collection(collection_id)
        if collection is None:
            raise KeyError(f"Collection '{collection_id}' not found.")

        versions: List[str] = []
        for item in collection.get_items():
            version = item.properties.get("version")
            if version is None:
                version = self._parse_version_from_item_id(item.id, collection_id)
            if version is None:
                continue
            if asset_key is not None and asset_key not in item.assets:
                continue
            versions.append(version)

        return sorted(set(versions), key=self._version_key)

    @staticmethod
    def _parse_version_from_item_id(item_id: str, collection_id: str) -> Optional[str]:
        prefix = f"{collection_id}_v"
        if item_id.startswith(prefix):
            return item_id[len(prefix):]
        return None

    @staticmethod
    def _version_key(v: str):
        try:
            return tuple(int(p) for p in v.split("."))
        except ValueError:
            return v
