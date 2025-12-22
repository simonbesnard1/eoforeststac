# eoforeststac/products/hansen_gfc.py

import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

HANSEN_GFC_CFG = {
    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    "id": "HANSEN_GFC",
    "title": "Global Forest Change (Hansen et al.)",
    "description": (
        "Global Forest Change (GFC) dataset derived from Landsat imagery, "
        "quantifying global forest extent, loss, and gain from 2000 to 2024. "
        "The product includes percent tree cover for year 2000, annual forest "
        "loss year, forest gain (2000–2012), and ancillary layers. "
        "Produced by the University of Maryland and partners."
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

    # Nominal temporal coverage
    "start_datetime": datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2024, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC paths
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/HANSEN_GFC/collection.json",
    "base_path": f"{BASE_S3_URL}/HANSEN_GFC",

    # ------------------------------------------------------------------
    # Provenance / citation
    # ------------------------------------------------------------------
    "providers": [
        {
            "name": "University of Maryland, Department of Geographical Sciences",
            "roles": ["producer"],
            "url": "https://glad.umd.edu"
        },
        {
            "name": "Google Earth Engine",
            "roles": ["processor", "host"],
            "url": "https://earthengine.google.com"
        },
    ],

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/HANSEN_GFC_v{v}.zarr",
            title=f"Global Forest Change (Hansen et al.) v{v} – Zarr"
        )
    },

    # ------------------------------------------------------------------
    # Extra metadata (optional but useful downstream)
    # ------------------------------------------------------------------
    "keywords": [
        "forest cover",
        "deforestation",
        "forest loss",
        "forest gain",
        "landsat",
        "global",
    ],

    "references": [
        "https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html",
        "https://doi.org/10.1126/science.1244693",
    ],

    "spatial_resolution": "30 m",
    "crs": "EPSG:4326",
}
