import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

HANSEN_GFC_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "HANSEN_GFC",
    "title": "Hansen Global Forest Change (GFC) – Tree cover and annual loss/gain (30 m)",
    "description": (
        "Global Forest Change (GFC) dataset derived from time-series analysis of Landsat imagery, "
        "characterizing percent tree cover for year 2000, annual tree cover loss (2001 onward), "
        "tree cover gain (2000–2012), and a data mask.\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
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
        ]],
    },
    "start_datetime": datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2024, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/HANSEN_GFC/collection.json",
    "base_path": f"{BASE_S3_URL}/HANSEN_GFC",

    # ------------------------------------------------------------------
    # Governance
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
        "Landsat",
        "global",
        "deforestation",
        "GLAD",
        "UMD",
        "zarr",
        "stac",
    ],
    "themes": ["disturbance", "forest structure", "land cover change"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
        
        # Official documentation / access points
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

        # Canonical citation
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.1126/science.1244693",
            "type": "text/html",
            "title": "Hansen et al., Science (2013) – primary citation",
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
        "temporal_resolution": ["annual"],
        "variables": [
            "treecover2000",
            "loss",
            "lossyear",
            "gain",
            "datamask",
        ],
        
        # keep a simple global units list AND keep your detailed mapping
        "units_by_variable": {
            "treecover2000": "percent",
            "loss": "binary",
            "lossyear": "year",
            "gain": "binary",
            "datamask": "binary"
        },
        
        # Spatial metadata
        "eo:gsd": [30.0],        # often reported ~30.92 m; keep 30 m as a clean atlas value
        "proj:epsg": [4326],

        "data_format": ["zarr"],

        # Dataset-specific semantics
        "gain_period": ["2000–2012"],
        "loss_period": ["2001–2024"],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Cloud-optimized Zarr store of Hansen Global Forest Change layers.",
            "roles": ["data"],
            "type": "application/vnd.zarr",
        }
    },

    # ------------------------------------------------------------------
    # Asset template (roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/HANSEN_GFC_v{v}.zarr",
            title=f"Hansen GFC v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing Hansen Global Forest Change layers "
                "(tree cover 2000, annual loss year, gain, and data mask)."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes
    # ------------------------------------------------------------------
    "version_notes": {
        "1.12": "Update covering tree cover loss through year 2024 (GFC-2024 v1.12).",
    },
}
