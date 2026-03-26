from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.potapov_lcluc import POTAPOV_LCLUC_CFG

create_potapov_lcluc_collection = lambda: create_collection(POTAPOV_LCLUC_CFG)
create_potapov_lcluc_item = lambda version: create_item(POTAPOV_LCLUC_CFG, version)