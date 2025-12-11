import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

POTAPOV_HEIGHT_CFG = {
    "id": "POTAPOV_HEIGHT",
    "title": "Global Canopy Height (Potapov et al.)",
    "description": "Global canopy height dataset derived from Landsat and ICESat-2.",
    "bbox": [-180, -90, 180, 90],
    "start_datetime": datetime.datetime(2005, 1, 1),
    "end_datetime": datetime.datetime(2020, 1, 1),
    "collection_href": f"{BASE_S3_URL}/POTAPOV_HEIGHT/collection.json",
    "base_path": f"{BASE_S3_URL}/POTAPOV_HEIGHT",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180,-90],[-180,90],[180,90],[180,-90],[-180,-90]]],
    },
    "providers": [
        {"name": "UMD Global Forest Watch", "roles": ["producer"], "url": "https://glad.umd.edu/"}
    ],
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/POTAPOV_HEIGHT_v{v}.zarr",
            title=f"Potapov Height v{v}"
        )
    }
}

