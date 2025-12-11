from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.tmf import TMF_CFG

create_tmf_collection = lambda: create_collection(TMF_CFG)
create_tmf_item = lambda version: create_item(TMF_CFG, version)

