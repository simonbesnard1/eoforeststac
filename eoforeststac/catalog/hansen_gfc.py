# eoforeststac/catalog/hansen_gfc.py
from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.hansen_gfc import HANSEN_GFC_CFG

def create_hansen_gfc_collection():
    return create_collection(HANSEN_GFC_CFG)

def create_hansen_gfc_item(version: str):
    return create_item(HANSEN_GFC_CFG, version)




