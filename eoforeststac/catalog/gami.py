# eoforeststac/catalog/gami.py
from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.gami import GAMI_CFG

def create_gami_collection():
    return create_collection(GAMI_CFG)

def create_gami_item(version: str):
    return create_item(GAMI_CFG, version)

