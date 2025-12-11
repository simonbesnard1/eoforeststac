from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.saatchi_biomass import SAATCHI_BIOMASS_CFG

create_saatchi_biomass_collection = lambda: create_collection(SAATCHI_BIOMASS_CFG)
create_saatchi_biomass_item = lambda v: create_item(SAATCHI_BIOMASS_CFG, v)

