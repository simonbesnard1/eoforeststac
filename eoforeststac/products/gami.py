import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

GAMI_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "GAMI",
    "title": "Global Age Mapping Integration (GAMI) – Global forest age (100 m)",
    "description": (
        "Global gridded forest age product derived by integrating machine-learning models with "
        "remote sensing predictors and reference forest inventory information. "
        "Provides spatially explicit forest age estimates and uncertainty.\n\n"
        "Temporal semantics: GAMI is a static age map referenced to a specific year or reference period "
        "(depending on version). The temporal extent below denotes the reference period/years used for "
        "harmonization; each item/version can document its exact reference year(s).\n\n"
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
    "start_datetime": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # Keep your note (useful for provenance; can be carried into extra_fields later)
    "temporal_notes": (
        "Temporal extent denotes the reference period/years used for harmonization. "
        "For each version, items describe the exact reference year(s) of age estimates."
    ),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/GAMI/collection.json",
    "base_path": f"{BASE_S3_URL}/GAMI",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    # Replace "various" with the exact license when you want it strict (e.g., CC-BY-4.0).
    "license": "various",
    "providers": [
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["producer", "processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    "keywords": [
        "forest age",
        "stand age",
        "demography",
        "machine learning",
        "remote sensing",
        "forest inventory",
        "carbon cycle",
        "global",
        "zarr",
        "stac",
    ],
    "themes": ["forest structure", "carbon", "demography"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
      
        # Canonical citation + paper
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5880/GFZ.1.4.2023.006",
            "type": "text/html",
            "title": "GAMI dataset DOI (GFZ Data Services)",
        },
        {
            "rel": "related",
            "href": "https://doi.org/10.5194/essd-13-4881-2021",
            "type": "text/html",
            "title": "Peer-reviewed paper (ESSD, 2021)",
        },

        # Your packaging project
        {
            "rel": "about",
            "href": "https://github.com/simonbesnard1/eoforeststac",
            "type": "text/html",
            "title": "STAC packaging project (EOForestSTAC)",
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
        "variables": ["forest_age", "forest_age_uncertainty"],
        "units": ["years"],

        # Keep consistent with your other collections
        "eo:gsd": [100.0],
        "proj:epsg": [4326],

        "product_family": ["GAMI"],
        "data_format": ["zarr"],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Cloud-optimized Zarr store of global forest age estimates (and uncertainty).",
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
            href=f"{cfg['base_path']}/GAMI_v{v}.zarr",
            title=f"GAMI v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing global forest age estimates "
                "and associated uncertainty layers."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes (UI / provenance helper)
    # ------------------------------------------------------------------
    "version_notes": {
        "2.0": "Initial public release.",
        "2.1": "Incremental updates and/or bug fixes.",
        "3.0": "Major update (methods/data).",
        "3.1": "Minor update (methods/data).",
    },
}
