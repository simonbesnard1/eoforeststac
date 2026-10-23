import datetime
from eoforeststac.core.config import S3_HTTP_BASE

# ------------------------------------------------------------------
# Per-region definitions
# ------------------------------------------------------------------

REGIONS = {
    "finland": {
        "label": "Finland",
        "description": (
            "Forest biomass maps at 10 m resolution for Finland (2019, 2020 and 2021), "
            "derived from National Forest Inventory plots and airborne laser "
            "scanning. Each year covers the area scanned in that year's ALS "
            "campaign; all years share one EPSG:3067 grid."
        ),
        "bbox": [18.638, 59.727, 33.108, 70.095],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [18.638, 59.727],
                    [18.638, 70.095],
                    [33.108, 70.095],
                    [33.108, 59.727],
                    [18.638, 59.727],
                ]
            ],
        },
        "proj_epsg": 3067,
        "start_datetime": datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2021, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ALS_BIOMASS_FINLAND",
    },
    "ireland": {
        "label": "Ireland",
        "description": (
            "Forest biomass maps at 10 m resolution for Ireland (2006, 2011, 2015, 2016, 2017 and 2020), "
            "derived from National Forest Inventory plots and airborne laser "
            "scanning. Each year covers the area scanned in that year's ALS "
            "campaign; all years share one EPSG:2157 grid."
        ),
        "bbox": [-10.583, 51.463, -5.857, 55.333],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-10.583, 51.463],
                    [-10.583, 55.333],
                    [-5.857, 55.333],
                    [-5.857, 51.463],
                    [-10.583, 51.463],
                ]
            ],
        },
        "proj_epsg": 2157,
        "start_datetime": datetime.datetime(2006, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ALS_BIOMASS_IRELAND",
    },
    "italy": {
        "label": "Italy",
        "description": (
            "Forest biomass maps at 10 m resolution for Italy (2006 and 2014), "
            "derived from National Forest Inventory plots and airborne laser "
            "scanning. Each year covers the area scanned in that year's ALS "
            "campaign; all years share one EPSG:25832 grid."
        ),
        "bbox": [10.438, 45.638, 12.02, 46.548],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [10.438, 45.638],
                    [10.438, 46.548],
                    [12.02, 46.548],
                    [12.02, 45.638],
                    [10.438, 45.638],
                ]
            ],
        },
        "proj_epsg": 25832,
        "start_datetime": datetime.datetime(2006, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2014, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ALS_BIOMASS_ITALY",
    },
    "netherlands": {
        "label": "Netherlands",
        "description": (
            "Forest biomass maps at 10 m resolution for Netherlands (2016, 2017, 2018 and 2019), "
            "derived from National Forest Inventory plots and airborne laser "
            "scanning. Each year covers the area scanned in that year's ALS "
            "campaign; all years share one EPSG:28992 grid."
        ),
        "bbox": [3.958, 50.733, 7.268, 53.442],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [3.958, 50.733],
                    [3.958, 53.442],
                    [7.268, 53.442],
                    [7.268, 50.733],
                    [3.958, 50.733],
                ]
            ],
        },
        "proj_epsg": 28992,
        "start_datetime": datetime.datetime(2016, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2019, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ALS_BIOMASS_NETHERLANDS",
    },
    "spain": {
        "label": "Spain",
        "description": (
            "Forest biomass maps at 10 m resolution for Spain (2016, 2018, 2019, 2020 and 2021), "
            "derived from National Forest Inventory plots and airborne laser "
            "scanning. Each year covers the area scanned in that year's ALS "
            "campaign; all years share one EPSG:25830 grid."
        ),
        "bbox": [-6.324, 38.193, 3.395, 43.263],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-6.324, 38.193],
                    [-6.324, 43.263],
                    [3.395, 43.263],
                    [3.395, 38.193],
                    [-6.324, 38.193],
                ]
            ],
        },
        "proj_epsg": 25830,
        "start_datetime": datetime.datetime(2016, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2021, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ALS_BIOMASS_SPAIN",
    },
    "sweden": {
        "label": "Sweden",
        "description": (
            "Forest biomass maps at 10 m resolution for Sweden (2018, 2019, 2020, 2021, 2022, 2023 and 2024), "
            "derived from National Forest Inventory plots and airborne laser "
            "scanning. Each year covers the area scanned in that year's ALS "
            "campaign; all years share one EPSG:3006 grid."
        ),
        "bbox": [9.313, 55.158, 25.263, 68.58],
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [9.313, 55.158],
                    [9.313, 68.58],
                    [25.263, 68.58],
                    [25.263, 55.158],
                    [9.313, 55.158],
                ]
            ],
        },
        "proj_epsg": 3006,
        "start_datetime": datetime.datetime(2018, 1, 1, tzinfo=datetime.timezone.utc),
        "end_datetime": datetime.datetime(2024, 12, 31, tzinfo=datetime.timezone.utc),
        "zarr_name": "ALS_BIOMASS_SWEDEN",
    },
}

# ------------------------------------------------------------------
# Collection-level config
# ------------------------------------------------------------------
ALS_BIOMASS_PRODUCTS_CFG = {
    "id": "ALS_BIOMASS_PRODUCTS",
    "short_title": "ALS Biomass Products",
    "title": "ALS Biomass Products – harmonized 10 m forest aboveground biomass from ALS (V1.0)",
    "description": (
        "Version 1.0. Internal to GFZ: not for public distribution.\n\n"
        "Harmonized forest aboveground biomass maps at 10 m resolution derived from "
        "airborne laser scanning and National Forest Inventory plots, in selected "
        "regions of Finland, Spain and the Netherlands.\n\n"
        "Each country is a child collection in its national CRS. Its Zarr store holds "
        "biomass(time, y, x) with one time step per ALS campaign year; every year "
        "covers the area scanned that year and is NaN elsewhere.\n\n"
        "Citation: Song, Q., Enguehard, L., Kuschnerus, M., & Herold, M. (2026). "
        "Harmonized Airborne Laser Scanning-derived forest above ground biomass maps "
        "in selected regions of Finland, Spain, and the Netherlands (Version V 1.0) "
        "[Dataset]. Zenodo. https://doi.org/10.5281/zenodo.23591088"
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
    "collection_href": f"{S3_HTTP_BASE}/ALS_BIOMASS_PRODUCTS/collection.json",
    "base_path": f"{S3_HTTP_BASE}/ALS_BIOMASS_PRODUCTS",
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
        "biomass",
        "national forest inventory",
        "Europe",
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
            "href": "https://doi.org/10.5281/zenodo.23591088",
            "type": "text/html",
            "title": "Song, Q., Enguehard, L., Kuschnerus, M., & Herold, M. (2026). Harmonized "
            "Airborne Laser Scanning-derived forest above ground biomass maps in selected "
            "regions of Finland, Spain, and the Netherlands (Version V 1.0). Zenodo.",
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
        "variables": ["biomass"],
        "units_by_variable": {"biomass": "Mg ha-1"},
        "spatial_resolutions": ["10m"],
        "proj:epsg": sorted({r["proj_epsg"] for r in REGIONS.values()}),
        "product_family": ["alsdb"],
        "data_format": ["zarr"],
    },
    "raster_bands": {
        "biomass": {"data_type": "float32", "nodata": "nan"},
    },
    # Region statistics in the explorer (eoforeststac.analytics); keys are
    # the variable names in the Zarr store
    "analytics": {
        "biomass": {
            "kind": "density",
            "quantity": "Forest biomass",
            "total_units": "Mg",
        },
    },
    # Map overviews (eoforeststac.pyramids): reducer per variable, "mean" for
    # continuous fields, "max" for event years and presence, "first" for classes
    "pyramid": {
        "reducers": {
            "biomass": "mean",
        }
    },
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store with biomass(time, y, x) at 10 m "
                "resolution, one time step per ALS campaign year."
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
    },
    "regions": REGIONS,
}
