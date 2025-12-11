import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

SAATCHI_BIOMASS_CFG = {
    "id": "SAATCHI_BIOMASS",
    "title": "Global Aboveground Biomass (Saatchi et al.)",
    "description": "Global AGB estimates derived from radar and field datasets (Saatchi et al. 2020).",
    "bbox": [-180, -90, 180, 90],
    "start_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),
    "collection_href": f"{BASE_S3_URL}/SAATCHI_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/SAATCHI_BIOMASS",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180,-90],[-180,90],[180,90],[180,-90],[-180,-90]]],
    },
    "providers": [
        {"name": "NASA JPL", "roles": ["producer"], "url": "https://www.jpl.nasa.gov/"}
    ],
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/SAATCHI_BIOMASS_v{v}.zarr",
            title=f"Saatchi Biomass v{v}"
        )
    }
}

