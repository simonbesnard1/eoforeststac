# eoforeststac/catalog/reader.py

import json

import pystac

from eoforeststac.core.io import read_text


def read_collection(href: str) -> pystac.Collection:
    """Read a Collection from S3 or the local filesystem (fsspec-backed)."""
    collection = pystac.Collection.from_dict(json.loads(read_text(href)))
    collection.set_self_href(href)
    return collection


def read_item(href: str) -> pystac.Item:
    """Read an Item from S3 or the local filesystem (fsspec-backed)."""
    item = pystac.Item.from_dict(json.loads(read_text(href)))
    item.set_self_href(href)
    return item
