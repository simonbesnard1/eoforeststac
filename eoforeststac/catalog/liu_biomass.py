from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.liu_biomass import LIU_BIOMASS_CFG

create_liu_biomass_collection = lambda: create_collection(LIU_BIOMASS_CFG)
create_liu_biomass_item = lambda v: create_item(LIU_BIOMASS_CFG, v)

