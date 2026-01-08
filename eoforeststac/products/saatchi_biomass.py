# eoforeststac/products/saatchi_biomass.py

import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

SAATCHI_BIOMASS_CFG = {
    "id": "SAATCHI_BIOMASS",
    "title": "Global live woody vegetation / aboveground biomass at 100 m (Saatchi & Yu, 2020 mosaic; Zenodo v2)",
    "description": (
        "Global live woody vegetation biomass mapping product at 100 m spatial resolution, "
        "distributed as a global aboveground biomass mosaic for reference year 2020. "
        "This STAC collection packages the Zenodo deliverable 'Mapping Global Live Woody Vegetation "
        "Biomass at Optimum Spatial Resolutions' and associated supplementary documentation.\n\n"
        "Primary data file on Zenodo: 'global_agb_100m_combined_mosaic_2020_cog.tif' (Cloud-Optimized GeoTIFF)."
    ),

    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -90.0, 180.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [[
            [-180.0, -90.0],
            [-180.0,  90.0],
            [ 180.0,  90.0],
            [ 180.0, -90.0],
            [-180.0, -90.0],
        ]]
    },

    # Reference year (explicit in the Zenodo file name and abstract context) :contentReference[oaicite:1]{index=1}
    "start_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # STAC paths
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/SAATCHI_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/SAATCHI_BIOMASS",

    # ------------------------------------------------------------------
    # Provenance / licensing
    # ------------------------------------------------------------------
    "license": "CC-BY-4.0",  # Zenodo record license is CC BY 4.0 :contentReference[oaicite:2]{index=2}

    "providers": [
        {
            "name": "Jet Propulsion Laboratory (Caltech) – Saatchi et al.",
            "roles": ["producer"],
            "url": "https://www.jpl.nasa.gov/",
        },
        {
            "name": "Zenodo",
            "roles": ["host"],
            "url": "https://zenodo.org/records/15858551",
        },
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],

    "keywords": [
        "aboveground biomass",
        "live woody biomass",
        "carbon density",
        "forest biomass",
        "global",
        "100m",
        "remote sensing",
        "disturbance",
    ],

    # ------------------------------------------------------------------
    # Canonical links
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "about",
            "href": "https://zenodo.org/records/15858551",
            "type": "text/html",
            "title": "Zenodo landing page (files, description, license)",
        },
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5281/zenodo.15858551",
            "type": "text/html",
            "title": "Dataset DOI (Zenodo): Mapping Global Live Woody Vegetation Biomass at Optimum Spatial Resolutions",
        },
        # Zenodo lists a related work under “Compiles” with DOI 10.5281/zenodo.7583611 :contentReference[oaicite:3]{index=3}
        {
            "rel": "related",
            "href": "https://doi.org/10.5281/zenodo.7583611",
            "type": "text/html",
            "title": "Related work (compiled journal article / deliverable link)",
        },
    ],

    # ------------------------------------------------------------------
    # Extensions (optional)
    # ------------------------------------------------------------------
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Structured summaries (keep conservative: only what is explicit)
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["static"],
        "reference_year": [2020],
        "eo:gsd": [100],  # 100 m stated in abstract/description :contentReference[oaicite:4]{index=4}
        "variables": ["aboveground_biomass"],
        "data_files": ["global_agb_100m_combined_mosaic_2020_cog.tif"],
    },

    # ------------------------------------------------------------------
    # Assets (roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/SAATCHI_BIOMASS_v{v}.zarr",
            title=f"Saatchi global AGB 100 m (2020) v{v} – Zarr",
            roles=["data"],
            description=(
                "Zarr packaging of the global aboveground biomass mosaic for reference year 2020 "
                "originally distributed as a Cloud-Optimized GeoTIFF on Zenodo (10.5281/zenodo.15858551)."
            ),
        )
    },

    "version_notes": {
        "2.0": "Zenodo record published as Version v2 (Oct 7, 2025).",
    },
}

