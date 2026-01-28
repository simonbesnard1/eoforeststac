from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.cci_biomass import CCI_BIOMASS_CFG

create_cci_biomass_collection = lambda: create_collection(CCI_BIOMASS_CFG)
create_cci_biomass_item = lambda version: create_item(CCI_BIOMASS_CFG, version)
