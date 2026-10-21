import pystac

from eoforeststac.catalog.factory import create_collection
from eoforeststac.catalog.sites import create_site_collection, create_site_item
from eoforeststac.products.als_products import ALS_PRODUCTS_CFG, ALS_RESOLUTIONS


def create_als_products_collection():
    return create_collection(ALS_PRODUCTS_CFG)


def create_als_products_site_collection(site_id: str) -> pystac.Collection:
    return create_site_collection(ALS_PRODUCTS_CFG, site_id)


def create_als_products_item(site_id: str, version: str) -> pystac.Item:
    """Return the item for one site and version, with one Zarr asset per resolution."""
    return create_site_item(ALS_PRODUCTS_CFG, site_id, version, ALS_RESOLUTIONS)
