import pystac
import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

def create_gami_collection() -> pystac.Collection:
    return pystac.Collection(
        id="GAMI",
        title="Global Age Mapping Integration (GAMI)",
        description="Forest age derived using machine learning and remote sensing. Produced by GFZ Potsdam.",
        license="CC-BY-4.0",
        providers=[
            pystac.Provider(
                name="GFZ Potsdam",
                roles=["producer", "licensor"],
                url="https://www.gfz-potsdam.de/en/"
            )
        ],
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent([[-180, -90, 180, 90]]),
            temporal=pystac.TemporalExtent([
                [datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc),
                 datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)]
            ])
        ),
        keywords=["Forest Age", "Remote Sensing", "Machine Learning"],
        href=f"{BASE_S3_URL}/GAMI/collection.json"
    )

def create_gami_item(version: str) -> pystac.Item:
    item = pystac.Item(
        id=f"GAMI_v{version}",
        geometry={
            "type": "Polygon",
            "coordinates": [[[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]],
        },
        bbox=[-180, -90, 180, 90],
        datetime=datetime.datetime(2020, 1, 1),
        properties={
            "product_name": "Global Age Mapping Integration (GAMI)",
            "version": version,
            "start_datetime": "2010-01-01T00:00:00Z",
            "end_datetime": "2020-01-01T00:00:00Z",
        },
        href=f"{BASE_S3_URL}/GAMI/GAMI_v{version}/item.json"
    )

    item.add_asset("zarr", create_zarr_asset(
        f"{BASE_S3_URL}/GAMI/GAMI_v{version}.zarr",
        title=f"GAMI v{version} Zarr"
    ))
    return item

