from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.radd_europe import RADD_EUROPE_CFG

create_radd_europe_collection = lambda: create_collection(RADD_EUROPE_CFG)
create_radd_europe_item = lambda version: create_item(RADD_EUROPE_CFG, version)
