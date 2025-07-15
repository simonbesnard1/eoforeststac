import pystac
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.io import register_io
from eoforeststac.catalog_builders.gami import create_gami_collection, create_gami_item
from eoforeststac.catalog_builders.efda import create_efda_collection, create_efda_item

def build_catalog() -> pystac.Catalog:
    # Register the custom S3-based STAC I/O
    register_io()

    # Create the root catalog
    catalog = pystac.Catalog(
        id="EO_Global_Catalog",
        description="STAC catalog for Earth Observation datasets, including Biomass, Forest Age, and Forest Disturbance.",
        href=f"{BASE_S3_URL}/catalog.json"
    )

    # Add GAMI collection and items
    gami_collection = create_gami_collection()
    gami_collection.add_item(create_gami_item("2.1"))
    gami_collection.add_item(create_gami_item("2.0"))
    catalog.add_child(gami_collection)
    
    # Add EFDA collection and items
    EFDA_VERSIONS = ["2.1.1"]
    efda_collection = create_efda_collection()
    for version in EFDA_VERSIONS:
        for year in range(1985, 2024):
            item = create_efda_item(year=year, version=version)
            efda_collection.add_item(item)
    catalog.add_child(efda_collection)

    # Normalize all HREFs (ensures correct relative paths)
    catalog.normalize_hrefs(BASE_S3_URL)
    catalog.save()

    return catalog

