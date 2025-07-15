import pystac
import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_geotiff_asset 

def create_efda_collection() -> pystac.Collection:
    return pystac.Collection(
        id="EFDA",
        title="European Forest Disturbance Atlas (EFDA)",
        description=(
            "Maps of annual forest disturbances across 38 European countries derived from Landsat data. "
            "Layers include year of disturbance, number of disturbances, severity, and agents (wind/bark beetle, fire, harvest). "
            "Version 2.1.1 includes updates from 1985 to 2023."
        ),
        license="CC-BY-4.0",
        providers=[
            pystac.Provider(
                name="Viana-Soto, Alba and Senf, Cornelius",
                roles=["producer", "licensor"],
                url="https://www.gfz-potsdam.de/en/"
            )
        ],
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent([[2400000, 1300000, 6600000, 5500000]]),  # EPSG:3035 bounds
            temporal=pystac.TemporalExtent([
                [datetime.datetime(1985, 1, 1, tzinfo=datetime.timezone.utc),
                 datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc)]
            ])
        ),
        keywords=["Forest Disturbance", "Remote Sensing", "Europe", "Landsat", "EFDA"],
        href=f"{BASE_S3_URL}/EFDA/collection.json"
    )

def create_efda_item(year: int, version: str) -> pystac.Item:
    item_id =f"EFDA_{year}_v{version}"
    item = pystac.Item(
        id=item_id,
        geometry=None,  
        bbox=[2400000, 1300000, 6600000, 5500000],
        datetime=datetime.datetime(year, 7, 1),
        properties={
            "product_name": "European Forest Disturbance Atlas (EFDA)",
            "year": year,
            "epsg": 3035,
            "version": version,
        },
        href=f"{BASE_S3_URL}/EFDA/v{version}/{year}/item.json"
    )

    # Add all relevant assets (GeoTIFFs)
    item.add_asset("disturbance", create_geotiff_asset(
        href=f"{BASE_S3_URL}/EFDA/v{version}/{year}_disturb_mosaic_v{version.replace('.', '')}_22_epsg3035.tif",
        title="Annual disturbance (stacked)",
        description="Binary disturbance mask (1=disturbed, 0=undisturbed)"
    ))
    item.add_asset("agent", create_geotiff_asset(
        href=f"{BASE_S3_URL}/EFDA/v{version}/{year}_disturb_agent_v{version.replace('.', '')}_reclass_compv211_epsg3035.tif",
        title="Annual disturbance agent",
        description="Causal agent: 1=wind/beetle, 2=fire, 3=harvest, 4=mixed"
    ))
    
    return item
