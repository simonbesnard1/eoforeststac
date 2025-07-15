import pystac
from foreststac.config import BASE_S3_URL
from foreststac.io import register_io
from foreststac.gami import create_gami_collection, create_gami_item

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

    # Normalize all HREFs (ensures correct relative paths)
    catalog.normalize_hrefs(BASE_S3_URL)
    catalog.save()

    return catalog

