import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

JRC_GFC_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "JRC_GFC2020",
    "title": "JRC Global Forest Cover 2020 (GFC2020) – Forest presence/absence (10 m)",
    "description": (
        "Global forest cover map for reference year 2020 produced by the European Commission’s "
        "Joint Research Centre (JRC). Provides a harmonized, globally consistent representation "
        "of forest presence/absence at 10 m resolution, developed to support the EU Regulation "
        "on deforestation-free supply chains (EUDR) cutoff date context.\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -90.0, 180.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-180.0, -90.0],
            [-180.0,  90.0],
            [ 180.0,  90.0],
            [ 180.0, -90.0],
            [-180.0, -90.0],
        ]],
    },
    "start_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/JRC_GFC2020/collection.json",
    "base_path": f"{BASE_S3_URL}/JRC_GFC2020",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "various",
    "providers": [
        {
            "name": "European Commission – Joint Research Centre (JRC)",
            "roles": ["producer"],
            "url": "https://forobs.jrc.ec.europa.eu/GFC",
        },
        {
            "name": "Google Earth Engine",
            "roles": ["host"],
            "url": "https://developers.google.com/earth-engine",
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
        "forest cover",
        "forest presence",
        "presence/absence",
        "EUDR",
        "deforestation-free supply chains",
        "JRC",
        "global",
        "10 m",
        "2020",
        "zarr",
        "stac",
    ],
    "themes": ["land cover", "forest structure", "policy"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
       
        # Canonical resources
        {
            "rel": "about",
            "href": "https://forobs.jrc.ec.europa.eu/GFC",
            "type": "text/html",
            "title": "JRC Forest Observatory – Global Forest Cover 2020 (download portal)",
        },
        {
            "rel": "related",
            "href": "https://developers.google.com/earth-engine/datasets/catalog/JRC_GFC2020_V3",
            "type": "text/html",
            "title": "Earth Engine catalog entry (JRC/GFC2020/V3)",
        },
        {
            "rel": "documentation",
            "href": "https://publications.jrc.ec.europa.eu/repository/handle/JRC136960",
            "type": "text/html",
            "title": "JRC technical report (method overview)",
        },
        {
            "rel": "related",
            "href": "https://data.europa.eu/89h/8c561543-31df-4e1b-9994-e529afecaf54",
            "type": "text/html",
            "title": "EU Open Data Portal entry (GFC2020 v3 metadata)",
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
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",
        "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Summaries (client-friendly structured metadata)
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["static"],
        "variables": ["forest"],
        "units": ["binary"],

        "eo:gsd": [10.0],
        "proj:epsg": [4326],  # consistent with bbox/geometry (swap if your Zarr is in another CRS)

        "data_format": ["zarr"],

        "classes": [
            {"value": 0, "name": "non-forest"},
            {"value": 1, "name": "forest"},
        ],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Cloud-optimized Zarr store of JRC GFC2020 (forest presence/absence for 2020).",
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
        "thumbnail": {
            "title": "Preview",
            "roles": ["thumbnail"],
            "type": "image/png",
        },
    },

    # ------------------------------------------------------------------
    # Asset template (roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/JRC_GFC2020_v{v}.zarr",
            title=f"JRC GFC2020 v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing the JRC Global Forest Cover 2020 product "
                "(forest presence/absence at 10 m, reference year 2020)."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes (optional)
    # ------------------------------------------------------------------
    "version_notes": {
        "3.0": "GFC2020 version 3 distribution/packaging.",
    },
}
