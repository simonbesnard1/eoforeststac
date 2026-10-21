import datetime
from eoforeststac.core.config import S3_HTTP_BASE

# ------------------------------------------------------------------
# Per-region definitions
# ------------------------------------------------------------------

REGIONS = {
    "finland": {
        "label": "Finland",
        "description": (
            "wip"
        ),
        "bbox": [-9.5, 35.9, 4.4, 43.8],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-9.5, 35.9],
                    [-9.5, 43.8],
                    [4.4, 43.8],
                    [4.4, 35.9],
                    [-9.5, 35.9],
                ]
            ],
        },
        "proj_epsg": 25830,
        "start_datetime": datetime.datetime(2015, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ALS_BIOMASS_FINLAND",
    },
}

# ------------------------------------------------------------------
# Collection-level config
# ------------------------------------------------------------------
ALS_BIOMASS_PRODUCTS_CFG = {
    "id": "ALS_BIOMASS_PRODUCTS",
    "short_title": "ALS Biomass Products",
    "title": "ALS Biomass Products",
    "description": (
        "⚠️ This collection is under active development. Data coverage, variables, "
        "and metadata are subject to change without notice.\n\n"
    ),
    "bbox": [-180.0, -90.0, 180.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-180.0, -90.0],
                [-180.0, 90.0],
                [180.0, 90.0],
                [180.0, -90.0],
                [-180.0, -90.0],
            ]
        ],
    },
    "start_datetime": datetime.datetime(2015, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),
    "collection_href": f"{S3_HTTP_BASE}/ALS_BIOMASS_PRODUCTS/collection.json",
    "base_path": f"{S3_HTTP_BASE}/ALS_BIOMASS_PRODUCTS",
    "license": "EUPL-1.2",
    "providers": [
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["producer", "processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],
    "keywords": [
        "experimental",
    ],
    "themes": ["lidar", "forest structure", "canopy height"],
    "links": [
        {
            "rel": "about",
            "href": "https://github.com/simonbesnard1/alsdb",
            "type": "text/html",
            "title": "alsdb processing pipeline",
        },
        {
            "rel": "cite-as",
            "href": "https://github.com/simonbesnard1/alsdb",
            "type": "text/html",
            "title": "alsdb – ALS gridded products pipeline (cite repository until DOI is available)",
        },
    ],
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
        "https://stac-extensions.github.io/file/v2.1.0/schema.json",
        "https://stac-extensions.github.io/raster/v1.1.0/schema.json",
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",
    ],
    "summaries": {
        "temporal_resolution": ["multi-year"],
        "variables": [
        ],
        "units_by_variable": {
        },
        "spatial_resolutions": "10m",
        "proj:epsg": sorted({r["proj_epsg"] for r in REGIONS.values()}),
        "product_family": ["alsdb"],
        "data_format": ["zarr"],
    },
    "raster_bands": {
    },
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "wip"
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
    },
    "regions": REGIONS,
}
