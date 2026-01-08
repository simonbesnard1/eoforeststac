import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

POTAPOV_HEIGHT_CFG = {
    "id": "POTAPOV_HEIGHT",
    "title": "Global Canopy Height (Potapov et al.)",
    "description": (
        "Global canopy height maps provided for multiple reference years (2005, 2010, 2015, 2020). "
        "The product integrates spaceborne LiDAR information with optical imagery "
        "to produce gridded canopy height estimates. See the dataset documentation for full processing "
        "details and citation guidance."
    ),

    # ------------------------------------------------------------------
    # Spatial extent
    # ------------------------------------------------------------------
    "bbox": [-180, -90, 180, 90],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]],
    },

    # Temporal coverage: earliest to latest epoch in your product
    "start_datetime": datetime.datetime(2005, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC wiring
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/POTAPOV_HEIGHT/collection.json",
    "base_path": f"{BASE_S3_URL}/POTAPOV_HEIGHT",

    # ------------------------------------------------------------------
    # Governance / provenance
    # ------------------------------------------------------------------
    "license": "various",

    "providers": [
        {"name": "Dataset authors / original providers", "roles": ["producer"], "url": "https://glad.umd.edu/"},
        {"name": "GFZ Helmholtz Centre Potsdam", "roles": ["processor", "host"], "url": "https://www.gfz.de"},
    ],

    "keywords": [
        "canopy height",
        "vegetation height",
        "forest structure",
        "global",
        "LiDAR",
        "multi-epoch",
    ],

    # Add the correct DOI/landing page here when you have it.
    "links": [
        {"rel": "cite-as", "href": "https://doi.org/10.1016/j.rse.2020.112165", "type": "text/html", "title": "Dataset DOI"}
    ],

    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
    ],

    "summaries": {
        "temporal_resolution": ["multi-epoch"],
        "reference_years": [2005, 2010, 2015, 2020],
        "variables": ["canopy_height"],
        "units": ["m"],
        "lidar_sources": ["ICESat-2", "GEDI"],
    },

    # ------------------------------------------------------------------
    # Assets (roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/POTAPOV_HEIGHT_v{v}.zarr",
            title=f"Global canopy height {v} (Zarr)",
            roles=["data"],
            description=(
                "Zarr packaging of the global canopy height layer for the given reference year/epoch. "
                "Part of a multi-epoch canopy height product (2005/2010/2015/2020) integrating LiDAR "
                "information including ICESat-2."
            ),
        )
    },

    # Optional: give meaning to version strings if you use them as epochs
    "version_notes": {
        "2005": "Canopy height for reference year 2005.",
        "2010": "Canopy height for reference year 2010.",
        "2015": "Canopy height for reference year 2015.",
        "2020": "Canopy height for reference year 2020.",
    },
}

