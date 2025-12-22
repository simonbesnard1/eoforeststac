import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

JRC_TMF_CFG = {
    "id": "JRC_TMF",
    "title": "Tropical Moist Forest Change (TMF)",
    "description": "Forest disturbance and regrowth dataset for the tropical moist forest biome.",
    "bbox": [-180, -30, 180, 30],
    "start_datetime": datetime.datetime(1990, 1, 1),
    "end_datetime": datetime.datetime(2023, 1, 1),
    "collection_href": f"{BASE_S3_URL}/JRC_TMF/collection.json",
    "base_path": f"{BASE_S3_URL}/JRC_TMF",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180,-30],[-180,30],[180,30],[180,-30],[-180,-30]]],
    },
    "providers": [
        {"name": "JRC", "roles": ["producer"], "url": "https://joint-research-centre.ec.europa.eu/"}
    ],
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/JRC_TMF_v{v}.zarr",
            title=f"TMF v{v}"
        )
    }
}

