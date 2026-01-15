import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

JRC_TMF_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "JRC_TMF",
    "title": "JRC Tropical Moist Forests (TMF) - Forest change (degradation, deforestation, regrowth) (30m)",
    "description": (
        "Pan-tropical dataset on forest cover change in tropical moist forests (TMF) derived from "
        "Landsat time series. Wall-to-wall maps depict TMF extent and disturbances (deforestation "
        "and degradation) as well as post-deforestation recovery (forest regrowth).\n\n"
        "The product is distributed via two complementary components: a transition map and an annual "
        "change collection.\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -30.0, 180.0, 30.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-180.0, -30.0],
            [-180.0,  30.0],
            [ 180.0,  30.0],
            [ 180.0, -30.0],
            [-180.0, -30.0],
        ]],
    },
    "start_datetime": datetime.datetime(1990, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2024, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/JRC_TMF/collection.json",
    "base_path": f"{BASE_S3_URL}/JRC_TMF",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "various",
    "providers": [
        {
            "name": "European Commission – Joint Research Centre (JRC)",
            "roles": ["producer"],
            "url": "https://forobs.jrc.ec.europa.eu/TMF",
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
        "tropical moist forest",
        "TMF",
        "Landsat",
        "forest change",
        "deforestation",
        "degradation",
        "regrowth",
        "annual change",
        "transition map",
        "pantropical",
        "zarr",
        "stac",
    ],
    "themes": ["disturbance", "land cover change", "carbon"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
        
        # Official resources
        {
            "rel": "about",
            "href": "https://forobs.jrc.ec.europa.eu/TMF",
            "type": "text/html",
            "title": "JRC Forest Observations – TMF overview",
        },
        {
            "rel": "related",
            "href": "https://forobs.jrc.ec.europa.eu/TMF/data",
            "type": "text/html",
            "title": "TMF data access (downloads, versions)",
        },
        {
            "rel": "documentation",
            "href": "https://forobs.jrc.ec.europa.eu/TMF/download/TMF_DataUsersGuide.pdf",
            "type": "application/pdf",
            "title": "TMF Data Users Guide (PDF)",
        },
        {
            "rel": "related",
            "href": "https://forobs.jrc.ec.europa.eu/TMF/explorer",
            "type": "text/html",
            "title": "TMF Explorer (interactive viewer)",
        },

        # Canonical citation
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.1126/sciadv.abe1603",
            "type": "text/html",
            "title": "Vancutsem et al., Science Advances (2021) – key paper",
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

        # keep these conservative unless you want to enumerate actual band names
        "variables": ["AnnualChange", "DeforestationYear", "DegradationYear", "TransitionMap_MainClasses", "TransitionMap_Subtypes", "UndisturbedDegradedForest"],
        
        "units_by_variable": {"AnnualChange": "categorical",
                              "DeforestationYear": "year",
                              "DegradationYear": "year",
                              "TransitionMap_MainClasses": "categorical",
                              "TransitionMap_Subtypes": "categorical",
                              "UndisturbedDegradedForest": "binary",
                              },
        
        # spatial metadata
        "eo:gsd": [30.0],
        "proj:epsg": [4326],  # swap if your Zarr is stored in another CRS

        "data_format": ["zarr"],

        "layers_note": [
            "TMF dataset contains multiple layers including annual change and transition products (see user guide)."
        ],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store of JRC TMF layers (annual change + transition products) "
                "covering 1990–2024."
            ),
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
            href=f"{cfg['base_path']}/JRC_TMF_v{v}.zarr",
            title=f"JRC TMF v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing the JRC Tropical Moist Forests dataset, "
                "including TMF extent and change information (degradation, deforestation, regrowth) "
                "from 1990–2024 derived from Landsat time series."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes (optional)
    # ------------------------------------------------------------------
    "version_notes": {
        "2024": "Includes annual change collection through year 2024 (per TMF user guide / portal).",
    },
}
