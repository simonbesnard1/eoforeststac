import pystac

from eoforeststac.catalog.factory import create_collection
from eoforeststac.catalog.sites import create_site_collection, create_site_item
from eoforeststac.products.uls_products import ULS_PRODUCTS_CFG, ULS_RESOLUTIONS


def create_uls_products_collection():
    return create_collection(ULS_PRODUCTS_CFG)


def create_uls_products_site_collection(site_id: str) -> pystac.Collection:
    return create_site_collection(ULS_PRODUCTS_CFG, site_id)


def create_uls_products_item(site_id: str, version: str) -> pystac.Item:
    """Return the item for one site and version, with one Zarr asset per resolution."""
    return create_site_item(ULS_PRODUCTS_CFG, site_id, version, ULS_RESOLUTIONS)
