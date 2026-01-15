import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

ROBINSON_CR_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "ROBINSON_CR",
    "title": "Robinson et al. – Chapman-Richards growth-curve parameters for secondary-forest aboveground carbon dynamics (1 km)",
    "description": (
        "Global, pixel-level Chapman–Richards (CR) growth-curve parameters and derived outputs "
        "describing aboveground carbon (AGC) accumulation in young secondary forests. "
        "The dataset provides CR parameters (A, b, k) and their standard errors, plus derived layers "
        "including maximum annual accumulation rate, the age at which that maximum rate occurs, and "
        "a relative benefit metric used in the associated publication.\n\n"
        "Parameters can be combined to reconstruct growth trajectories using the Chapman-Richards form "
        "described in the record README.\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
    ),

    # ------------------------------------------------------------------
    # Spatial / nominal temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -90.0, 108.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-180.0, -90.0],
            [-180.0,  90.0],
            [ 108.0,  90.0],
            [ 108.0, -90.0],
            [-180.0, -90.0],
        ]],
    },
    # Static model output; you use publication year as nominal envelope
    "start_datetime": datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2025, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/ROBINSON_CR/collection.json",
    "base_path": f"{BASE_S3_URL}/ROBINSON_CR",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "CC-BY-4.0",
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
        "natural regeneration",
        "carbon removal",
        "aboveground carbon",
        "Chapman-Richards",
        "growth curves",
        "nature-based solutions",
        "zarr",
        "stac",
    ],
    "themes": ["carbon", "forest dynamics", "model parameters"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
        
        # Canonical links (paper + data + explorer)
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
            "title": "Paper (Nature Climate Change, 2025)",
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

        # spatial metadata grounded in README
        "proj:epsg": [4326],
        "eo:gsd": [1000.0],

        "variables": [
            "cr_a", "cr_b", "cr_k",
            "cr_a_error", "cr_b_error", "cr_k_error",
            "max_rate", "age_at_max_rate",
            "max_removal_potential_benefit_25",
        ],
        # keep a simple global units list AND keep your detailed mapping
        "units_by_variable": {
            "cr_a": "Mg C ha-1",
            "cr_a_error": "Mg C ha-1",
            "cr_b": "adimensional",
            "cr_b_error": "adimensional",
            "cr_k": "adimensional",
            "cr_k_error": "adimensional",
            "max_rate": "Mg C ha-1 yr-1",
            "age_at_max_rate": "years",
            "max_removal_potential_benefit_25": "%",
        },

        "data_format": ["zarr"],

        "notes": [
            "Parameter names and units follow the Zenodo README; see record for full definitions and the growth equation."
        ],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store of Chapman-Richards parameters (A, b, k), their standard errors, "
                "and derived layers (max_rate, age_at_max_rate, benefit_25)."
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
            href=f"{cfg['base_path']}/ROBINSON_CR_v{v}.zarr",
            title=f"Robinson et al. CR parameters & derived layers v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store of Chapman-Richards parameters (A, b, k), their standard errors, "
                "and derived layers (max_rate, age_at_max_rate, benefit_25) from Robinson et al. (2025). "
                "Original distribution is GeoTIFF (EPSG:4326, ~1 km)."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes (optional)
    # ------------------------------------------------------------------
    "version_notes": {
        "1": "Zenodo record version 1 (published 2025-03-26).",
    },
}
