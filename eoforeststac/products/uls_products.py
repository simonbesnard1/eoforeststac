import datetime

from eoforeststac.core.config import S3_HTTP_BASE

ULS_RESOLUTIONS = {
    "10m": {
        "gsd": 10.0,
        "variables": [
            "basal_area_m2_ha",
            "basal_area_m2_sum",
            "crown_radius_m_iqr",
            "crown_radius_m_max",
            "crown_radius_m_mean",
            "crown_radius_m_median",
            "crown_radius_m_min",
            "dbh_m_iqr",
            "dbh_m_max",
            "dbh_m_mean",
            "dbh_m_median",
            "dbh_m_min",
            "dbh_measurement_se",
            "dbh_within_cell_sd",
            "height_m_iqr",
            "height_m_max",
            "height_m_mean",
            "height_m_median",
            "height_m_min",
            "height_measurement_se",
            "height_within_cell_sd",
            "n_segments",
            "n_segments_ha",
            "n_valid_dbh",
            "volume_m3_ha",
            "volume_m3_sum",
        ],
    },
    "20m": {
        "gsd": 20.0,
        "variables": [
            "basal_area_m2_ha",
            "basal_area_m2_sum",
            "crown_radius_m_iqr",
            "crown_radius_m_max",
            "crown_radius_m_mean",
            "crown_radius_m_median",
            "crown_radius_m_min",
            "dbh_m_iqr",
            "dbh_m_max",
            "dbh_m_mean",
            "dbh_m_median",
            "dbh_m_min",
            "dbh_measurement_se",
            "dbh_within_cell_sd",
            "height_m_iqr",
            "height_m_max",
            "height_m_mean",
            "height_m_median",
            "height_m_min",
            "height_measurement_se",
            "height_within_cell_sd",
            "n_segments",
            "n_segments_ha",
            "n_valid_dbh",
            "volume_m3_ha",
            "volume_m3_sum",
        ],
    },
    "100m": {
        "gsd": 100.0,
        "variables": [
            "basal_area_m2_ha",
            "basal_area_m2_sum",
            "crown_radius_m_iqr",
            "crown_radius_m_max",
            "crown_radius_m_mean",
            "crown_radius_m_median",
            "crown_radius_m_min",
            "dbh_m_iqr",
            "dbh_m_max",
            "dbh_m_mean",
            "dbh_m_median",
            "dbh_m_min",
            "dbh_measurement_se",
            "dbh_within_cell_sd",
            "height_m_iqr",
            "height_m_max",
            "height_m_mean",
            "height_m_median",
            "height_m_min",
            "height_measurement_se",
            "height_within_cell_sd",
            "n_segments",
            "n_segments_ha",
            "n_valid_dbh",
            "volume_m3_ha",
            "volume_m3_sum",
        ],
    },
}

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
    "test_region": {
        "label": "Test (Germany)",
        "description": (
            "Unmanned laser scanning products derived from UAV-based LiDAR surveys "
            "over the Test ICOS flux tower site in Thuringia, Germany. Processed "
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
        "proj_epsg": 25832,
        "start_datetime": datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2022, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ULS_TEST_REGION",
    },
}

ULS_PRODUCTS_CFG = {
    "id": "ULS_PRODUCTS",
    "title": "ULS Products – UAV laser scanning gridded products [Experimental]",
    "description": (
        "⚠️ This collection is under active development. Data coverage, variables, "
        "and metadata are subject to change without notice.\n\n"
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
        "experimental",
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
            "basal_area_m2_ha",
            "basal_area_m2_sum",
            "crown_radius_m_iqr",
            "crown_radius_m_max",
            "crown_radius_m_mean",
            "crown_radius_m_median",
            "crown_radius_m_min",
            "dbh_m_iqr",
            "dbh_m_max",
            "dbh_m_mean",
            "dbh_m_median",
            "dbh_m_min",
            "dbh_measurement_se",
            "dbh_within_cell_sd",
            "height_m_iqr",
            "height_m_max",
            "height_m_mean",
            "height_m_median",
            "height_m_min",
            "height_measurement_se",
            "height_within_cell_sd",
            "n_segments",
            "n_segments_ha",
            "n_valid_dbh",
            "volume_m3_ha",
            "volume_m3_sum",
        ],
        "units_by_variable": {
            "basal_area_m2_ha": "m2 ha-1",
            "basal_area_m2_sum": "m2",
            "crown_radius_m_iqr": "m",
            "crown_radius_m_max": "m",
            "crown_radius_m_mean": "m",
            "crown_radius_m_median": "m",
            "crown_radius_m_min": "m",
            "dbh_m_iqr": "m",
            "dbh_m_max": "m",
            "dbh_m_mean": "m",
            "dbh_m_median": "m",
            "dbh_m_min": "m",
            "dbh_measurement_se": "m",
            "dbh_within_cell_sd": "m",
            "height_m_iqr": "m",
            "height_m_max": "m",
            "height_m_mean": "m",
            "height_m_median": "m",
            "height_m_min": "m",
            "height_measurement_se": "m",
            "height_within_cell_sd": "m",
            "n_segments": "count",
            "n_segments_ha": "trees ha-1",
            "n_valid_dbh": "count",
            "volume_m3_ha": "m3 ha-1",
            "volume_m3_sum": "m3",
        },
        "spatial_resolutions": list(ULS_RESOLUTIONS.keys()),
        "proj:epsg": sorted({r["proj_epsg"] for r in REGIONS.values()}),
        "product_family": ["uls"],
        "data_format": ["zarr"],
    },
        "raster_bands": {
            "basal_area_m2_ha": {"data_type": "float32", "nodata": -9999.0},
            "basal_area_m2_sum": {"data_type": "float32", "nodata": -9999.0},
            "crown_radius_m_iqr": {"data_type": "float64", "nodata": -9999.0},
            "crown_radius_m_max": {"data_type": "float32", "nodata": -9999.0},
            "crown_radius_m_mean": {"data_type": "float32", "nodata": -9999.0},
            "crown_radius_m_median": {"data_type": "float32", "nodata": -9999.0},
            "crown_radius_m_min": {"data_type": "float32", "nodata": -9999.0},
            "dbh_m_iqr": {"data_type": "float64", "nodata": -9999.0},
            "dbh_m_max": {"data_type": "float32", "nodata": -9999.0},
            "dbh_m_mean": {"data_type": "float32", "nodata": -9999.0},
            "dbh_m_median": {"data_type": "float32", "nodata": -9999.0},
            "dbh_m_min": {"data_type": "float32", "nodata": -9999.0},
            "dbh_measurement_se": {"data_type": "float64", "nodata": -9999.0},
            "dbh_within_cell_sd": {"data_type": "float64", "nodata": -9999.0},
            "height_m_iqr": {"data_type": "float64", "nodata": -9999.0},
            "height_m_max": {"data_type": "float32", "nodata": -9999.0},
            "height_m_mean": {"data_type": "float32", "nodata": -9999.0},
            "height_m_median": {"data_type": "float32", "nodata": -9999.0},
            "height_m_min": {"data_type": "float32", "nodata": -9999.0},
            "height_measurement_se": {"data_type": "float64", "nodata": -9999.0},
            "height_within_cell_sd": {"data_type": "float64", "nodata": -9999.0},
            "n_segments": {"data_type": "int32", "nodata": -9999},
            "n_segments_ha": {"data_type": "float64", "nodata": -9999.0},
            "n_valid_dbh": {"data_type": "int32", "nodata": -9999},
            "volume_m3_ha": {"data_type": "float32", "nodata": -9999.0},
            "volume_m3_sum": {"data_type": "float32", "nodata": -9999.0},
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
