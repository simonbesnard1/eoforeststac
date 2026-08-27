from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.xu_recovery_curves import XU_RECOVERY_CURVES_CFG

create_xu_recovery_curves_collection = lambda: create_collection(XU_RECOVERY_CURVES_CFG)
create_xu_recovery_curves_item = lambda v: create_item(XU_RECOVERY_CURVES_CFG, v)
