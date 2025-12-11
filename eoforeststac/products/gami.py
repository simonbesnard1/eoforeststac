# eoforeststac/products/gami.py
import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

GAMI_CFG = {
    "id": "GAMI",
    "title": "Global Age Mapping Integration (GAMI)",
    "description": "Forest age derived from machine learning and remote sensing.",
    "bbox": [-180, -90, 180, 90],
    "start_datetime": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "collection_href": f"{BASE_S3_URL}/GAMI/collection.json",
    "base_path": f"{BASE_S3_URL}/GAMI",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]
        ]]
    },
    "providers": [
        {
            "name": "GFZ Potsdam",
            "roles": ["producer", "licensor"],
            "url": "https://www.gfz-potsdam.de/"
        }
    ],
    "keywords": ["Forest Age", "Remote Sensing", "Machine Learning"],
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/GAMI_v{v}.zarr",
            title=f"GAMI v{v} Zarr"
        )
    }
}
