import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

EFDA_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "EFDA",
    "title": "European Forest Disturbance Atlas (EFDA) – Annual disturbance maps for Europe (30 m)",
    "description": (
        "Annual forest disturbance maps for continental Europe derived from Landsat time series. "
        "The dataset includes annual layers describing disturbance occurrence, severity, and causal "
        "agent, as well as summary layers (e.g., number of disturbances and latest/greatest disturbance year).\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-25.0, 34.0, 45.0, 72.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-25.0, 34.0],
            [-25.0, 72.0],
            [ 45.0, 72.0],
            [ 45.0, 34.0],
            [-25.0, 34.0],
        ]],
    },
    "start_datetime": datetime.datetime(1985, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/EFDA/collection.json",
    "base_path": f"{BASE_S3_URL}/EFDA",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    # If Zenodo specifies a single license, replace "various" with it.
    "license": "various",
    "providers": [
        {
            "name": "Technical University of Munich (TUM) – Earth Observation for Ecosystem Management",
            "roles": ["producer"],
            "url": "https://www.lss.ls.tum.de/en/eoem/",
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
        "forest disturbance",
        "disturbance agent",
        "severity",
        "Landsat",
        "Europe",
        "annual",
        "30 m",
        "harvest",
        "wind",
        "bark beetle",
        "fire",
        "monitoring",
        "zarr",
        "stac",
    ],
    "themes": ["disturbance", "forest structure", "carbon"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
       
        # Official dataset / paper
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5194/essd-17-2373-2025",
            "type": "text/html",
            "title": "ESSD paper describing EFDA (2025)",
        },
        
        {
            "rel": "related",
            "href": "https://doi.org/10.5281/zenodo.13333034",
            "type": "text/html",
            "title": "Zenodo dataset (EFDA)",
        },
        {
            "rel": "about",
            "href": "https://www.lss.ls.tum.de/en/eoem/datasets/european-forest-disturbance-atlas-efda/",
            "type": "text/html",
            "title": "Dataset page (TUM EOEM)",
        },

        # Community / interactive resources
        {
            "rel": "related",
            "href": "https://albaviana.users.earthengine.app/view/european-forest-disturbance-map",
            "type": "text/html",
            "title": "Online EFDA map viewer (GEE app)",
        },
        {
            "rel": "related",
            "href": "https://github.com/albaviana/European-Forest-Disturbance-Atlas",
            "type": "text/html",
            "title": "Project repository / processing overview",
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
        "temporal_resolution": ["annual"],
        "variables": [
            "disturbance_occurrence",
            "disturbance_severity",
            "disturbance_agent",
            "number_of_disturbances",
            "latest_disturbance_year",
            "greatest_disturbance_year",
        ],
        "units": ["1", "categorical", "year"],  # loose but helpful; refine if you standardize variable metadata
        "platform": ["Landsat"],

        # spatial metadata (keep consistent with CCI style)
        "eo:gsd": [30.0],
        "proj:epsg": [3035],

        "product_family": ["European Forest Disturbance Atlas (EFDA)"],
        "data_format": ["zarr"],

        # Dataset-specific structured helpers
        "disturbance_agents": ["wind_bark_beetle", "fire", "harvest", "mixed"],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Cloud-optimized Zarr store of EFDA layers (annual + summary).",
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
            href=f"{cfg['base_path']}/EFDA_v{v}.zarr",
            title=f"EFDA v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing EFDA annual disturbance layers "
                "(occurrence, severity, agent) and summary layers."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes (UI / provenance helper)
    # ------------------------------------------------------------------
    "version_notes": {
        "2.0.0": "Initial version covering 1985–2021.",
        "2.1.0": "Updated to 1985–2023; added forest land-use layer and annual stacks including probabilities and agents.",
        "2.1.1": "Improvements to disturbance maps and added a disturbance severity layer.",
    },
}
