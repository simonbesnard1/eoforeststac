import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

LIU_BIOMASS_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "LIU_BIOMASS",
    "title": "Liu et al. – Europe canopy cover, canopy height, and aboveground biomass (30 m)",
    "description": (
        "European maps of canopy cover, canopy height, and aboveground biomass derived from "
        "high-resolution PlanetScope imagery and airborne LiDAR canopy height models using deep learning. "
        "The Zenodo release includes aggregated canopy cover/height products and a biomass map at 30 m "
        "resolution computed from canopy cover and height using allometric equations.\n\n"
        "IMPORTANT – Usage restrictions: This dataset is provided for non-commercial scientific, "
        "education, and research purposes only, reflecting restrictions associated with PlanetScope "
        "imagery access under research licensing. Users must not use the dataset for commercial purposes "
        "and should follow the dataset’s stated data agreement and citation requirements.\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
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
        ]],
    },
    "start_datetime": datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2019, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/LIU_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/LIU_BIOMASS",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    # STAC 'license' expects a short token. "proprietary" is appropriate here.
    "license": "proprietary",
    "license_notes": (
        "Non-commercial scientific/education/research use only. "
        "Derived from PlanetScope imagery accessed under a research license; "
        "see Zenodo record and Planet Education & Research terms for details."
    ),
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
        "zarr",
        "stac",
    ],
    "themes": ["biomass", "forest structure", "carbon"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
        
        # Canonical resources + restrictions
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
            "rel": "license",
            "href": "https://assets.planet.com/docs/ToS_EducationAndResearch.pdf",
            "type": "application/pdf",
            "title": "Planet Education & Research Program terms (non-commercial license)",
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
        "variables": ["canopy_cover", "canopy_height", "aboveground_biomass"],
        "units": ["percent", "m", "Mg ha-1"],  # adjust if your stored units differ

        # Spatial metadata — only set if you’re confident
        "eo:gsd": [30.0],       # biomass map explicitly at 30 m; cover/height may differ
        "proj:epsg": [4326],  # uncomment if your Zarr is stored in EPSG:4326

        "product_family": ["Liu et al. (Trees outside forests, Europe)"],
        "data_format": ["zarr"],

        # Critical usage constraints surfaced for clients
        "usage_constraints": ["non-commercial scientific/education/research only"],
        "license_notes": [
            "Derived from PlanetScope imagery under research licensing; non-commercial use only."
        ],
        "biomass_resolution_note": [
            "Biomass map provided at 30 m resolution (computed from canopy cover & height)."
        ],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store of European canopy cover, canopy height, and aboveground biomass. "
                "Usage restricted to non-commercial research/education/scientific purposes."
            ),
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
            href=f"{cfg['base_path']}/LIU_BIOMASS_v{v}.zarr",
            title=f"Liu et al. canopy structure & biomass v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store of European canopy cover, canopy height, and aboveground biomass layers. "
                "Includes aggregated canopy structure products and biomass at 30 m resolution. "
                "Usage restricted to non-commercial research/education/scientific purposes."
            ),
        ),
    },
}
