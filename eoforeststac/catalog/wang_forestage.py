from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.wang_forestage import WANG_FORESTAGE_CFG

create_wang_forestage_collection = lambda: create_collection(WANG_FORESTAGE_CFG)
create_wang_forestage_item = lambda version: create_item(WANG_FORESTAGE_CFG, version)
