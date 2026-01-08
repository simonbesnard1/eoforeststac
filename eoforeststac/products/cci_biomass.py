import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

CCI_BIOMASS_CFG = {
    # ---- STAC IDs / text ----
    "id": "CCI_BIOMASS",
    "title": "ESA CCI Biomass – Global Annual Aboveground Biomass",
    "description": (
        "Global annual maps of aboveground biomass (AGB) produced within the ESA Climate "
        "Change Initiative (CCI) Biomass project."
    ),

    # ---- Spatial / temporal extent ----
    # Keep bbox + geometry in config (builder converts to pystac.Extent)
    "bbox": [-180, -90, 180, 90],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]],
    },
    "start_datetime": datetime.datetime(2007, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),

    # ---- Publishing / href layout ----
    "collection_href": f"{BASE_S3_URL}/CCI_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/CCI_BIOMASS",

    # ---- Data governance ----
    # If you know the exact license, replace "various" with e.g. "CC-BY-4.0" etc.
    "license": "various",

    # Providers: consider adding host/processor for your STAC packaging
    "providers": [
        {"name": "ESA Climate Change Initiative (CCI)", "roles": ["producer"], "url": "https://climate.esa.int"},
        {"name": "GFZ Helmholtz Centre Potsdam", "roles": ["processor", "host"], "url": "https://www.gfz.de"},
    ],

    # ---- Discovery / search ----
    "keywords": [
        "aboveground biomass",
        "forest",
        "global",
        "annual",
        "ESA CCI",
        "remote sensing",
    ],

    # ---- Helpful external links (render nicely in STAC Browser) ----
    # Keep these as plain dicts; builder turns into pystac.Link
    "links": [
        {
            "rel": "about",
            "href": "https://climate.esa.int/en/projects/biomass/",
            "title": "ESA CCI Biomass project page",
        },
        # Add DOI landing page here if you have it; leave commented if unknown
        # {"rel": "cite-as", "href": "https://doi.org/...", "title": "Dataset DOI"},
    ],

    # ---- Optional: declare STAC extensions you intend to use ----
    # You don’t have to fully populate them on day 1, but it signals structure.
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",    # eo:gsd, etc.
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",  # proj:epsg, etc.
        # "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
    ],

    # ---- Summaries: structured, client-friendly metadata ----
    # Use only what you’re confident about. Add more over time.
    "summaries": {
        # Resolution / grid (if known; otherwise omit)
        "eo:gsd": [100.0],

        # Variables / units (custom namespace is fine; summaries are flexible)
        "variables": ["agb"],
        "units": ["Mg/ha"],  # change if your product uses different units
        "temporal_resolution": ["annual"],
        "product_family": ["ESA-CCI Biomass"],
    },

    # ---- Assets template ----
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/CCI_BIOMASS_v{v}.zarr",
            title=f"CCI Biomass v{v} (Zarr)",
            roles=["data"],
            description="Zarr store of annual AGB maps.",
        ),
    },
}

