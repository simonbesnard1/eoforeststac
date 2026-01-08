# eoforeststac/products/liu_biomass.py

import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

LIU_BIOMASS_CFG = {
    "id": "LIU_BIOMASS",
    "title": "Europe – Canopy Cover, Canopy Height, and Aboveground Biomass (Liu et al., 2019 reference imagery)",
    "description": (
        "European maps of canopy cover, canopy height, and aboveground biomass derived from "
        "high-resolution PlanetScope imagery and airborne LiDAR canopy height models using deep learning. "
        "The Zenodo release includes aggregated canopy cover/height products and a biomass map at 30 m "
        "resolution computed from canopy cover and height using allometric equations.\n\n"
        "IMPORTANT – Usage restrictions: This dataset is provided for non-commercial scientific, "
        "education, and research purposes only, reflecting restrictions associated with PlanetScope "
        "imagery access under research licensing. Users must not use the dataset for commercial purposes "
        "and should follow the dataset’s stated data agreement and citation requirements."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent (Europe; nominal 2019 reference mosaics)
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
        ]]
    },
    "start_datetime": datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2019, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC paths
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/LIU_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/LIU_BIOMASS",

    # ------------------------------------------------------------------
    # Governance / provenance
    # ------------------------------------------------------------------
    # Zenodo is the canonical landing; paper is the canonical scientific citation.
    "providers": [
        {
            "name": "University of Copenhagen (dataset authors: Liu et al.)",
            "roles": ["producer"],
            "url": "https://zenodo.org/records/8154445",
        },
        {
            "name": "Planet Labs PBC",
            "roles": ["licensor"],
            "url": "https://www.planet.com/",
        },
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],

    # ------------------------------------------------------------------
    # Licensing / usage constraints (core of this product)
    # ------------------------------------------------------------------
    # STAC 'license' wants a short token; "proprietary" is OK, but add explicit notes.
    "license": "proprietary",
    "license_notes": (
        "Non-commercial scientific/education/research use only. "
        "Derived from PlanetScope imagery accessed under a research license; "
        "see Zenodo record and Planet Education & Research terms for details."
    ),

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    "keywords": [
        "aboveground biomass",
        "biomass",
        "canopy height",
        "canopy cover",
        "trees outside forests",
        "PlanetScope",
        "LiDAR",
        "deep learning",
        "Europe",
        "non-commercial",
    ],

    # ------------------------------------------------------------------
    # Canonical links
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "about",
            "href": "https://zenodo.org/records/8154445",
            "type": "text/html",
            "title": "Zenodo dataset landing page (includes data agreement notes)",
        },
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5281/zenodo.8154445",
            "type": "text/html",
            "title": "Dataset DOI (Zenodo)",
        },
        {
            "rel": "related",
            "href": "https://doi.org/10.1126/sciadv.adh4097",
            "type": "text/html",
            "title": "Paper: Trees outside forests across Europe (Science Advances, 2023)",
        },
        {
            "rel": "related",
            "href": "https://assets.planet.com/docs/ToS_EducationAndResearch.pdf",
            "type": "application/pdf",
            "title": "Planet Education & Research Program terms (non-commercial license)",
        },
    ],

    # ------------------------------------------------------------------
    # Extensions (optional)
    # ------------------------------------------------------------------
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
        # "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Structured summaries (only what we can support from sources)
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["static"],
        "variables": ["canopy_cover", "canopy_height", "aboveground_biomass"],
        # Zenodo: biomass at 30 m; cover/height aggregated version also provided. :contentReference[oaicite:1]{index=1}
        "biomass_resolution_note": ["Biomass map provided at 30 m resolution (computed from cover & height)."],
        "usage_constraints": ["non-commercial scientific/education/research only"],
    },

    # ------------------------------------------------------------------
    # Assets (roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/LIU_BIOMASS_v{v}.zarr",
            title=f"Liu et al. Europe canopy structure & biomass v{v} (Zarr)",
            roles=["data"],
            description=(
                "Zarr packaging of European canopy cover, canopy height, and aboveground biomass layers. "
                "Includes aggregated canopy structure products and biomass at 30 m resolution. "
                "Usage restricted to non-commercial research/education/scientific purposes."
            ),
        )
    },
}

