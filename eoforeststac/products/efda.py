import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

EFDA_CFG = {
    # ---- Identity ----
    "id": "EFDA",
    "title": "European Forest Disturbance Atlas (EFDA) – Annual disturbances for Europe (Landsat)",
    "description": (
        "Annual forest disturbance maps for continental Europe derived from Landsat time series. "
        "Includes annual layers on disturbance occurrence, severity, and causal agent, as well as "
        "summary layers such as number of disturbances and latest/greatest disturbance year."
    ),

    # ---- Spatial / temporal extent ----
    "bbox": [-25, 34, 45, 72],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-25, 34], [-25, 72], [45, 72], [45, 34], [-25, 34]]],
    },
    "start_datetime": datetime.datetime(1985, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),

    # ---- Publishing / href layout ----
    "collection_href": f"{BASE_S3_URL}/EFDA/collection.json",
    "base_path": f"{BASE_S3_URL}/EFDA",

    # ---- Governance ----
    # Replace with the exact Zenodo license if you want it strict; "various" is safe.
    "license": "various",

    "providers": [
        # Dataset/paper authors & institution (producer)
        {
            "name": "Technical University of Munich (TUM) – Earth Observation for Ecosystem Management",
            "roles": ["producer"],
            "url": "https://www.lss.ls.tum.de/en/eoem/",
        },
        # Your packaging/hosting role
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],

    # ---- Discovery ----
    "keywords": [
        "forest disturbance",
        "Landsat",
        "Europe",
        "annual",
        "severity",
        "disturbance agent",
        "harvest",
        "wind",
        "bark beetle",
        "fire",
        "ForestPaths",
        "monitoring",
    ],

    # ---- Canonical citations / landing pages ----
    "links": [
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5281/zenodo.13333034",
            "title": "Zenodo dataset (EFDA)",
        },
        {
            "rel": "related",
            "href": "https://doi.org/10.5194/essd-17-2373-2025",
            "title": "ESSD paper describing EFDA (2025)",
        },
        {
            "rel": "about",
            "href": "https://www.lss.ls.tum.de/en/eoem/datasets/european-forest-disturbance-atlas-efda/",
            "title": "Dataset page (TUM EOEM)",
        },
        {
            "rel": "related",
            "href": "https://albaviana.users.earthengine.app/view/european-forest-disturbance-map",
            "title": "Online EFDA map viewer (GEE app)",
        },
        {
            "rel": "related",
            "href": "https://github.com/albaviana/European-Forest-Disturbance-Atlas",
            "title": "Project repository / processing overview",
        },
    ],

    # ---- Extensions (optional but helpful) ----
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
        # If you later add DOI/citation fields as structured scientific extension:
        # "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
    ],

    # ---- Structured summaries (client-friendly) ----
    "summaries": {
        "temporal_resolution": ["annual"],
        "platform": ["Landsat"],  # safe per paper
        "variables": [
            "disturbance_occurrence",
            "disturbance_severity",
            "disturbance_agent",
            "number_of_disturbances",
            "latest_disturbance_year",
            "greatest_disturbance_year",
        ],
        "disturbance_agents": ["wind_bark_beetle", "fire", "harvest", "mixed"],
        "coverage_countries_count": [38],  # from TUM dataset page summary
    },

    # ---- Asset template ----
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/EFDA_v{v}.zarr",
            title=f"EFDA v{v} (Zarr)",
            roles=["data"],
            description="Zarr store of EFDA layers (annual + summary).",
        ),
    },

    # ---- Version notes (optional but useful for UI / provenance) ----
    "version_notes": {
        "2.0.0": "Initial version covering 1985–2021.",
        "2.1.0": "Updated to 1985–2023; added forest land-use layer and annual stacks including probabilities and agents.",
        "2.1.1": "Improvements to disturbance maps and added a disturbance severity layer.",
    },
}

