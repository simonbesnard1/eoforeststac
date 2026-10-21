import pystac

from eoforeststac.catalog.factory import create_collection
from eoforeststac.catalog.sites import create_site_collection, create_site_item
from eoforeststac.products.als_biomass_products import ALS_BIOMASS_PRODUCTS_CFG


def create_als_biomass_products_collection():
    return create_collection(ALS_BIOMASS_PRODUCTS_CFG)


def create_als_biomass_products_site_collection(site_id: str) -> pystac.Collection:
    return create_site_collection(ALS_BIOMASS_PRODUCTS_CFG, site_id)


def create_als_biomass_products_item(site_id: str, version: str) -> pystac.Item:
    """Return the item for one site and version, with a single 10 m Zarr asset."""
    return create_site_item(ALS_BIOMASS_PRODUCTS_CFG, site_id, version)
