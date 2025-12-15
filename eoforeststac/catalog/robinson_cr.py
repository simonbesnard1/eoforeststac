from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.robinson_cr import ROBINSON_CR_CFG

create_robinson_cr_collection = lambda: create_collection(ROBINSON_CR_CFG)
create_robinson_cr_item = lambda v: create_item(ROBINSON_CR_CFG, v)

