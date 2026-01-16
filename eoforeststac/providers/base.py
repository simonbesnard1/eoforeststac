import json
from typing import List, Optional

import fsspec
import pystac


class BaseProvider:
    def __init__(
        self,
        catalog_url: str,
        endpoint_url: str = "https://s3.gfz-potsdam.de",
        anon: bool = True,
    ):
        self.catalog_url = catalog_url
        self.endpoint_url = endpoint_url
        self.anon = anon        
        storage_options = {
            "anon": anon,
            "client_kwargs": {"endpoint_url": endpoint_url},
        }        
        self.s3_fs = fsspec.filesystem("s3", **storage_options)
        self._register_stac_io()
        self.catalog = self._load_catalog()

    def _register_stac_io(self) -> None:
        """StacIO that can read both s3:// and https:// hrefs via fsspec."""
        class FsspecStacIO(pystac.StacIO):
            def read_text(self, href: str, *args, **kwargs) -> str:
                with fsspec.open(href, "r") as f:
                    return f.read()
    
            def write_text(self, href: str, txt: str, *args, **kwargs) -> None:
                with fsspec.open(href, "w") as f:
                    f.write(txt)
    
            def exists(self, href: str, *args, **kwargs) -> bool:
                fs, path = fsspec.core.url_to_fs(href)
                return fs.exists(path)
    
        pystac.StacIO.set_default(FsspecStacIO)


    def _load_catalog(self) -> pystac.Catalog:
        # fsspec.open works for s3:// and https:// (if you ever switch)
        with fsspec.open(self.catalog_url, "r") as f:
            catalog_dict = json.load(f)

        cat = pystac.Catalog.from_dict(catalog_dict)
        cat.set_self_href(self.catalog_url)
        
        return cat
    
    # -----------------------------
    # STAC accessors
    # -----------------------------
    def get_collection(self, collection_id: str) -> Optional[pystac.Collection]:
        # With themes, collections are not direct children anymore
        return self.catalog.get_child(collection_id, recursive=True)

    def get_item(self, collection_id: str, item_id: str) -> pystac.Item:
        collection = self.get_collection(collection_id)
        if collection is None:
            raise KeyError(f"Collection '{collection_id}' not found.")
        item = collection.get_item(item_id)
        if item is None:
            raise KeyError(f"Item '{item_id}' not found in collection '{collection_id}'.")
        return item

    # -----------------------------
    # Catalog helpers
    # -----------------------------
    def list_collections(self) -> List[pystac.Collection]:
        """
        Return all collections in the catalog, robust to themed/nested catalogs.
        """
        cols = {}
        for root, children, _items in self.catalog.walk():
            for child in children:
                if isinstance(child, pystac.Collection):
                    cols[child.id] = child
        return list(cols.values())

    def list_collection_ids(self) -> List[str]:
        return sorted([c.id for c in self.list_collections()])

    def list_items(self, collection_id: str) -> List[pystac.Item]:
        collection = self.get_collection(collection_id)
        if collection is None:
            raise KeyError(
                f"Collection '{collection_id}' not found.\n"
                f"Available collections: {', '.join(self.list_collection_ids())}"
            )
        return list(collection.get_items())