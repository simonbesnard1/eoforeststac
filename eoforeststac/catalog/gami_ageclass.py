# eoforeststac/catalog/gami_ageclass.py
import pystac

from eoforeststac.catalog.factory import create_collection, create_item
from eoforeststac.core.assets import create_zarr_asset
from eoforeststac.products.gami_ageclass import (
    GAMI_AGECLASS_CFG,
    GAMI_AGECLASS_RESOLUTIONS,
)


def create_gami_ageclass_collection() -> pystac.Collection:
    return create_collection(GAMI_AGECLASS_CFG)


def create_gami_ageclass_item(version: str) -> pystac.Item:
    """One item per version, with one Zarr asset per spatial resolution."""
    item = create_item(GAMI_AGECLASS_CFG, version)

    for res, meta in GAMI_AGECLASS_RESOLUTIONS.items():
        item.add_asset(
            f"zarr_{res}",
            create_zarr_asset(
                href=f"{GAMI_AGECLASS_CFG['base_path']}/GAMI_AGECLASS_{res}_v{version}.zarr",
                title=f"{res}",
                roles=["data"],
                description=(
                    f"Zarr store at {res} resolution. "
                    "Dims: members (20), age_class (12), latitude, longitude, time (2010, 2020)."
                ),
            ),
        )

    return item
