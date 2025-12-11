# eoforeststac/core/io.py

import boto3
import fsspec
import json
from botocore.config import Config
from eoforeststac.core.config import S3_ENDPOINT_URL, S3_PROFILE


_s3_client = None
_fs_s3 = None


# -------------------------------------------------------------------
# S3 CLIENT (WRITE)
# -------------------------------------------------------------------
def get_s3_client():
    """Return a boto3 S3 client configured for Ceph RGW."""
    global _s3_client

    if _s3_client is None:
        session = boto3.Session(profile_name=S3_PROFILE or None)

        # Ceph-safe boto3 client configuration
        cfg = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        )

        _s3_client = session.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            config=cfg,
        )

    return _s3_client


# -------------------------------------------------------------------
# S3 FILESYSTEM (READ)
# -------------------------------------------------------------------
def get_fs(url: str):
    """Return fsspec filesystem for reading."""
    global _fs_s3

    if url.startswith("s3://"):
        if _fs_s3 is None:
            _fs_s3 = fsspec.filesystem(
                "s3",
                client_kwargs={"endpoint_url": S3_ENDPOINT_URL},
                profile=S3_PROFILE,
                use_ssl=True,
                config_kwargs={"signature_version": "s3v4"},
            )
        return _fs_s3

    return fsspec.filesystem("file")


# -------------------------------------------------------------------
# I/O FUNCTIONS
# -------------------------------------------------------------------
def write_text(url: str, text: str):
    """Write text to S3 or local filesystem."""
    if url.startswith("s3://"):
        bucket, key = url.replace("s3://", "").split("/", 1)
        client = get_s3_client()

        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=text.encode("utf-8"),
            ContentType="application/json",
        )
        return

    # Local
    with open(url, "w") as f:
        f.write(text)


def read_text(url: str) -> str:
    """Read text from S3 or local filesystem."""
    fs = get_fs(url)
    with fs.open(url, "r") as f:
        return f.read()


def write_json(url: str, obj: dict):
    write_text(url, json.dumps(obj, indent=2))


def exists(url: str) -> bool:
    fs = get_fs(url)
    return fs.exists(url)
