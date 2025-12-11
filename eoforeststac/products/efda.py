import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

EFDA_CFG = {
    "id": "EFDA",
    "title": "European Forest Disturbance Atlas (EFDA)",
    "description": "Continental-scale forest disturbance data for Europe, 1985–2023.",
    "bbox": [-25, 34, 45, 72],
    "start_datetime": datetime.datetime(1985, 1, 1),
    "end_datetime": datetime.datetime(2023, 1, 1),
    "collection_href": f"{BASE_S3_URL}/EFDA/collection.json",
    "base_path": f"{BASE_S3_URL}/EFDA",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-25,34],[-25,72],[45,72],[45,34],[-25,34]]],
    },
    "providers": [
        {"name": "GFZ Potsdam", "roles": ["producer"], "url": "https://www.gfz-potsdam.de/"}
    ],
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/EFDA_v{v}.zarr",
            title=f"EFDA v{v}"
        )
    }
}

