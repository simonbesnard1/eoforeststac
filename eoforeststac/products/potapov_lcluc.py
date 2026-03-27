import datetime
from eoforeststac.core.config import S3_HTTP_BASE
from eoforeststac.core.assets import create_zarr_asset

POTAPOV_LCLUC_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "Potapov_LCLUC",
    "title": "Potapov Land Cover and Land Use Change 2000-2020",
    "description": (
        "The GLAD Global Land Cover and Land Use Change dataset quantifies \
        changes in forest extent and height, cropland, built-up lands, \
        surface water, and perennial snow and ice extent from the year \
        2000 to 2020 at 30-m spatial resolution. The global dataset derived \
        from the GLAD Landsat Analysis Ready Data. Each thematic product was \
        independently derived using state-of-the-art, locally and regionally \
        calibrated machine learning tools. Each thematic layer was validated \
        independently using a statistical sampling.\n\n"
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
    "start_datetime": datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),
    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{S3_HTTP_BASE}/Potapov_LCLUC/collection.json",
    "base_path": f"{S3_HTTP_BASE}/Potapov_LCLUC",
    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "Open-access",
    "providers": [
        {
            "name": "University of Maryland",
            "roles": ["producer"],
            "url": "https://glad.umd.edu/dataset/GLCLUC2020",
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
        "forest",
        "global",
        "remote sensing",
        "land cover",
        "change",
    ],
    # Optional but often useful for “atlas” grouping (your own convention)
    "themes": ["landcover", "landuse", "forest"],
    # ------------------------------------------------------------------
    # Links (what makes STAC Browser feel curated)
    # ------------------------------------------------------------------
    "links": [
        # Official documentation
        {
            "rel": "about",
            "href": "https://glad.earthengine.app/view/glcluc-2000-2020",
            "type": "text/html",
            "title": "GLAD LCLUC Dataset Online Availability",
        },
        # If you have a canonical terms/licensing page, link it explicitly
        {
            "rel": "license",
            "href": "http://creativecommons.org/licenses/by/4.0/",
            "type": "text/html",
            "title": "Creative Commons Attribution 4.0 International License",
        },
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.3389/frsen.2022.856903",
            "type": "text/html",
            "title": "Dataset DOI",
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
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",  # bands, nodata, etc.
    ],
    # ------------------------------------------------------------------
    # Summaries (client-friendly structured metadata)
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": [
            "Land cover/use every 4 years and change over 20 years"
        ],
        "variables": [
            "LCLU2000",
            "LCLU2005",
            "LCLU2010",
            "LCLU2015",
            "LCLU2020",
            "LCLUC2000-2020change",
        ],
        "units_by_variable": {
            "LCLU2000": "Categorical",
            "LCLU2005": "Categorical",
            "LCLU2010": "Categorical",
            "LCLU2015": "Categorical",
            "LCLU2020": "Categorical",
            "LCLUC2000-2020change": "Categorical",
        },
        "eo:gsd": [30.0],
        "proj:epsg": [4326],
        "classes": [
            "See full legend: https://storage.googleapis.com/earthenginepartners-hansen/GLCLU2000-2020/legend.xlsx"
        ],
        "product_family": ["GLAD LCLUC"],
        "data_format": ["zarr"],
    },
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Potapov Land Cover Land Use Change (LCLUC)",
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
    },
    # ------------------------------------------------------------------
    # Asset template (add roles + description as you requested)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/POTAPOV_LCLUC_v{v}.zarr",
            title=f"Potapov Land Cover and Land Use Change 2000-2020 v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing annual land cover and land use change layers "
                "for the Potapov LCLUC product."
            ),
        ),
    },
}
