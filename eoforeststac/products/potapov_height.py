import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

POTAPOV_HEIGHT_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "POTAPOV_HEIGHT",
    "title": "Global Canopy Height (Potapov et al.) (30 m)",
    "description": (
        "Global canopy height maps provided for multiple reference years (2000, 2005, 2010, 2015, 2020). "
        "The product integrates spaceborne LiDAR information with optical imagery to produce gridded "
        "canopy height estimates. See the dataset documentation for full processing details and "
        "citation guidance.\n\n"
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
    "start_datetime": datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/POTAPOV_HEIGHT/collection.json",
    "base_path": f"{BASE_S3_URL}/POTAPOV_HEIGHT",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "various",
    "providers": [
        {
            "name": "University of Maryland (GLAD), Department of Geographical Sciences",
            "roles": ["producer"],
            "url": "https://glad.umd.edu/",
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
        "canopy height",
        "vegetation height",
        "forest structure",
        "LiDAR",
        "multi-epoch",
        "global",
        "zarr",
        "stac",
    ],
    "themes": ["forest structure", "biomass", "carbon"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
        
        # Canonical citation / landing (replace/add as needed)
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.1016/j.rse.2020.112165",
            "type": "text/html",
            "title": "Primary citation (Remote Sensing of Environment, 2020)",
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
        "temporal_resolution": ["multi-epoch"],
        "reference_years": [2000, 2005, 2010, 2015, 2020],

        "variables": ["canopy_height"],
        "units": ["m"],

        # Spatial metadata (fill in what you actually store)
        # If you know your packaged grid spacing (e.g., 30 m, 1 km), set it here.
        "eo:gsd": [30.0],
        "proj:epsg": [4326],

        "data_format": ["zarr"],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Cloud-optimized Zarr store of global canopy height for a given reference year/epoch.",
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
            href=f"{cfg['base_path']}/POTAPOV_HEIGHT_v{v}.zarr",
            title=f"Global canopy height {v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing global canopy height for the given reference year/epoch. "
                "Part of a multi-epoch canopy height product (2005/2010/2015/2020)."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes (epochs)
    # ------------------------------------------------------------------
    "version_notes": {
        "2000": "Canopy height for reference year 2000.",
        "2005": "Canopy height for reference year 2005.",
        "2010": "Canopy height for reference year 2010.",
        "2015": "Canopy height for reference year 2015.",
        "2020": "Canopy height for reference year 2020.",
    },
}
