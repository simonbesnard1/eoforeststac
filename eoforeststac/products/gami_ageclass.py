import datetime
from eoforeststac.core.config import S3_HTTP_BASE
from eoforeststac.core.assets import create_zarr_asset

# Mapping: resolution label -> (GSD in metres at equator, input dir suffix)
GAMI_AGECLASS_RESOLUTIONS = {
    "1deg": {"gsd": 111320.0, "dir": "AgeClass_1deg"},
    "0.5deg": {"gsd": 55660.0, "dir": "AgeClass_0.5deg"},
    "0.25deg": {"gsd": 27830.0, "dir": "AgeClass_0.25deg"},
    "0.1deg": {"gsd": 11132.0, "dir": "AgeClass_0.1deg"},
    "0.083deg": {"gsd": 9240.0, "dir": "AgeClass_0.083deg"},
}

GAMI_AGECLASS_CFG = {
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    "id": "GAMI_AGECLASS",
    "title": "GAMI – Global Forest Age-Class Fractions (multi-resolution)",
    "description": (
        "Global gridded forest age-class fraction product derived from the Global Age Mapping "
        "Integration (GAMI) ensemble. Each pixel contains the fractional area of forest "
        "belonging to 12 age classes (0–20, 20–40, …, >299 years) for reference years "
        "2010 and 2020.\n\n"
        "Uncertainty representation: the 'members' dimension holds 20 ensemble realisations "
        "allowing downstream uncertainty propagation via member statistics (mean/IQR).\n\n"
        "Available at five spatial resolutions: 1°, 0.5°, 0.25°, 0.1°, and 0.083°. "
        "Each resolution is registered as a separate STAC item within this collection.\n\n"
        "This collection provides analysis-ready Zarr packaging for cloud-native access."
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
    "start_datetime": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),
    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{S3_HTTP_BASE}/GAMI_AGECLASS/collection.json",
    "base_path": f"{S3_HTTP_BASE}/GAMI_AGECLASS",
    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "CC-BY-4.0",
    "providers": [
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["producer", "processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],
    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    "keywords": [
        "forest age",
        "age class",
        "age structure",
        "stand age",
        "demography",
        "machine learning",
        "ensemble",
        "uncertainty",
        "carbon cycle",
        "global",
        "multi-resolution",
        "zarr",
        "stac",
    ],
    "themes": ["forest structure", "carbon", "demography"],
    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5880/GFZ.1.4.2023.006",
            "type": "text/html",
            "title": "GAMI dataset DOI (GFZ Data Services)",
        },
        {
            "rel": "related",
            "href": "https://doi.org/10.5194/essd-13-4881-2021",
            "type": "text/html",
            "title": "Peer-reviewed paper (ESSD, 2021)",
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
    # Summaries (collection-level; items carry resolution-specific values)
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["multi-epoch"],
        "reference_years": [2010, 2020],
        "variables": ["forest_age"],
        "units_by_variable": {"forest_age": "fraction"},
        "age_classes": [
            "0-20",
            "20-40",
            "40-60",
            "60-80",
            "80-100",
            "100-120",
            "120-140",
            "140-160",
            "160-180",
            "180-200",
            "200-299",
            ">299",
        ],
        "n_age_classes": [12],
        "ensemble_dimension": ["members"],
        "ensemble_members": [20],
        "spatial_resolutions": list(GAMI_AGECLASS_RESOLUTIONS.keys()),
        "proj:epsg": [4326],
        "product_family": ["GAMI"],
        "data_format": ["zarr"],
    },
    # ------------------------------------------------------------------
    # Item assets template
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store of global forest age-class fractions. "
                "Dimensions: (members=20, age_class=12, latitude, longitude, time=2)."
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        }
    },
    # ------------------------------------------------------------------
    # Asset template — resolution injected at item creation time
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v, resolution="": create_zarr_asset(
            href=f"{cfg['base_path']}/GAMI_AGECLASS_{resolution}_v{v}.zarr",
            title=f"GAMI Age-Class Fractions {resolution} v{v} (Zarr)",
            roles=["data"],
            description=(
                f"Cloud-optimized Zarr store of global forest age-class fractions "
                f"at {resolution} spatial resolution. "
                "Dimensions: members (20 ensemble members), age_class (12 classes), "
                "latitude, longitude, time (2010, 2020)."
            ),
        ),
    },
}
