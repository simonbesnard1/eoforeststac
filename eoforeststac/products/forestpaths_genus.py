import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset


FORESTPATHS_GENUS_CFG = {
    "id": "FORESTPATHS_GENUS",
    "title": "European Forest Genus Composition (ForestPaths)",
    "description": (
        "European map of dominant forest genus derived from the ForestPaths framework. "
        "The product provides genus-level forest composition at 10 m spatial resolution."
    ),

    # ------------------------------------------------------------------
    # Spatial (Europe, projected)
    # ------------------------------------------------------------------
    "bbox": [-35.0, 34.0, 45.0, 72.0],  # approximate Europe extent in lon/lat
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-35.0, 34.0],
            [-35.0, 72.0],
            [ 45.0, 72.0],
            [ 45.0, 34.0],
            [-35.0, 34.0],
        ]],
    },

    # ---- temporal (static product, encoded as nominal year) ----
    "start_datetime": datetime.datetime(
        2020, 1, 1, tzinfo=datetime.timezone.utc
    ),
    "end_datetime": datetime.datetime(
        2020, 12, 31, tzinfo=datetime.timezone.utc
    ),

    # ---- STAC wiring ----
    "collection_href": f"{BASE_S3_URL}/FORESTPATHS_GENUS/collection.json",
    "base_path": f"{BASE_S3_URL}/FORESTPATHS_GENUS",

    # ---- provenance ----
    "providers": [
        {
            "name": "ForestPaths Consortium",
            "roles": ["producer", "processor"],
            "url": "https://zenodo.org/records/13341104",
        }
    ],

    # ---- citation & licensing (important for this product) ----
    "links": [
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5281/zenodo.13341104",
            "type": "text/html",
        }
    ],

    # ---- assets ----
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/FORESTPATHS_GENUS_v{v}.zarr",
            title=f"ForestPaths genus composition map v{v}",
        ),
    },
}
