# eoforeststac/products/jrc_gfc.py
import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

JRC_GFC_CFG = {
    "id": "JRC_GFC2020",
    "title": "JRC Global Forest Cover 2020",
    "description": (
        "Global Forest Cover (GFC) map produced by the Joint Research Centre (JRC). "
        "The product provides a global categorical forest cover classification "
        "for the reference year 2020, derived from Copernicus Sentinel data. "
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

    # Nominal reference year
    "start_datetime": datetime.datetime(2020, 1, 1),
    "end_datetime": datetime.datetime(2020, 12, 31),

    # ------------------------------------------------------------------
    # STAC paths
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/JRC_GFC2020/collection.json",
    "base_path": f"{BASE_S3_URL}/JRC_GFC2020",

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------
    "providers": [
        {
            "name": "European Commission – Joint Research Centre (JRC)",
            "roles": ["producer"],
            "url": "https://forobs.jrc.ec.europa.eu/GFC"
        }
    ],

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/JRC_GFC2020_v{v}.zarr",
            title=f"JRC GFC2020 v{v} Zarr")
        }
    }




