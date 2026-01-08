# eoforeststac/products/robinson_cr.py

import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset


ROBINSON_CR_CFG = {
    "id": "ROBINSON_CR",
    "title": "Global Chapman–Richards growth-curve parameters for secondary-forest aboveground carbon dynamics (Robinson et al., 2025)",
    "description": (
        "Global, pixel-level Chapman–Richards (CR) growth-curve parameters and derived outputs "
        "describing aboveground carbon (AGC) accumulation in young secondary forests. "
        "The dataset provides CR parameters (A, b, k) and their standard errors, plus derived layers "
        "including maximum annual accumulation rate, the age at which that maximum rate occurs, and "
        "a relative benefit metric used in the associated publication.\n\n"
        "Parameters can be combined to reconstruct growth trajectories using the Chapman–Richards form "
        "described in the record README."
    ),

    # ------------------------------------------------------------------
    # Spatial / nominal temporal extent
    # ------------------------------------------------------------------
    # Bounding extent is explicitly documented in the Zenodo README: lon [-180, 108], lat [-90, 90]. :contentReference[oaicite:3]{index=3}
    "bbox": [-180.0, -90.0, 108.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-180.0, -90.0],
            [-180.0,  90.0],
            [ 108.0,  90.0],
            [ 108.0, -90.0],
            [-180.0, -90.0],
        ]]
    },

    # Static model output; use publication year as a nominal temporal envelope
    "start_datetime": datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2025, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC paths
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/ROBINSON_CR/collection.json",
    "base_path": f"{BASE_S3_URL}/ROBINSON_CR",

    # ------------------------------------------------------------------
    # Provenance / licensing
    # ------------------------------------------------------------------
    "license": "CC-BY-4.0",  # Zenodo record license is Creative Commons Attribution 4.0 :contentReference[oaicite:4]{index=4}

    "providers": [
        {
            "name": "CIFOR-ICRAF (World Agroforestry Centre)",
            "roles": ["producer"],
            "url": "https://www.cifor-icraf.org",
        },
        {
            "name": "The Nature Conservancy (TNC)",
            "roles": ["producer"],
            "url": "https://www.nature.org",
        },
        {
            "name": "Zenodo",
            "roles": ["host"],
            "url": "https://zenodo.org/records/15090826",
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
        "secondary forests",
        "forest regrowth",
        "carbon removal",
        "aboveground carbon",
        "Chapman-Richards",
        "growth curves",
        "nature-based solutions",
        "natural regeneration",
    ],

    # ------------------------------------------------------------------
    # Canonical links (paper + data + explorer)
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5281/zenodo.15090826",
            "type": "text/html",
            "title": "Dataset DOI (Zenodo): Data outputs for Robinson et al. (2025)",
        },
        {
            "rel": "related",
            "href": "https://doi.org/10.1038/s41558-025-02355-5",
            "type": "text/html",
            "title": "Paper: Protect young secondary forests for optimum carbon removal (Nature Climate Change, 2025)",
        },
        {
            "rel": "documentation",
            "href": "https://zenodo.org/records/15090826",
            "type": "text/html",
            "title": "Record documentation (Zenodo landing page + README)",
        },
        {
            "rel": "related",
            "href": "https://ee-groa-carbon-accumulation.projects.earthengine.app/view/natural-forest-regeneration-carbon-accumulation-explorer",
            "type": "text/html",
            "title": "Web application: Natural forest regeneration carbon accumulation explorer",
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
    # Structured summaries (grounded in README)
    # ------------------------------------------------------------------
    "summaries": {
        # README: pixel size 0.008333... degrees (~1 km), CRS EPSG:4326 :contentReference[oaicite:5]{index=5}
        "proj:epsg": [4326],
        "eo:gsd": [1000],  # ~1 km at equator (derived from 0.008333°) :contentReference[oaicite:6]{index=6}
        "temporal_resolution": ["static"],
        "variables": [
            "cr_a", "cr_b", "cr_k",
            "cr_a_error", "cr_b_error", "cr_k_error",
            "max_rate", "age_at_max_rate",
            "max_removal_potential_benefit_25",
        ],
        "units_by_variable": {
            "cr_a": "Mg C ha-1",
            "max_rate": "Mg C ha-1 yr-1",
            "age_at_max_rate": "years",
            "max_removal_potential_benefit_25": "%",
        },
        "model": ["Chapman–Richards"],
        "notes": [
            "Parameter names and units follow the Zenodo README; see record for full definitions and usage equation."
        ],
    },

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/ROBINSON_CR_v{v}.zarr",
            title=f"Robinson et al. CR parameters & derived layers v{v} (Zarr)",
            roles=["data"],
            description=(
                "Zarr packaging of Chapman–Richards parameters (A, b, k), their standard errors, "
                "and derived layers (max_rate, age_at_max_rate, benefit_25) from Robinson et al. (2025). "
                "Original distribution is GeoTIFF (EPSG:4326, ~1 km)."
            ),
        )
    },

    # Optional: interpret your version string(s)
    "version_notes": {
        "1": "Zenodo record version 1 (published 2025-03-26).",
    },
}

