# eoforeststac/products/hansen_gfc.py

import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

HANSEN_GFC_CFG = {
    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    "id": "HANSEN_GFC",
    "title": "Hansen Global Forest Change",
    "description": (
        "Global Forest Change (GFC) dataset derived from time-series analysis of Landsat imagery, "
        "characterizing global tree cover and tree cover loss from 2000 through 2024, and tree cover "
        "gain for 2000–2012. Includes percent tree cover for year 2000, annual loss year, gain, and a "
        "data mask."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -90.0, 180.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-180.0, -90.0],
            [-180.0,  90.0],
            [ 180.0,  90.0],
            [ 180.0, -90.0],
            [-180.0, -90.0],
        ]]
    },
    "start_datetime": datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2024, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC paths (your packaging)
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/HANSEN_GFC/collection.json",
    "base_path": f"{BASE_S3_URL}/HANSEN_GFC",

    # ------------------------------------------------------------------
    # Governance / provenance
    # ------------------------------------------------------------------
    # License varies by distribution channel; set explicitly if you want strictness.
    "license": "various",

    "providers": [
        {
            "name": "University of Maryland (GLAD), Department of Geographical Sciences",
            "roles": ["producer"],
            "url": "https://glad.umd.edu",
        },
        {
            "name": "Google Earth Engine",
            "roles": ["host"],
            "url": "https://developers.google.com/earth-engine",
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
        "tree cover",
        "forest change",
        "tree cover loss",
        "tree cover gain",
        "landsat",
        "global",
        "deforestation",
        "UMD GLAD",
    ],

    # ------------------------------------------------------------------
    # STAC links (preferred over ad-hoc references)
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "about",
            "href": "https://developers.google.com/earth-engine/datasets/catalog/UMD_hansen_global_forest_change_2024_v1_12",
            "type": "text/html",
            "title": "Earth Engine data catalog entry (bands, pixel size, mask)",
        },
        {
            "rel": "related",
            "href": "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html",
            "type": "text/html",
            "title": "Official data download page (GeoTIFF tiles)",
        },
        {
            "rel": "related",
            "href": "https://glad.earthengine.app/view/global-forest-change",
            "type": "text/html",
            "title": "Web visualization (Global Forest Change app)",
        },
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.1126/science.1244693",
            "type": "text/html",
            "title": "Hansen et al., Science (2013) – primary citation",
        },
    ],

    # ------------------------------------------------------------------
    # Extensions (optional but nice)
    # ------------------------------------------------------------------
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Structured summaries (truthful + useful)
    # ------------------------------------------------------------------
    "summaries": {
        # Earth Engine page reports pixel size ~30.92 m and includes key bands. :contentReference[oaicite:3]{index=3}
        "eo:gsd": [30.92],
        "temporal_resolution": ["annual"],
        "variables": [
            "treecover2000",
            "loss",
            "lossyear",
            "gain",
            "datamask"
        ],
        # Definition note (trees ≥ 5m) comes from the GLAD visualization / docs. :contentReference[oaicite:4]{index=4}
        "tree_definition": ["vegetation taller than 5 m"],
        "gain_period": ["2000–2012"],
    },

    # ------------------------------------------------------------------
    # Assets (your packaged format)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/HANSEN_GFC_v{v}.zarr",
            title=f"Hansen GFC v{v} (Zarr)",
            roles=["data"],
            description="Zarr store of Global Forest Change.",
        )
    },

    # ------------------------------------------------------------------
    # Optional: version notes
    # ------------------------------------------------------------------
    "version_notes": {
        "1.12": "Update covering loss through year 2024 (GFC-2024).",
    },
}

