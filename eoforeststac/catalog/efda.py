from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.efda import EFDA_CFG

create_efda_collection = lambda: create_collection(EFDA_CFG)
create_efda_item = lambda version: create_item(EFDA_CFG, version)

