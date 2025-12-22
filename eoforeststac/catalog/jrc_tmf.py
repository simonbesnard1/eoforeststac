from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.jrc_tmf import JRC_TMF_CFG

create_jrc_tmf_collection = lambda: create_collection(JRC_TMF_CFG)
create_jrc_tmf_item = lambda version: create_item(JRC_TMF_CFG, version)

