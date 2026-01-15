import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

GAMI_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "GAMI",
    "title": "Global Age Mapping Integration (GAMI) – Global forest age ensemble (100 m)",
    "description": (
        "Global gridded forest age product derived by integrating machine-learning models with "
        "remote sensing predictors and reference forest inventory information.\n\n"
        "Uncertainty representation: the Zarr store contains an ensemble dimension ('members') "
        "with 20 alternative forest-age estimates. This allows downstream users to propagate "
        "age uncertainty by summarizing across ensemble members (e.g., mean/median/IQR) rather than "
        "relying on a single uncertainty layer.\n\n"
        "Temporal semantics: GAMI provides forest-age estimates for discrete reference years. "
        "In this packaging, a 'time' dimension contains the available reference years "
        "(e.g., 2010 and 2020). Each item/version documents the exact reference years provided.\n\n"
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

    "temporal_notes": (
        "Temporal extent denotes the available reference years provided via the 'time' dimension "
        "in the packaged Zarr store (e.g., 2010 and 2020)."
    ),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/GAMI/collection.json",
    "base_path": f"{BASE_S3_URL}/GAMI",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
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
        "ensemble",
        "uncertainty propagation",
        "global",
        "zarr",
        "stac",
    ],
    "themes": ["forest structure", "carbon", "demography"],

    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------
    "links": [
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
    ],

    # ------------------------------------------------------------------
    # Extensions
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
        # honest for your structure: discrete reference years, not a continuous annual series
        "temporal_resolution": ["multi-epoch"],
        "reference_years": [2010, 2020],

        "variables": ["forest_age"],
        "units_by_variable": {"forest_age": "years"},

        # Ensemble semantics
        "ensemble_dimension": ["members"],
        "ensemble_members": [20],
        "ensemble_notes": [
            "The 'members' dimension contains 20 alternative age estimates; uncertainty can be summarized across members."
        ],

        # Spatial metadata
        "eo:gsd": [100.0],
        "proj:epsg": [4326],

        "product_family": ["GAMI"],
        "data_format": ["zarr"],
    },

    # ------------------------------------------------------------------
    # Item assets template
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store of global forest age estimates with an ensemble dimension "
                "('members'=20) and discrete reference years ('time')."
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        }
    },

    # ------------------------------------------------------------------
    # Asset template
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/GAMI_v{v}.zarr",
            title=f"GAMI v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing global forest age estimates. "
                "Includes an ensemble dimension ('members'=20) and discrete reference years in 'time' "
                "(e.g., 2010 and 2020) for uncertainty propagation via member statistics."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes
    # ------------------------------------------------------------------
    "version_notes": {
        "2.0": "Initial public release.",
        "2.1": "Incremental updates and/or bug fixes.",
        "3.0": "Major update (methods/data).",
        "3.1": "Minor update (methods/data).",
    },
}
