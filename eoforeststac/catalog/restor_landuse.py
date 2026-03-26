from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.restor_landuse import RESTOR_LANDUSE_CFG

create_restor_landuse_collection = lambda: create_collection(RESTOR_LANDUSE_CFG)
create_restor_landuse_item = lambda version: create_item(RESTOR_LANDUSE_CFG, version)
