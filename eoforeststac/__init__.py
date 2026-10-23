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
# Public API, imported lazily (PEP 562)
# -----------------------------------------------------------------------------
# Importing one submodule (e.g. eoforeststac.analytics on the tile server)
# must not pull in the writers, catalog builders and S3 stack.
_SUBMODULES = {
    "analytics",
    "catalog",
    "checks",
    "products",
    "providers",
    "pyramids",
    "writers",
    "core",
}
_ATTRIBUTES = {
    # writers (high-level, stable API)
    "BaseZarrWriter": "eoforeststac.writers.base",
    "CCIBiomassWriter": "eoforeststac.writers.CCI_biomass",
    "GAMIWriter": "eoforeststac.writers.gami",
    "SaatchiBiomassWriter": "eoforeststac.writers.saatchi_biomass",
    "EFDAWriter": "eoforeststac.writers.efda",
    "JRCTMFWriter": "eoforeststac.writers.jrc_tmf",
    "PotapovHeightWriter": "eoforeststac.writers.potapov_height",
    # catalog builders (collections + items)
    "build_catalog": "eoforeststac.catalog.root",
    "create_collection": "eoforeststac.catalog.factory",
    "create_item": "eoforeststac.catalog.factory",
    # configuration helpers
    "BASE_S3_URL": "eoforeststac.core.config",
    "S3_ENDPOINT_URL": "eoforeststac.core.config",
}


def __getattr__(name):
    import importlib

    if name in _SUBMODULES:
        return importlib.import_module(f"eoforeststac.{name}")
    if name in _ATTRIBUTES:
        return getattr(importlib.import_module(_ATTRIBUTES[name]), name)
    raise AttributeError(f"module 'eoforeststac' has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | _SUBMODULES | set(_ATTRIBUTES))


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
    "analytics",
    # writers
    "BaseZarrWriter",
    "CCIBiomassWriter",
    "GAMIWriter",
    "SaatchiBiomassWriter",
    "EFDAWriter",
    "JRCTMFWriter",
    "PotapovHeightWriter",
    # catalog builders
    "build_catalog",
    "create_collection",
    "create_item",
    # config
    "BASE_S3_URL",
    "S3_ENDPOINT_URL",
]
