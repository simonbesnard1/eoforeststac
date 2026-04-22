import datetime
from eoforeststac.core.config import S3_HTTP_BASE
from eoforeststac.core.assets import create_zarr_asset

GEDI_L4D_CFG = {
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    "id": "GEDI_L4D",
    "title": "GEDI L4D Imputed Forest Structure (30 m)",
    "description": (
        "Spatially complete 30-meter resolution imputation of GEDI waveform-based forest structure "
        "metrics across the global tropics and temperate zone (±51.6° latitude). Relative height "
        "percentiles (RH10-RH98) are imputed "
        "from high-quality GEDI shots using nearest-neighbour models trained on Landsat time series, "
        "one model per 10×10 km tile. Companion RMSE layers quantify model uncertainty.\n\n"
        "Source: Seo et al. (2025), ORNL DAAC dataset 2455. "
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
    ),
    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -51.99, 180.0, 51.99],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-180.0, -51.99],
                [-180.0, 51.99],
                [180.0, 51.99],
                [180.0, -51.99],
                [-180.0, -51.99],
            ]
        ],
    },
    "start_datetime": datetime.datetime(2019, 4, 18, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2023, 3, 16, tzinfo=datetime.timezone.utc),
    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{S3_HTTP_BASE}/GEDI_L4D/collection.json",
    "base_path": f"{S3_HTTP_BASE}/GEDI_L4D",
    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "proprietary",
    "providers": [
        {
            "name": "NASA ORNL DAAC",
            "roles": ["producer"],
            "url": "https://daac.ornl.gov",
        },
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["processor", "host"],
            "url": "https://www.gfz.de",
        },
        {
            "name": "FORWARDS - The ForestWard Observatory to Secure Resilience of European Forests",
            "roles": ["funding"],
            "url": "https://cordis.europa.eu/project/id/101084481",
        },
    ],
    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    "keywords": [
        "GEDI",
        "LiDAR",
        "canopy height",
        "relative height",
        "forest structure",
        "imputation",
        "global",
        "zarr",
        "stac",
    ],
    "themes": ["forest structure", "canopy height"],
    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.3334/ORNLDAAC/2455",
            "type": "text/html",
            "title": (
                "Seo, E., S.P. Healey, Z. Yang, R.O. Dubayah, T. De Conto, and J. Armston. "
                "2025. GEDI L4D Imputed Waveforms, Version 2. ORNL DAAC, Oak Ridge, "
                "Tennessee, USA. https://doi.org/10.3334/ORNLDAAC/2455"
            ),
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
    # Summaries
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["static (2019-04-18 to 2023-03-16)"],
        "variables": [
            "rh10",
            "rh20",
            "rh30",
            "rh40",
            "rh50",
            "rh60",
            "rh70",
            "rh80",
            "rh90",
            "rh95",
            "rh98",
        ],
        "units_by_variable": {
            "rh10": "m",
            "rh20": "m",
            "rh30": "m",
            "rh40": "m",
            "rh50": "m",
            "rh60": "m",
            "rh70": "m",
            "rh80": "m",
            "rh90": "m",
            "rh95": "m",
            "rh98": "m",
        },
        "eo:gsd": [30.0],
        "proj:epsg": [4326],
        "data_format": ["zarr"],
    },
    # ------------------------------------------------------------------
    # Item assets
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store containing imputed GEDI L4D forest structure variables "
                "(RH percentiles, canopy cover, AGBD) at 30 m resolution."
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
            href=f"{cfg['base_path']}/GEDI_L4D_v{v}.zarr",
            title=f"GEDI L4D v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store of GEDI L4D imputed forest structure at 30 m. "
                "Variables: RH10-RH98, canopy cover, AGBD. Projection: EPSG:4326."
            ),
        ),
    },
}
