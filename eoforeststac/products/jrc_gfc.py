# eoforeststac/products/jrc_gfc.py
import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

JRC_GFC_CFG = {
    "id": "JRC_GFC2020",
    "title": "JRC Global Forest Cover 2020 (GFC2020) – Forest presence/absence",
    "description": (
        "Global forest cover map for reference year 2020 produced by the European Commission’s "
        "Joint Research Centre (JRC). Provides a harmonized, globally consistent representation "
        "of forest presence/absence at 10 m resolution, developed to support the EU Regulation "
        "on deforestation-free supply chains (EUDR) cutoff date context."
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
        ]]
    },
    "start_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC paths
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/JRC_GFC2020/collection.json",
    "base_path": f"{BASE_S3_URL}/JRC_GFC2020",

    # ------------------------------------------------------------------
    # Governance / provenance
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

    "keywords": [
        "forest cover",
        "forest presence",
        "EUDR",
        "deforestation-free supply chains",
        "JRC",
        "Copernicus",
        "Sentinel",
        "global",
        "10m",
        "2020",
    ],

    # ------------------------------------------------------------------
    # Canonical links (STAC style)
    # ------------------------------------------------------------------
    "links": [
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
            "title": "JRC technical report (method overview, v1)",
        },
        {
            "rel": "related",
            "href": "https://data.europa.eu/89h/8c561543-31df-4e1b-9994-e529afecaf54",
            "type": "text/html",
            "title": "EU Open Data Portal entry (GFC2020 v3 metadata)",
        },
    ],

    # ------------------------------------------------------------------
    # Extensions
    # ------------------------------------------------------------------
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Structured summaries
    # ------------------------------------------------------------------
    "summaries": {
        "eo:gsd": [10],           # 10 m resolution :contentReference[oaicite:2]{index=2}
        "temporal_resolution": ["static"],
        "variables": ["forest"],  # presence/absence
        "classes": [
            {"value": 0, "name": "non-forest"},
            {"value": 1, "name": "forest"},
        ],
        "product_versions": ["3"],  # portal says “version 3” for GFC2020 :contentReference[oaicite:3]{index=3}
    },

    # ------------------------------------------------------------------
    # Assets (note roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/JRC_GFC2020_v{v}.zarr",
            title=f"JRC GFC2020 v{v} (Zarr)",
            roles=["data"],
            description=(
                "Zarr packaging of the JRC Global Forest Cover 2020 product "
                "(forest presence/absence at 10 m, reference year 2020)."
            ),
        ),
    },

    # Optional: short per-version notes (useful if you expose multiple)
    "version_notes": {
        "3.0": "GFC2020 version 3 distribution/packaging.",
    },
}

