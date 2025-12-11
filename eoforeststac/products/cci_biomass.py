import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

CCI_BIOMASS_CFG = {
    "id": "CCI_BIOMASS",
    "title": "ESA CCI Biomass Global Annual Maps",
    "description": "Aboveground biomass (AGB) product from ESA Climate Change Initiative.",
    "bbox": [-180, -90, 180, 90],
    "start_datetime": datetime.datetime(2007, 1, 1),
    "end_datetime": datetime.datetime(2020, 12, 31),
    "collection_href": f"{BASE_S3_URL}/CCI_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/CCI_BIOMASS",
    "geometry": {"type": "Polygon", "coordinates": [[[-180,-90],[-180,90],[180,90],[180,-90],[-180,-90]]]},
    "providers": [{"name": "ESA CCI", "roles": ["producer"], "url": "https://climate.esa.int"}],
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/CCI_BIOMASS_v{v}.zarr",
            title=f"CCI Biomass v{v} Zarr"
        )
    }
}

