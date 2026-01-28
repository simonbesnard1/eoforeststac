# SPDX-License-Identifier: MIT
# Copyright (c) 2025
# Simon Besnard, GFZ Potsdam
#
# eoforeststac – STAC catalogs and Zarr writers for forest EO data
#

from importlib.metadata import version as _version

# -----------------------------------------------------------------------------
# Version
# -----------------------------------------------------------------------------
try:
    __version__ = _version("eoforeststac")
except Exception:
    __version__ = "9999"

# -----------------------------------------------------------------------------
# Core namespaces (public API)
# -----------------------------------------------------------------------------
from eoforeststac import (
    catalog,
    products,
    providers,
    writers,
    core,
)

# -----------------------------------------------------------------------------
# Writers (high-level, stable API)
# -----------------------------------------------------------------------------
from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.writers.CCI_biomass import CCI_BiomassWriter
from eoforeststac.writers.gami import GAMIWriter
from eoforeststac.writers.saatchi_biomass import SaatchiBiomassWriter
from eoforeststac.writers.efda import EFDAWriter
from eoforeststac.writers.jrc_tmf import JRCTMFWriter
from eoforeststac.writers.potapov_height import PotapovHeightWriter

# -----------------------------------------------------------------------------
# Catalog builders (collections + items)
# -----------------------------------------------------------------------------
from eoforeststac.catalog.root import build_root_catalog
from eoforeststac.catalog.factory import (
    create_collection,
    create_item,
)

# -----------------------------------------------------------------------------
# Configuration helpers
# -----------------------------------------------------------------------------
from eoforeststac.core.config import (
    BASE_S3_URL,
    S3_ENDPOINT_URL,
)

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
__all__ = [
    # version
    "__version__",
    # namespaces
    "catalog",
    "products",
    "providers",
    "writers",
    "core",
    # writers
    "BaseZarrWriter",
    "CCI_BiomassWriter",
    "GAMIWriter",
    "SaatchiBiomassWriter",
    "EFDAWriter",
    "JRCTMFWriter",
    "PotapovHeightWriter",
    # catalog builders
    "build_root_catalog",
    "create_collection",
    "create_item",
    # config
    "BASE_S3_URL",
    "S3_ENDPOINT_URL",
]
