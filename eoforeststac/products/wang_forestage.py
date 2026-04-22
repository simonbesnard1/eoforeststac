import datetime
from eoforeststac.core.config import S3_HTTP_BASE
from eoforeststac.core.assets import create_zarr_asset

WANG_FORESTAGE_CFG = {
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    "id": "WANG_FORESTAGE",
    "title": "Global 30m Forest Age Map – Natural and Planted Forests (Wang et al.)",
    "description": (
        "Global 30-metre resolution maps of forest age for natural and planted forests, "
        "derived from Landsat time-series data using the CCDC (Continuous Change Detection "
        "and Classification) algorithm to identify spectral change points representing "
        "disturbance and regrowth events. Separate nearest-neighbour imputation models are "
        "developed for every 10×10 km tile covering land between ±51.6° latitude. "
        "The dataset provides two layers: age of natural forests and age of planted forests.\n\n"
        "Source: Wang et al. (2025), Mendeley Data doi:10.17632/yfm4sw8h25.2. "
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
    ),
    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -90.0, 180.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-180.0, -90.0],
                [-180.0, 90.0],
                [180.0, 90.0],
                [180.0, -90.0],
                [-180.0, -90.0],
            ]
        ],
    },
    "start_datetime": datetime.datetime(1985, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2024, 12, 31, tzinfo=datetime.timezone.utc),
    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{S3_HTTP_BASE}/WANG_FORESTAGE/collection.json",
    "base_path": f"{S3_HTTP_BASE}/WANG_FORESTAGE",
    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "CC-BY-4.0",
    "providers": [
        {
            "name": "China Agricultural University",
            "roles": ["producer"],
            "url": "https://www.cau.edu.cn",
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
        "forest age",
        "natural forest",
        "planted forest",
        "Landsat",
        "CCDC",
        "global",
        "30m",
        "zarr",
        "stac",
    ],
    "themes": ["forest age", "forest structure", "demography"],
    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5194/essd-2025-674",
            "type": "text/html",
            "title": (
                "Wang, Y., Wang, H., Liang, C., Li, X., Liu, Z., Zhang, X., Li, S., and Zhao, Y. "
                "2026. A global map of forest age for natural and planted forests at a fine spatial "
                "resolution of 30 meters. Earth System Science Data (preprint). "
                "https://doi.org/10.5194/essd-2025-674"
            ),
        },
        {
            "rel": "related",
            "href": "https://doi.org/10.17632/yfm4sw8h25.2",
            "type": "text/html",
            "title": "Dataset: Mendeley Data V2. https://doi.org/10.17632/yfm4sw8h25.2",
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
        "temporal_resolution": ["static (Landsat time series 1985–2024)"],
        "variables": ["natural_forest_age", "planted_forest_age"],
        "units_by_variable": {
            "natural_forest_age": "years",
            "planted_forest_age": "years",
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
                "Cloud-optimized Zarr store containing global 30m forest age for "
                "natural and planted forests."
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
            href=f"{cfg['base_path']}/WANG_FORESTAGE_v{v}.zarr",
            title=f"Wang et al. Forest Age v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store of global 30m forest age "
                "(natural and planted). Projection: EPSG:4326."
            ),
        ),
    },
}
