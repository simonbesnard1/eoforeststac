import fsspec
import pystac
import json

class BaseProvider:
    def __init__(self, catalog_url: str, endpoint_url: str = "https://s3.gfz-potsdam.de", anon: bool = True):
        self.catalog_url = catalog_url
        self.endpoint_url = endpoint_url
        self.anon = anon
        self.s3_fs = fsspec.filesystem("s3", anon=anon, endpoint_url=endpoint_url)

        self._register_stac_io()
        self.catalog = self._load_catalog()

    def _register_stac_io(self):
        """Registers a custom StacIO class for S3-based reading."""
        fs = self.s3_fs  # capture in closure

        class S3StacIO(pystac.StacIO):
            def read_text(self, href: str) -> str:
                with fs.open(href, "r") as f:
                    return f.read()

            def write_text(self, href: str, txt: str) -> None:
                with fs.open(href, "w") as f:
                    f.write(txt)

            def exists(self, href: str) -> bool:
                return fs.exists(href)

        pystac.StacIO.set_default(S3StacIO)

    def _load_catalog(self) -> pystac.Catalog:
        with self.s3_fs.open(self.catalog_url) as f:
            catalog_dict = json.load(f)
        return pystac.Catalog.from_dict(catalog_dict)

    def get_collection(self, collection_id: str) -> pystac.Collection:
        return self.catalog.get_child(collection_id)

    def get_item(self, collection_id: str, item_id: str) -> pystac.Item:
        collection = self.get_collection(collection_id)
        return collection.get_item(item_id)
