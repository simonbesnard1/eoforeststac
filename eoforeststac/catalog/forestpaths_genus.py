from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.forestpaths_genus import FORESTPATHS_GENUS_CFG

create_forestpaths_genus_collection = lambda: create_collection(FORESTPATHS_GENUS_CFG)
create_forestpaths_genus_item = lambda v: create_item(FORESTPATHS_GENUS_CFG, v)
