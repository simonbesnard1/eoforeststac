from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.products.cci_biomass import (
    CCI_BIOMASS_CFG,
    CCI_BIOMASS_VERSION_EXTENT,
)

create_cci_biomass_collection = lambda: create_collection(CCI_BIOMASS_CFG)


def create_cci_biomass_item(version: str):
    """
    CCI Biomass item, using the temporal extent actually published for
    this specific version rather than the collection-wide union.
    """
    start, end = CCI_BIOMASS_VERSION_EXTENT.get(
        version, (CCI_BIOMASS_CFG["start_datetime"], CCI_BIOMASS_CFG["end_datetime"])
    )
    version_cfg = {
        **CCI_BIOMASS_CFG,
        "start_datetime": start,
        "end_datetime": end,
    }
    return create_item(version_cfg, version)
