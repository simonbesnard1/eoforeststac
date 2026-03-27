import datetime
from eoforeststac.core.config import S3_HTTP_BASE
from eoforeststac.core.assets import create_zarr_asset

RESTOR_LANDUSE_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "RESTOR_LANDUSE",
    "title": "Annual Land Use and Land Cover maps for the Brazilian Amazon (2000 - 2022)(30 m)",
    "description": (
        "Annual Land Use and Land Cover maps for the Brazilian "
        "Amazon dataset, covering the Brazilian Amazon biome. .\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
    ),
    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-74.6193, -16.4822, -42.8267, 5.8892],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-74.6193, -16.4822],
                [-74.6193, 5.8892],
                [-42.8267, 5.8892],
                [-42.8267, -16.4822],
                [-74.6193, -16.4822],
            ]
        ],
    },
    "start_datetime": datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2022, 12, 31, tzinfo=datetime.timezone.utc),
    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{S3_HTTP_BASE}/RESTOR_LANDUSE/collection.json",
    "base_path": f"{S3_HTTP_BASE}/RESTOR_LANDUSE",
    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "Open-access",
    "providers": [
        {
            "name": "National Institute for Space Research (INPE)",
            "roles": ["producer"],
            "url": "https://www3.inpe.br/50anos/english/presentation.php",
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
        "land-use",
        "land cover",
        "Brazil",
        "Amazon",
        "annual",
        "INPE",
        "remote sensing",
        "zarr",
        "stac",
    ],
    # ------------------------------------------------------------------
    # Links (what makes STAC Browser feel curated)
    # ------------------------------------------------------------------
    "links": [
        # If you have a canonical terms/licensing page, link it explicitly
        {
            "rel": "cite-as",
            "href": "https://zenodo.org/records/18716512",
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
        "temporal_resolution": ["annual"],
        # core data semantics
        "variables": ["lulc"],
        "units": ["categorical"],
        # spatial metadata
        "eo:gsd": [30.0],
        "proj:wkt2": "+proj=aea +lat_0=-12 +lon_0=-54 +lat_1=-2 +lat_2=-22 +x_0=5000000 +y_0=10000000 +ellps=GRS80 +units=m +no_defs",
        "data_format": ["zarr"],
        # classification legend (1..14)
        "classes": [
            {"value": 1, "name": "Annual agriculture"},
            {"value": 2, "name": "Semi-perennial agriculture"},
            {"value": 3, "name": "Water"},
            {"value": 4, "name": "Forest"},
            {"value": 5, "name": "Silviculture"},
            {"value": 6, "name": "Secondary vegetation"},
            {"value": 7, "name": "Mining"},
            {"value": 8, "name": "Urbanized area"},
            {"value": 9, "name": "Non-forest natural vegetation"},
            {"value": 10, "name": "Pasture"},
            {"value": 11, "name": "Seasonally flooded"},
            {"value": 12, "name": "Deforestation of the year"},
            {"value": 13, "name": "Perennial agriculture"},
            {"value": 14, "name": "Not observed"},
        ],
        "product_family": ["RESTOR LAND USE"],
        "data_format": ["zarr"],
    },
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Annual land use and land cover maps .",
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
        # "thumbnail": {
        #       "href": "https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/thumbnails/cci_biomass.png",
        #       "type": "image/png",
        #       "title": "AGB quicklook",
        #       "roles": ["thumbnail"],
        #   }
    },
    # ------------------------------------------------------------------
    # Asset template (add roles + description as you requested)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/RESTOR_LANDUSE_v{v}.zarr",
            title=f"RESTOR Land Use v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing annual land use and land cover (LULC) maps "
                "for the Brazilian Amazon biome (2000–2022)."
            ),
        ),
    },
}
