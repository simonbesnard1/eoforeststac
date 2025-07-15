import xarray as xr
import pystac
import fsspec
import json

class S3STACReader:
    """
    A reader for accessing STAC (SpatioTemporal Asset Catalog) data stored in an S3 bucket.
    This class provides methods for listing collections, retrieving items, and loading Zarr datasets.
    """
    
    def __init__(self, bucket_url: str, endpoint_url: str = "https://s3.gfz-potsdam.de", anon: bool = True):
        """
        Initialize the S3STACReader.

        Args:
            bucket_url (str): S3 URL pointing to the STAC catalog JSON file.
            endpoint_url (str, optional): The S3 endpoint URL. Defaults to "https://s3.gfz-potsdam.de".
            anon (bool, optional): Set to True for public S3 access, False for authenticated access. Defaults to True.
        """
        self.bucket_url = bucket_url
        self.s3_fs = fsspec.filesystem("s3", anon=anon, endpoint_url=endpoint_url)
        self._register_stac_io()
        self.catalog = self._load_catalog()

    def _register_stac_io(self):
        """
        Register a custom STAC I/O handler to enable reading STAC JSON files directly from the S3 bucket.
        """
        class S3StacIO(pystac.StacIO):
            s3_fs = self.s3_fs

            def read_text(self, href: str) -> str:
                """Read text content from a given S3 path."""
                with self.s3_fs.open(href, "r") as f:
                    return f.read()

            def write_text(self, href: str, txt: str) -> None:
                """Write text content to a given S3 path."""
                with self.s3_fs.open(href, "w") as f:
                    f.write(txt)

            def exists(self, href: str) -> bool:
                """Check if a file exists at a given S3 path."""
                return self.s3_fs.exists(href)

        pystac.StacIO.set_default(S3StacIO)

    def _load_catalog(self) -> pystac.Catalog:
        """
        Load the STAC catalog from the S3 bucket.

        Returns:
            pystac.Catalog: A STAC catalog object representing the dataset structure.
        """
        with self.s3_fs.open(self.bucket_url, 'r') as f:
            catalog_json = json.load(f)
        return pystac.Catalog.from_dict(catalog_json)

    def list_collections(self) -> list:
        """
        Retrieve a list of all collection IDs available in the catalog.

        Returns:
            list: A list of collection IDs.
        """
        return [collection.id for collection in self.catalog.get_children()]

    def list_items(self, collection_id: str) -> list:
        """
        Retrieve a list of all item IDs within a specified collection.

        Args:
            collection_id (str): The ID of the collection to query.

        Returns:
            list: A list of item IDs within the specified collection.
        """
        collection = self.catalog.get_child(collection_id)
        return [item.id for item in collection.get_items()]

    def load_zarr_dataset(self, collection_id: str, item_id: str, consolidated: bool = True) -> xr.Dataset:
        """
        Load a Zarr dataset from the STAC catalog.

        Args:
            collection_id (str): The ID of the collection containing the dataset.
            item_id (str): The ID of the item within the collection.
            consolidated (bool, optional): Whether to use consolidated metadata. Defaults to True.

        Returns:
            xr.Dataset: The opened xarray dataset.

        Raises:
            KeyError: If the specified item does not contain a 'zarr' asset.
        """
        collection = self.catalog.get_child(collection_id)
        item = collection.get_item(item_id)
        
        if "zarr" not in item.assets:
            raise KeyError(f"Item '{item_id}' in collection '{collection_id}' does not contain a 'zarr' asset.")
        
        zarr_asset = item.assets["zarr"]
        store = self.s3_fs.get_mapper(zarr_asset.href)
        return xr.open_zarr(store, consolidated=consolidated)


# Example usage
if __name__ == "__main__":
    bucket_url = "s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json"
    reader = S3STACReader(bucket_url)

    # List available collections
    print("Collections:", reader.list_collections())
    
    # List items in the 'GAMI' collection
    print("GAMI Items:", reader.list_items("GAMI"))
    
    # Load and print a Zarr dataset
    ds = reader.load_zarr_dataset("GAMI", "GAMI_v2.1")
    print(ds)

