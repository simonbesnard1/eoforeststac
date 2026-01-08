import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

JRC_TMF_CFG = {
    "id": "JRC_TMF",
    "title": "JRC Tropical Moist Forests (TMF) – Forest cover change, degradation, deforestation, regrowth (1990–2024)",
    "description": (
        "Pan-tropical dataset on forest cover change in tropical moist forests (TMF) derived from "
        "Landsat time series. Wall-to-wall maps depict TMF extent and disturbances (deforestation "
        "and degradation) as well as post-deforestation recovery (forest regrowth). Distributed via "
        "two complementary products: a transition map and an annual change collection."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    # Tropical moist forest belt is not exactly [-30, 30], but your bbox is a safe envelope.
    "bbox": [-180, -30, 180, 30],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180, -30], [-180, 30], [180, 30], [180, -30], [-180, -30]]],
    },

    # JRC indicates annual collection from 1990 to 2024 (35 maps). :contentReference[oaicite:5]{index=5}
    "start_datetime": datetime.datetime(1990, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2024, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC wiring
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/JRC_TMF/collection.json",
    "base_path": f"{BASE_S3_URL}/JRC_TMF",

    # ------------------------------------------------------------------
    # Governance / provenance
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

    "keywords": [
        "tropical moist forest",
        "TMF",
        "Landsat",
        "deforestation",
        "degradation",
        "regrowth",
        "annual change",
        "transition map",
        "pantropical",
    ],

    # ------------------------------------------------------------------
    # Canonical links
    # ------------------------------------------------------------------
    "links": [
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
        {
            "rel": "related",
            "href": "https://doi.org/10.1126/sciadv.abe1603",
            "type": "text/html",
            "title": "Vancutsem et al., Science Advances (2021) – key paper",
        },
    ],

    # ------------------------------------------------------------------
    # Extensions (optional)
    # ------------------------------------------------------------------
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Structured summaries
    # ------------------------------------------------------------------
    "summaries": {
        # JRC overview mentions 0.09 ha resolution (~30m Landsat). :contentReference[oaicite:6]{index=6}
        "eo:gsd": [30],
        "temporal_resolution": ["annual"],
        "products": ["transition_map", "annual_change_collection"],
        # JRC describes deforestation, degradation and regrowth explicitly. :contentReference[oaicite:7]{index=7}
        "change_processes": ["degradation", "deforestation", "regrowth"],
        # This list is intentionally generic; exact band names/classes are in the user guide. :contentReference[oaicite:8]{index=8}
        "layers_note": ["TMF dataset contains multiple layers including annual change and transition products (see user guide)."],
    },

    # ------------------------------------------------------------------
    # Assets (roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/JRC_TMF_v{v}.zarr",
            title=f"JRC TMF v{v} (Zarr)",
            roles=["data"],
            description=(
                "Zarr packaging of the JRC Tropical Moist Forests dataset, including "
                "TMF extent and change information (degradation, deforestation, regrowth) "
                "from 1990–2024 derived from Landsat time series."
            ),
        )
    },

    # Optional, if you use version tags like '2024' or 'v2023' in your DEFAULT_VERSIONS:
    "version_notes": {
        "2024": "Includes annual change collection through year 2024 (per TMF user guide / portal).",
    },
}

