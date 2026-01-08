# eoforeststac/products/gami.py
import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

GAMI_CFG = {
    # ---- identity ----
    "id": "GAMI",
    "title": "GAMI – Global Forest Age Maps",
    "description": (
        "Global gridded forest age product derived by integrating machine-learning models "
        "with remote sensing and reference forest inventory information. "
        "Provides spatially explicit forest age estimates and uncertainty."
    ),

    # ---- spatial extent ----
    "bbox": [-180, -90, 180, 90],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]],
    },

    # ---- temporal semantics ----
    # IMPORTANT: for age products the meaning of time can be subtle:
    # - a "reference year" (age at year X)
    # - a multi-year composite / harmonized time window
    #
    # Keep interval broad & honest unless you have per-version specifics.
    "start_datetime": datetime.datetime(2010, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),
    "temporal_notes": (
        "Temporal extent denotes the reference period/years used for harmonization. "
        "For each version, items describe the exact reference year(s) of age estimates."
    ),

    # ---- STAC wiring ----
    "collection_href": f"{BASE_S3_URL}/GAMI/collection.json",
    "base_path": f"{BASE_S3_URL}/GAMI",

    # ---- governance ----
    # Put the real license string if you have it (e.g. CC-BY-4.0). Otherwise keep 'various' for safety.
    "license": "various",

    "providers": [
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["producer", "processor", "host"],
            "url": "https://www.gfz.de",
        },
        # Optional: if there is a consortium/institution list, add it here.
    ],

    "keywords": [
        "stand age",
        "machine learning",
        "remote sensing",
        "carbon cycle",
        "forest demography",
        "global",
    ],

    # ---- links ----
    "links": [
    {
        "rel": "cite-as",
        "href": "https://doi.org/10.5880/GFZ.1.4.2023.006",
        "type": "text/html",
        "title": "GAMI dataset DOI (GFZ Data Services)",
    },
    {
        "rel": "related",
        "href": "https://doi.org/10.5194/essd-13-4881-2021",
        "type": "text/html",
        "title": "Peer-reviewed paper (ESSD, 2021)",
    },
],

    # ---- extensions (optional but recommended) ----
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
        # "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
    ],

    # ---- summaries: structured metadata clients can use ----
    # Keep unknowns out; add once you confirm.
    "summaries": {
        "temporal_resolution": ["static"],  # age map for a reference year/period (not a daily time series)
        "variables": ["forest_age"],
        "units": ["years"],
        "eo:gsd": [100],      # e.g., 100 m
        "proj:epsg": [4326],  # or whatever you store
    },

    # ---- assets ----
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/GAMI_v{v}.zarr",
            title=f"GAMI v{v} (Zarr)",
            roles=["data"],
            description="Zarr store of global forest age estimates.",
        ),
    },

    # Optional: version-specific notes (super nice in STAC Browser)
    "version_notes": {
        "2.0": "Initial public release.",
        "2.1": "Incremental updates and/or bug fixes.",
        "3.0": "Major update (methods/data).",
        "3.1": "Minor update (methods/data).",
    },
}

