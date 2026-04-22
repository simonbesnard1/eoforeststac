from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.gedi_l4d import GEDI_L4D_CFG

create_gedi_l4d_collection = lambda: create_collection(GEDI_L4D_CFG)
create_gedi_l4d_item = lambda version: create_item(GEDI_L4D_CFG, version)
