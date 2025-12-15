# eoforeststac/products/robinson_cr.py

import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset


ROBINSON_CR_CFG = {
    "id": "ROBINSON_CR",
    "title": "Global Chapman-Richards Curve Parameters for Secondary Forest Carbon Dynamics",
    "description": (
        "Global pixel-level Chapman–Richards (CR) growth curve parameters and "
        "derived metrics describing aboveground carbon accumulation in secondary forests. "
        "The dataset provides spatially explicit estimates of CR parameters "
        "(a, b, k), their associated standard errors, and derived quantities such as "
        "maximum carbon accumulation rate, age at maximum rate, and relative "
        "carbon removal potential. The product supports analysis of forest regrowth "
        "dynamics and optimal protection strategies for young secondary forests."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -90.0, 108.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-180.0, -90.0],
            [-180.0,  90.0],
            [ 108.0,  90.0],
            [ 108.0, -90.0],
            [-180.0, -90.0],
        ]]
    },

    # Static model product (no explicit time axis)
    "start_datetime": datetime.datetime(2000, 1, 1),
    "end_datetime": datetime.datetime(2020, 12, 31),

    # ------------------------------------------------------------------
    # STAC paths
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/ROBINSON_CR/collection.json",
    "base_path": f"{BASE_S3_URL}/ROBINSON_CR",

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------
    "providers": [
        {
            "name": "Center for International Forestry Research (CIFOR-ICRAF)",
            "roles": ["producer"],
            "url": "https://www.cifor-icraf.org",
        },
        {
            "name": "The Nature Conservancy (TNC)",
            "roles": ["producer"],
            "url": "https://www.nature.org",
        },
    ],

    "contacts": [
        {
            "name": "Nathaniel Robinson",
            "role": "pointOfContact",
            "email": "n.robinson@cifor-icraf.org",
        },
        {
            "name": "Susan Cook-Patton",
            "role": "pointOfContact",
            "email": "susan.cook-patton@tnc.org",
        },
    ],

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    # Single Zarr store containing all CR parameters and derived layers
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/ROBINSON_CR_v{v}.zarr",
            title=f"Global Chapman–Richards Parameters v{v}"
        )
    },

    # ------------------------------------------------------------------
    # Scientific context
    # ------------------------------------------------------------------
    "keywords": [
        "secondary forests",
        "carbon removal",
        "forest regrowth",
        "Chapman-Richards",
        "carbon sequestration",
        "nature-based solutions",
    ],

    "references": [
        {
            "citation": (
                "Robinson et al., Protect young secondary forests for optimum carbon removal"
            ),
            "url": "https://www.nature.com/articles/s41558-025-02355-5",
        }
    ],
}
