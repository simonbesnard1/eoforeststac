import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

RADD_EUROPE_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "RADD_EUROPE",
    "title": "RADD Europe - Monthly forest disturbance occurrence (Sentinel-1, 10 m)",
    "description": (
        "Monthly forest disturbance occurrence for Europe derived from RADD (RAdar for Detecting Deforestation)"
        "alerts based on Sentinel-1 radar time series and ERA5 temperature data. Native alert dates encoded as YYddd"
        "are retained as a static alert layer and additionally converted into a monthly time series indicating the month"
        "in which an alert was triggered for each pixel. The collection includes (i) a monthly binary disturbance cube (ii)"
        "native alert dates and (iii) a forest mask. Within the valid domain, the forest mask has classes 0/1; pixels outside"
        "the mask domain are set to -9999. Binary disturbance occurrence is provided on a monthly time axis and uses -9999 outside"
        "the valid domain. Data are provided in the ETRS89 / LAEA Europe projection (EPSG:3035)."
    ),
    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    # NOTE: STAC bbox/geometry should be WGS84 lon/lat. If you have the exact
    # Europe footprint, replace this with your computed bounds.
    "bbox": [-25.0, 34.0, 45.0, 72.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-25.0, 34.0],
                [-25.0, 72.0],
                [45.0, 72.0],
                [45.0, 34.0],
                [-25.0, 34.0],
            ]
        ],
    },
    "start_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),
    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/RADD_EUROPE/collection.json",
    "base_path": f"{BASE_S3_URL}/RADD_EUROPE",
    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    # If you have an explicit license/terms page, update this.
    "license": "proprietary",
    "providers": [
        {
            "name": "Wageningen University & Research (WUR)",
            "roles": ["producer"],
            "url": "https://www.wur.nl",
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
        {
            "name": "OEMC - Open-Earth-Monitor Cyberinfrastructure",
            "roles": ["funding"],
            "url": "https://cordis.europa.eu/project/id/101059548",
        },
    ],
    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    "keywords": [
        "forest disturbance",
        "disturbance alerts",
        "RADD",
        "Sentinel-1",
        "radar",
        "Europe",
        "monthly",
        "remote sensing",
        "zarr",
        "stac",
    ],
    "themes": ["forest disturbance", "risk", "forest structure"],
    # ------------------------------------------------------------------
    # Links (what makes STAC Browser feel curated)
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "about",
            "href": "https://www.wur.nl/en/research-results/chair-groups/environmental-sciences/"
            "laboratory-of-geo-information-science-and-remote-sensing/research/"
            "sensing-measuring/radd-forest-disturbance-alert.htm",
            "type": "text/html",
            "title": "RADD Forest Disturbance Alert (method overview)",
        },
        {
            "rel": "cite-as",
            "href": "hhttps://iopscience.iop.org/article/10.1088/1748-9326/ad2d82",
            "type": "text/html",
            "title": "paper DOI",
        },
        # Terms of use (if you have it)
        # {
        #     "rel": "license",
        #     "href": "https://.../terms",
        #     "type": "text/html",
        #     "title": "Terms of use / licensing",
        # },
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
    ],
    # ------------------------------------------------------------------
    # Summaries
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["monthly"],
        "variables": [
            "disturbance_occurence",
            "alert_yydoy",
            "forest_mask",
        ],
        "units_by_variable": {
            "disturbance_occurence": "binary",
            "alert_yydoy": "YYddd",
            "forest_mask": "binary",
        },
        "variable_descriptions": {
            "disturbance_occurence": (
                "Binary monthly indicator of forest disturbance occurrence. "
                "A value of 1 indicates that a RADD alert was triggered in the corresponding month. "
                "Values are 0 otherwise within the valid forest mask domain."
            ),
            "alert_yydoy": (
                "Native RADD alert date encoded as YYddd (year since 2000 and day of year). "
                "Each pixel contains at most one alert date. Pixels without alerts or "
                "outside the valid domain are set to the dataset fill value."
            ),
            "forest_mask": (
                "Categorical forest mask indicating forest (1) and non-forest (0) areas "
                "within the valid domain."
            ),
        },
        "eo:gsd": [10.0],
        "proj:epsg": [3035],
        "data_format": ["zarr"],
    },
    # ------------------------------------------------------------------
    # Item assets (how a client should interpret the asset)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store containing monthly disturbance occurrence "
                "and a categorical forest mask."
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
        # Optional thumbnail (collection list only, if you want)
        # "thumbnail": {
        #     "href": "https://raw.githubusercontent.com/.../radd_europe.png",
        #     "type": "image/png",
        #     "title": "RADD Europe quicklook",
        #     "roles": ["thumbnail"],
        # },
    },
    # ------------------------------------------------------------------
    # Asset template
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/RADD_EUROPE_v{v}.zarr",
            title=f"RADD Europe v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing (i) monthly forest disturbance occurrence,"
                "(ii) native RADD alert dates encoded as YYddd, and (iii) a categorical forest mask."
                "Projection: EPSG:3035."
            ),
        ),
    },
}
