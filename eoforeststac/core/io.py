import boto3
import fsspec
import pystac
from eoforeststac.core.config import S3_PROFILE, S3_ENDPOINT_URL

session = boto3.Session(profile_name=S3_PROFILE)

# fsspec for reading
fs = fsspec.filesystem(
    "s3",
    client_kwargs={"endpoint_url": S3_ENDPOINT_URL, "profile": S3_PROFILE}
)

# boto3 client for writing
s3_client = session.client("s3", endpoint_url=S3_ENDPOINT_URL)

class S3StacIO(pystac.StacIO):
    def read_text(self, href: str) -> str:
        with fs.open(href, "r") as f:
            return f.read()

    def write_text(self, href: str, txt: str) -> None:
        if not href.startswith("s3://"):
            raise ValueError("Expected s3:// URL")
        bucket, key = href.replace("s3://", "").split("/", 1)
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=txt.encode("utf-8"),
            ContentType="application/json"
        )

    def exists(self, href: str) -> bool:
        return fs.exists(href)


def register_io():
    pystac.StacIO.set_default(S3StacIO)
