from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.potapov_height import POTAPOV_HEIGHT_CFG

create_potapov_height_collection = lambda: create_collection(POTAPOV_HEIGHT_CFG)
create_potapov_height_item = lambda version: create_item(POTAPOV_HEIGHT_CFG, version)

