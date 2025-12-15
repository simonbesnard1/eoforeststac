# eoforeststac/catalog/jrc_gfc.py
from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.jrc_gfc import JRC_GFC_CFG

def create_jrc_gfc_collection():
    return create_collection(JRC_GFC_CFG)

def create_jrc_gfc_item(version: str):
    return create_item(JRC_GFC_CFG, version)

