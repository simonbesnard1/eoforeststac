# eoforeststac/catalog/gami_ageclass.py
from typing import List

import pystac

from eoforeststac.catalog.factory import create_collection, create_item_for_resolution
from eoforeststac.products.gami_ageclass import (
    GAMI_AGECLASS_CFG,
    GAMI_AGECLASS_RESOLUTIONS,
)


def create_gami_ageclass_collection() -> pystac.Collection:
    return create_collection(GAMI_AGECLASS_CFG)


def create_gami_ageclass_items(version: str) -> List[pystac.Item]:
    """Return one STAC item per spatial resolution for the given version."""
    return [
        create_item_for_resolution(GAMI_AGECLASS_CFG, version, res)
        for res in GAMI_AGECLASS_RESOLUTIONS
    ]
