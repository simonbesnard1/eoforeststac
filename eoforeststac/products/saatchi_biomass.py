import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

SAATCHI_BIOMASS_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "SAATCHI_BIOMASS",
    "title": "Saatchi & Yu - Global aboveground biomass (AGB) 100 m (2020)",
    "description": (
        "Global live woody vegetation / aboveground biomass mapping product at 100 m spatial resolution, "
        "distributed as a global aboveground biomass mosaic for reference year 2020. "
        "This STAC collection packages the Zenodo deliverable 'Mapping Global Live Woody Vegetation "
        "Biomass at Optimum Spatial Resolutions' and associated supplementary documentation.\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native access."
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
        ]],
    },
    "start_datetime": datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2020, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/SAATCHI_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/SAATCHI_BIOMASS",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "CC-BY-4.0",
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

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------
    "keywords": [
        "aboveground biomass",
        "AGB",
        "live woody biomass",
        "carbon density",
        "forest biomass",
        "global",
        "100 m",
        "remote sensing",
        "zarr",
        "stac",
    ],
    "themes": ["biomass", "carbon", "forest structure"],

    # ------------------------------------------------------------------
    # Links (curated STAC Browser experience)
    # ------------------------------------------------------------------
    "links": [
       
        # Canonical links
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
        {
            "rel": "related",
            "href": "https://doi.org/10.5281/zenodo.7583611",
            "type": "text/html",
            "title": "Related work (compiled article / deliverable link)",
        },
        
    ],

    # ------------------------------------------------------------------
    # Extensions (signal what fields might exist in items/assets)
    # ------------------------------------------------------------------
    "stac_extensions": [
        "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
        "https://stac-extensions.github.io/proj/v1.1.0/schema.json",
        "https://stac-extensions.github.io/file/v2.1.0/schema.json",
        "https://stac-extensions.github.io/raster/v1.1.0/schema.json",
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json",
        "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
    ],

    # ------------------------------------------------------------------
    # Summaries (client-friendly structured metadata)
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["static"],
        "reference_year": [2020],

        "variables": ["aboveground_biomass"],
        "units_by_variable": {
                            "aboveground_biomass": "Mg  ha-1"},

        "eo:gsd": [100.0],
        "proj:epsg": [4326],

        "product_family": ["Saatchi & Yu global AGB"],
        "data_format": ["zarr"],
    },

    # ------------------------------------------------------------------
    # Item assets template (for Item Assets extension)
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": "Cloud-optimized Zarr store of the Saatchi & Yu global aboveground biomass mosaic (2020).",
            "roles": ["data"],
            "type": "application/vnd.zarr",
        },
        "thumbnail": {
            "title": "Preview",
            "roles": ["thumbnail"],
            "type": "image/png",
        },
    },

    # ------------------------------------------------------------------
    # Asset template (roles + description)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/SAATCHI_BIOMASS_v{v}.zarr",
            title=f"Saatchi & Yu global AGB 100 m (2020) v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store packaging of the global aboveground biomass mosaic for reference year 2020, "
                "originally distributed as a Cloud-Optimized GeoTIFF on Zenodo (10.5281/zenodo.15858551)."
            ),
        ),
    },

    # ------------------------------------------------------------------
    # Version notes
    # ------------------------------------------------------------------
    "version_notes": {
        "2.0": "Zenodo record published as Version v2 (Oct 7, 2025).",
    },
}
