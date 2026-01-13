import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

FORESTPATHS_GENUS_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "FORESTPATHS_GENUS",
    "title": "ForestPaths – European Tree Genus Map 2020 (10 m)",
    "description": (
        "European tree genus map at 10 m resolution for year 2020 (early access). "
        "Derived from Sentinel-1 and Sentinel-2 time series using a CatBoost model trained on "
        "forest inventories, citizen science observations, orthophoto interpretation, and LUCAS.\n\n"
        "The map distinguishes eight classes including Larix, Picea, Pinus, Fagus, and Quercus.\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-35.0, 34.0, 45.0, 72.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-35.0, 34.0],
            [-35.0, 72.0],
            [ 45.0, 72.0],
            [ 45.0, 34.0],
            [-35.0, 34.0],
        ]],
    },
    "start_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/FORESTPATHS_GENUS/collection.json",
    "base_path": f"{BASE_S3_URL}/FORESTPATHS_GENUS",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    # Replace "various" with the exact license string from Zenodo once confirmed.
    "license": "various",
    "providers": [
        {
            "name": "ForestPaths Consortium",
            "roles": ["producer"],
            "url": "https://forestpaths.eu",
        },
        {
            "name": "VITO – Flemish Institute for Technological Research",
            "roles": ["producer"],
            "url": "https://vito.be",
        },
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    "keywords": [
        "tree genus",
        "forest composition",
        "Europe",
        "Sentinel-1",
        "Sentinel-2",
        "CatBoost",
        "machine learning",
        "classification",
        "ForestPaths",
        "zarr",
        "stac",
    ],
    "themes": ["forest structure", "species composition", "classification"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
    
        # Canonical citation / landing pages
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5281/zenodo.13341104",
            "type": "text/html",
            "title": "Zenodo dataset (European Tree Genus Map 2020 – Early Access)",
        },
        {
            "rel": "about",
            "href": "https://zenodo.org/records/13341104",
            "type": "text/html",
            "title": "Dataset landing page",
        },
        {
            "rel": "related",
            "href": "https://forestpaths.eu/news/early-access-release-forestpaths-european-tree-genus-map",
            "type": "text/html",
            "title": "Release announcement (ForestPaths)",
        },
    ],

    # ------------------------------------------------------------------
    # Extensions (signal what fields might exist in items/assets)
    # ------------------------------------------------------------------
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
        "https://stac-extensions.github.io/file/v2.1.0/schema.json",
        "https://stac-extensions.github.io/raster/v1.1.0/schema.json",
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",
        "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Summaries (client-friendly structured metadata)
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["static"],

        # core data semantics
        "variables": ["genus"],
        "units": ["categorical"],

        # spatial metadata
        "eo:gsd": [10.0],
        "proj:epsg": [3035],

        "data_format": ["zarr"],

        # classification legend (0..7)
        "classes": [
            {"value": 0, "name": "Larix"},
            {"value": 1, "name": "Picea"},
            {"value": 2, "name": "Pinus"},
            {"value": 3, "name": "Fagus"},
            {"value": 4, "name": "Quercus"},
            {"value": 5, "name": "Other needleleaf"},
            {"value": 6, "name": "Other broadleaf"},
            {"value": 7, "name": "No trees"},
        ],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Cloud-optimized Zarr store of the ForestPaths tree genus classification map (2020).",
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
        "thumbnail": {
            "title": "Preview",
            "roles": ["thumbnail"],
            "type": "image/png",
        },
    },

    # ------------------------------------------------------------------
    # Asset template (roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/FORESTPATHS_GENUS_v{v}.zarr",
            title=f"ForestPaths – Tree genus map 2020 (Zarr) v{v}",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store packaging of the ForestPaths European tree genus map for 2020 "
                "(categorical classification with eight classes)."
            ),
        ),
    },
}
