import datetime

from eoforeststac.core.config import S3_HTTP_BASE
from eoforeststac.products.als_products import ALS_RESOLUTIONS

ULS_RESOLUTIONS = ALS_RESOLUTIONS

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
    "bbox": [-10.0, 35.0, 32.0, 70.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [[-10.0, 35.0], [-10.0, 70.0], [32.0, 70.0], [32.0, 35.0], [-10.0, 35.0]]
        ],
    },
    "start_datetime": datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(9999, 12, 31, tzinfo=datetime.timezone.utc),
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
            "n_segments",
            "n_valid_dbh",
            "dbh_m_mean",
            "dbh_median",
            "dbh_m_min",
            "dbh_m_max",
            "h_m_mean",
            "h_m_median",
            "h_m_min",
            "h_m_max",
            "crown_radius_m_mean",
            "crown_radius_m_median",
            "crown_radius_m_min",
            "crown_radius_m_max",
            "volume_m3_sum",
            "volume_m3_ha",
            "basal_area_m2_sum",
            "basal_area_m2_ha",
            "dbh_sd",
            "height_sd",
            "dbh_rmse",
            "dbh_rrmse",
            "dbh_perc_rrmse",
            "dbh_bias",
            "ba_rmse",
            "ba_rrmse",
            "ba_perc_rrmse",
            "ba_bias",
        ],
        "units_by_variable": {
            "n_segments": "count",
            "n_valid_dbh": "count",
            "dbh_m_mean": "m",
            "dbh_median": "m",
            "dbh_m_min": "m",
            "dbh_m_max": "m",
            "h_m_mean": "m",
            "h_m_median": "m",
            "h_m_min": "m",
            "h_m_max": "m",
            "crown_radius_m_mean": "m",
            "crown_radius_m_median": "m",
            "crown_radius_m_min": "m",
            "crown_radius_m_max": "m",
            "volume_m3_sum": "m3",
            "volume_m3_ha": "m3 ha-1",
            "basal_area_m2_sum": "m2",
            "basal_area_m2_ha": "m2 ha-1",
            "dbh_sd": "m",
            "height_sd": "m",
            "dbh_rmse": "m",
            "dbh_rrmse": "percent",
            "dbh_perc_rrmse": "percent",
            "dbh_bias": "m",
            "ba_rmse": "m2",
            "ba_rrmse": "percent",
            "ba_perc_rrmse": "percent",
            "ba_bias": "m2",
        },
        "spatial_resolutions": list(ULS_RESOLUTIONS.keys()),
        "proj:epsg": [4326],
        "product_family": ["uls"],
        "data_format": ["zarr"],
    },
    "raster_bands": {
        "n_segments": {"data_type": "int32", "nodata": -9999},
        "n_valid_dbh": {"data_type": "int32", "nodata": -9999},
        "dbh_m_mean": {"data_type": "float32", "nodata": -9999.0},
        "dbh_median": {"data_type": "float32", "nodata": -9999.0},
        "dbh_m_min": {"data_type": "float32", "nodata": -9999.0},
        "dbh_m_max": {"data_type": "float32", "nodata": -9999.0},
        "h_m_mean": {"data_type": "float32", "nodata": -9999.0},
        "h_m_median": {"data_type": "float32", "nodata": -9999.0},
        "h_m_min": {"data_type": "float32", "nodata": -9999.0},
        "h_m_max": {"data_type": "float32", "nodata": -9999.0},
        "crown_radius_m_mean": {"data_type": "float32", "nodata": -9999.0},
        "crown_radius_m_median": {"data_type": "float32", "nodata": -9999.0},
        "crown_radius_m_min": {"data_type": "float32", "nodata": -9999.0},
        "crown_radius_m_max": {"data_type": "float32", "nodata": -9999.0},
        "volume_m3_sum": {"data_type": "float32", "nodata": -9999.0},
        "volume_m3_ha": {"data_type": "float32", "nodata": -9999.0},
        "basal_area_m2_sum": {"data_type": "float32", "nodata": -9999.0},
        "basal_area_m2_ha": {"data_type": "float32", "nodata": -9999.0},
        "dbh_sd": {"data_type": "float32", "nodata": -9999.0},
        "height_sd": {"data_type": "float32", "nodata": -9999.0},
        "dbh_rmse": {"data_type": "float32", "nodata": -9999.0},
        "dbh_rrmse": {"data_type": "float32", "nodata": -9999.0},
        "dbh_perc_rrmse": {"data_type": "float32", "nodata": -9999.0},
        "dbh_bias": {"data_type": "float32", "nodata": -9999.0},
        "ba_rmse": {"data_type": "float32", "nodata": -9999.0},
        "ba_rrmse": {"data_type": "float32", "nodata": -9999.0},
        "ba_perc_rrmse": {"data_type": "float32", "nodata": -9999.0},
        "ba_bias": {"data_type": "float32", "nodata": -9999.0},
    },
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store with resolution groups (10m, 20m, 100m) "
                "containing gridded ULS products."
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
    },
    "regions": REGIONS,
    "resolutions": ULS_RESOLUTIONS,
}
