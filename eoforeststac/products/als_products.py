import datetime
from eoforeststac.core.config import S3_HTTP_BASE

ALS_RESOLUTIONS = {
    "1m": {"gsd": 1.0, "variables": ["chm", "dtm", "dsm"]},
    "10m": {
        "gsd": 10.0,
        "variables": [
            "gap",
            "lai",
            "biomass",
            "h50",
            "h75",
            "h95",
            "hmax",
            "hmean",
            "cc",
            "density",
            "fhd",
            "vci",
            "crr",
            "pv_0_2",
            "pv_2_5",
            "pv_5_10",
            "pv_10_20",
            "pv_20_40",
            "pv_above40",
        ],
    },
    "100m": {
        "gsd": 100.0,
        "variables": [
            "gap",
            "lai",
            "biomass",
            "h50",
            "h75",
            "h95",
            "hmax",
            "hmean",
            "cc",
            "density",
            "fhd",
            "vci",
            "crr",
            "pv_0_2",
            "pv_2_5",
            "pv_5_10",
            "pv_10_20",
            "pv_20_40",
            "pv_above40",
        ],
    },
}

# ------------------------------------------------------------------
# Per-region definitions
# ------------------------------------------------------------------

REGIONS = {
    "spain_pnoa": {
        "label": "Spain PNOA",
        "description": (
            "Airborne laser scanning point cloud products derived from the Spanish "
            "Plan Nacional de Ortofotografía Aérea (PNOA) LiDAR surveys, processed "
            "with alsdb and stored as analysis-ready Zarr."
        ),
        "bbox": [-9.5, 35.9, 4.4, 43.8],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-9.5, 35.9],
                    [-9.5, 43.8],
                    [4.4, 43.8],
                    [4.4, 35.9],
                    [-9.5, 35.9],
                ]
            ],
        },
        "proj_epsg": 25830,
        "start_datetime": datetime.datetime(2015, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ALS_SPAIN_PNOA",
    },
    # "brazil": {
    #     "label": "Brazil",
    #     "description": "...",
    #     "bbox": [...],
    #     "geometry": {...},
    #     "proj_epsg": 31983,
    #     "start_datetime": datetime.datetime(2018, 1, 1, tzinfo=datetime.timezone.utc),
    #     "end_datetime": datetime.datetime(2022, 12, 31, tzinfo=datetime.timezone.utc),
    #     "zarr_name": "ALS_BRAZIL",
    # },
}

# ------------------------------------------------------------------
# Collection-level config
# ------------------------------------------------------------------
ALS_PRODUCTS_CFG = {
    "id": "ALS_PRODUCTS",
    "title": "ALS Products – Airborne laser scanning gridded products",
    "description": (
        "Gridded products derived from airborne laser scanning (ALS) point clouds "
        "using the alsdb processing pipeline. Products include canopy height model (CHM), "
        "digital terrain model (DTM), digital surface model (DSM), gap fraction, effective LAI, "
        "above-ground biomass, and a suite of structural LiDAR metrics (height percentiles, "
        "canopy cover, point density, foliage height diversity, vegetation complexity index).\n\n"
        "Each region/campaign is a separate STAC item with its own spatial extent, CRS, "
        "and Zarr store."
    ),
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
    "start_datetime": datetime.datetime(2015, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),
    "collection_href": f"{S3_HTTP_BASE}/ALS_PRODUCTS/collection.json",
    "base_path": f"{S3_HTTP_BASE}/ALS_PRODUCTS",
    "license": "EUPL-1.2",
    "providers": [
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["producer", "processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],
    "keywords": [
        "airborne laser scanning",
        "ALS",
        "LiDAR",
        "canopy height",
        "CHM",
        "DTM",
        "DSM",
        "biomass",
        "gap fraction",
        "LAI",
        "forest structure",
        "point cloud",
        "zarr",
        "stac",
    ],
    "themes": ["lidar", "forest structure", "canopy height"],
    "links": [
        {
            "rel": "about",
            "href": "https://github.com/simonbesnard1/alsdb",
            "type": "text/html",
            "title": "alsdb processing pipeline",
        },
        {
            "rel": "cite-as",
            "href": "https://github.com/simonbesnard1/alsdb",
            "type": "text/html",
            "title": "alsdb – ALS gridded products pipeline (cite repository until DOI is available)",
        },
    ],
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
        "https://stac-extensions.github.io/file/v2.1.0/schema.json",
        "https://stac-extensions.github.io/raster/v1.1.0/schema.json",
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",
    ],
    "summaries": {
        "temporal_resolution": ["multi-year"],
        "variables": [
            "chm",
            "dtm",
            "dsm",
            "gap",
            "lai",
            "biomass",
            "h50",
            "h75",
            "h95",
            "hmax",
            "hmean",
            "cc",
            "density",
            "fhd",
            "vci",
            "crr",
            "pv_0_2",
            "pv_2_5",
            "pv_5_10",
            "pv_10_20",
            "pv_20_40",
            "pv_above40",
        ],
        "units_by_variable": {
            "chm": "m",
            "dtm": "m",
            "dsm": "m",
            "gap": "fraction",
            "lai": "m2 m-2",
            "biomass": "Mg ha-1",
            "h50": "m",
            "h75": "m",
            "h95": "m",
            "hmax": "m",
            "hmean": "m",
            "cc": "fraction",
            "density": "pts m-2",
            "fhd": "nats",
            "vci": "dimensionless",
            "crr": "dimensionless",
        },
        "spatial_resolutions": list(ALS_RESOLUTIONS.keys()),
        "proj:epsg": [25830],
        "product_family": ["alsdb"],
        "data_format": ["zarr"],
    },
    "raster_bands": {
        "chm": {"data_type": "float32", "nodata": -9999.0},
        "dtm": {"data_type": "float32", "nodata": -9999.0},
        "dsm": {"data_type": "float32", "nodata": -9999.0},
        "gap": {"data_type": "float32", "nodata": -9999.0},
        "lai": {"data_type": "float32", "nodata": -9999.0},
        "biomass": {"data_type": "float32", "nodata": -9999.0},
        "h50": {"data_type": "float32", "nodata": -9999.0},
        "h75": {"data_type": "float32", "nodata": -9999.0},
        "h95": {"data_type": "float32", "nodata": -9999.0},
        "hmax": {"data_type": "float32", "nodata": -9999.0},
        "hmean": {"data_type": "float32", "nodata": -9999.0},
        "cc": {"data_type": "float32", "nodata": -9999.0},
        "density": {"data_type": "float32", "nodata": -9999.0},
        "fhd": {"data_type": "float32", "nodata": -9999.0},
        "vci": {"data_type": "float32", "nodata": -9999.0},
        "crr": {"data_type": "float32", "nodata": -9999.0},
        "pv_0_2": {"data_type": "float32", "nodata": -9999.0},
        "pv_2_5": {"data_type": "float32", "nodata": -9999.0},
        "pv_5_10": {"data_type": "float32", "nodata": -9999.0},
        "pv_10_20": {"data_type": "float32", "nodata": -9999.0},
        "pv_20_40": {"data_type": "float32", "nodata": -9999.0},
        "pv_above40": {"data_type": "float32", "nodata": -9999.0},
    },
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store with resolution groups (1m, 10m) "
                "containing gridded ALS products."
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
    },
    "regions": REGIONS,
    "resolutions": ALS_RESOLUTIONS,
}
