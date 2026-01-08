import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

FORESTPATHS_GENUS_CFG = {
    "id": "FORESTPATHS_GENUS",
    "title": "ForestPaths – European Tree Genus Map 2020",
    "description": (
        "Early access European tree genus map at 10 m resolution for year 2020. "
        "Derived from Sentinel-1 and Sentinel-2 data using a CatBoost model trained on "
        "forest inventories, citizen science observations, orthophoto interpretation, and LUCAS. "
        "Map distinguishes eight classes including Larix, Picea, Pinus, Fagus, and Quercus."
    ),

    # ------------------------------------------------------------------
    # Spatial (Europe)
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

    # ------------------------------------------------------------------
    # Temporal (nominal year 2020; still represented as an interval)
    # ------------------------------------------------------------------
    "start_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC wiring
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/FORESTPATHS_GENUS/collection.json",
    "base_path": f"{BASE_S3_URL}/FORESTPATHS_GENUS",

    # ------------------------------------------------------------------
    # Governance / provenance
    # ------------------------------------------------------------------
    # Zenodo record provides a "How to cite" with authors + year + title + DOI.
    # If you know the license from Zenodo UI, set it explicitly; otherwise keep "various".
    "license": "various",

    "providers": [
        # Producer(s)
        {
            "name": "ForestPaths Consortium",
            "roles": ["producer"],
            "url": "https://forestpaths.eu",
        },
        # Key institutional contributors mentioned (VITO, TUM) — keep as providers for discoverability
        {
            "name": "VITO – Flemish Institute for Technological Research",
            "roles": ["producer"],
            "url": "https://vito.be",
        },
        # Your packaging/hosting
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
        "Europe",
        "Sentinel-1",
        "Sentinel-2",
        "machine learning",
        "ForestPaths"
    ],

    # ------------------------------------------------------------------
    # Canonical citation and related resources
    # ------------------------------------------------------------------
    "links": [
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
            "title": "ForestPaths news post (release announcement)",
        },
    ],

    # ------------------------------------------------------------------
    # STAC extensions (optional but very useful for this product)
    # ------------------------------------------------------------------
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
        # "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Structured summaries (client-friendly)
    # ------------------------------------------------------------------
    "summaries": {
        # grounded in Zenodo description
        "eo:gsd": [10],              # 10 m resolution :contentReference[oaicite:1]{index=1}
        "proj:epsg": [3035],         # EPSG:3035 :contentReference[oaicite:2]{index=2}
        "temporal_resolution": ["static"],

        # classification legend (0..7) :contentReference[oaicite:3]{index=3}
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

        # tiling & original distribution format (COG tiles 100 km grid) :contentReference[oaicite:4]{index=4}
        "tiling": ["100km grid"],
        "distribution_original": ["Cloud Optimized GeoTIFF (COG) tiles"],
    },

    # ------------------------------------------------------------------
    # Assets (your packaged format)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/FORESTPATHS_GENUS_v{v}.zarr",
            title=f"ForestPaths tree genus map 2020 (Zarr) – v{v}",
            roles=["data"],
            description="Zarr store packaging of the ForestPaths genus map.",
        ),
    },
}

