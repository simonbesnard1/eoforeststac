import datetime

from eoforeststac.core.config import S3_HTTP_BASE
from eoforeststac.products.als_products import ALS_RESOLUTIONS

ULS_RESOLUTIONS = ALS_RESOLUTIONS

REGIONS = {
    "hainich": {
        "label": "Hainich (Germany)",
        "description": (
            "Unmanned laser scanning products derived from UAV-based LiDAR surveys "
            "over the Hainich ICOS flux tower site in Thuringia, Germany. Processed "
            "with the ULS R pipeline and stored as analysis-ready Zarr."
        ),
        "bbox": [10.408, 51.034, 10.498, 51.124],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [10.408, 51.034],
                    [10.408, 51.124],
                    [10.498, 51.124],
                    [10.498, 51.034],
                    [10.408, 51.034],
                ]
            ],
        },
        "proj_epsg": 32632,
        "start_datetime": datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2022, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ULS_HAINICH",
    },
}

ULS_PRODUCTS_CFG = {
    "id": "ULS_PRODUCTS",
    "title": "ULS Products – UAV laser scanning gridded products",
    "description": (
        "Gridded products derived from unmanned laser scanning (ULS) point clouds "
        "collected by UAV-based LiDAR sensors. Products include canopy height model (CHM), "
        "digital terrain model (DTM), digital surface model (DSM), gap fraction, effective LAI, "
        "above-ground biomass, and a suite of structural LiDAR metrics (height percentiles, "
        "canopy cover, point density, foliage height diversity, vegetation complexity index).\n\n"
        "Each site/campaign is a separate STAC item with its own spatial extent, CRS, "
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
    "start_datetime": datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2022, 12, 31, tzinfo=datetime.timezone.utc),
    "collection_href": f"{S3_HTTP_BASE}/ULS_PRODUCTS/collection.json",
    "base_path": f"{S3_HTTP_BASE}/ULS_PRODUCTS",
    "license": "EUPL-1.2",
    "providers": [
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["producer", "processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],
    "keywords": [
        "unmanned laser scanning",
        "ULS",
        "UAV",
        "drone",
        "LiDAR",
        "canopy height",
        "CHM",
        "DTM",
        "DSM",
        "biomass",
        "gap fraction",
        "LAI",
        "forest structure",
        "flux tower",
        "zarr",
        "stac",
    ],
    "themes": ["lidar", "forest structure", "canopy height"],
    "links": [
        {
            "rel": "cite-as",
            "href": "https://meta.icos-cp.eu/objects/M1ET1IeG31p-6n4BFjDb3ZO7",
            "type": "text/html",
            "title": "ICOS Hainich flux tower metadata",
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
        "temporal_resolution": ["campaign"],
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
        "spatial_resolutions": list(ULS_RESOLUTIONS.keys()),
        "proj:epsg": [32632],
        "product_family": ["uls"],
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
                "Cloud-optimized Zarr store with resolution groups (1m, 10m, 100m) "
                "containing gridded ULS products."
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
    },
    "regions": REGIONS,
    "resolutions": ULS_RESOLUTIONS,
}
