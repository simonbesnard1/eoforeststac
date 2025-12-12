"""
eoforeststac
============

STAC catalogs and Zarr writers for forest Earth Observation datasets.
"""

from . import writers
from . import catalog
from . import providers
from . import products
from .core.config import BASE_S3_URL

__all__ = [
    "writers",
    "catalog",
    "providers",
    "products",
    "BASE_S3_URL",
]

