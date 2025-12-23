# eoforeststac/products/liu_biomass.py

import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

LIU_BIOMASS_CFG = {
    "id": "LIU_BIOMASS",
    "title": "Canopy Height, Cover and Aboveground Biomass across Europe (Liu et al.)",
    "description": (
        "European canopy cover, canopy height, and aboveground biomass maps "
        "derived from 3 m PlanetScope imagery and aerial LiDAR canopy height models "
        "using deep learning. Biomass is estimated at 30 m resolution from canopy "
        "cover and height via allometric equations. "
        "The dataset accompanies the study "
        "'The overlooked contribution of trees outside forests to tree cover and "
        "woody biomass across Europe'.\n\n"
        "IMPORTANT: This dataset is restricted to research and scientific use only "
        "and must not be used for commercial purposes, in accordance with the "
        "Planet Labs Education and Research license."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    # Europe-wide product in ETRS89 / LAEA Europe
    "bbox": [-25.0, 34.0, 45.0, 72.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-25.0, 34.0],
            [-25.0, 72.0],
            [ 45.0, 72.0],
            [ 45.0, 34.0],
            [-25.0, 34.0],
        ]]
    },

    # Reference year of PlanetScope imagery
    "start_datetime": datetime.datetime(
        2019, 1, 1, tzinfo=datetime.timezone.utc
    ),
    "end_datetime": datetime.datetime(
        2019, 12, 31, tzinfo=datetime.timezone.utc
    ),

    # ------------------------------------------------------------------
    # STAC paths
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/LIU_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/LIU_BIOMASS",

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------
    "providers": [
        {
            "name": "University of Copenhagen",
            "roles": ["producer"],
            "url": "https://zenodo.org/records/8154445",
        },
        {
            "name": "Planet Labs Inc.",
            "roles": ["host"],
            "url": "https://www.planet.com/",
        },
    ],

    # ------------------------------------------------------------------
    # Licensing / usage constraints (VERY IMPORTANT HERE)
    # ------------------------------------------------------------------
    "license": "proprietary",
    "keywords": [
        "aboveground biomass",
        "canopy height",
        "canopy cover",
        "trees outside forests",
        "PlanetScope",
        "Europe",
    ],

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/LIU_BIOMASS_v{v}.zarr",
            title=f"European Aboveground Biomass and Canopy Structure v{v}"
        )
    },
}
