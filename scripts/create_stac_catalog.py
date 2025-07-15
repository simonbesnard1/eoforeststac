import pystac
import datetime
import fsspec

# S3 Bucket Base URL
BASE_S3_URL = "s3://dog.atlaseo-glm.eo-gridded-data/collections"

# 1️⃣ Configure the S3 File System
s3_fs = fsspec.filesystem('s3', profile='atlaseo-glm', endpoint_url='https://s3.gfz-potsdam.de')

# 2️⃣ Custom STAC I/O Class for S3
class S3StacIO(pystac.StacIO):
    s3_fs = s3_fs

    def read_text(self, href: str) -> str:
        with self.s3_fs.open(href, "r") as f:
            return f.read()

    def write_text(self, href: str, txt: str) -> None:
        with self.s3_fs.open(href, "w") as f:
            f.write(txt)

    def exists(self, href: str) -> bool:
        return self.s3_fs.exists(href)

# Register the custom STAC I/O handler
pystac.StacIO.set_default(S3StacIO)

# 3️⃣ Create the Root STAC Catalog
catalog = pystac.Catalog(
    id="EO_Global_Catalog",
    description="STAC catalog for Earth Observation datasets, including Biomass, Forest Age, and Forest Disturbance.",
    href=f"{BASE_S3_URL}/catalog.json"
)

# 4️⃣ GAMI Collection
GAMI_collection = pystac.Collection(
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

# Add Collection to Catalog
catalog.add_child(GAMI_collection)

# 5️⃣ Create GAMI Items with Proper S3 HREFs
def create_gami_item(version: str):
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
        href=f"{BASE_S3_URL}/GAMI/GAMI_v{version}/item.json"  # S3 path for each item
    )

    # Add Zarr Asset with S3 HREF
    item.add_asset(
        "zarr",
        pystac.Asset(
            href=f"s3://dog.atlaseo-glm.eo-gridded-data/collections/GAMI/GAMI_v{version}.zarr",
            media_type="application/vnd+zarr",
            roles=["data"],
        ),
    )

    return item

# Add Items to the Collection
GAMI_collection.add_item(create_gami_item("2.1"))
GAMI_collection.add_item(create_gami_item("2.0"))

# 6️⃣ Normalize HREFs and Save to S3
catalog.normalize_hrefs(BASE_S3_URL)
catalog.save()

print("✅ STAC catalog successfully saved to S3!")
