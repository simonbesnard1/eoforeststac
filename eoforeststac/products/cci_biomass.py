import datetime
from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.assets import create_zarr_asset

CCI_BIOMASS_CFG = {
    # ------------------------------------------------------------------
    # Identity / narrative (atlas-friendly)
    # ------------------------------------------------------------------
    "id": "CCI_BIOMASS",
    "title": "ESA CCI Biomass – Global annual aboveground biomass (AGB)",
    "description": (
        "Annual global aboveground biomass (AGB) maps produced within the ESA Climate Change Initiative "
        "(CCI) Biomass project. The product supports carbon-cycle analysis, model evaluation, and "
        "large-scale assessments of biomass distribution and change.\n\n"
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
    "start_datetime": datetime.datetime(2007, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2023, 12, 31, tzinfo=datetime.timezone.utc),

    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{BASE_S3_URL}/CCI_BIOMASS/collection.json",
    "base_path": f"{BASE_S3_URL}/CCI_BIOMASS",

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "Open-access",

    "providers": [
        {
            "name": "ESA Climate Change Initiative (CCI)",
            "roles": ["producer"],
            "url": "https://climate.esa.int",
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
        "biomass",
        "carbon",
        "forest",
        "global",
        "annual",
        "ESA CCI",
        "remote sensing",
        "zarr",
        "stac",
    ],

    # Optional but often useful for “atlas” grouping (your own convention)
    "themes": ["carbon", "biomass", "forest structure"],

    # ------------------------------------------------------------------
    # Links (what makes STAC Browser feel curated)
    # ------------------------------------------------------------------
    "links": [
        # # Branding / visuals (host these in your GH pages or public bucket)
        # {
        #     "rel": "thumbnail",
        #     "href": "https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/thumbnails/cci_biomass.png",
        #     "type": "image/png",
        #     "title": "AGB thumbnail",
        # },

        # Official documentation
        {
            "rel": "about",
            "href": "https://climate.esa.int/en/projects/biomass/",
            "type": "text/html",
            "title": "ESA CCI Biomass project page",
        },

        # If you have a canonical terms/licensing page, link it explicitly
        {
            "rel": "license",
            "href": "https://artefacts.ceda.ac.uk/licences/specific_licences/esacci_biomass_terms_and_conditions.pdf",
            "type": "text/html",
            "title": "ESA CCI terms of use / licensing",
        },

        {
             "rel": "cite-as",
             "href": "https://doi.org/10.5285/AF60720C1E404A9E9D2C145D2B2EAD4E",
             "type": "text/html",
             "title": "Dataset DOI",
         },
        
        {
            "rel": "about",
            "href": "https://github.com/simonbesnard1/eoforeststac",
            "type": "text/html",
            "title": "STAC packaging project (EOForestSTAC)",
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
        "https://stac-extensions.github.io/item-assets/v1.0.0/schema.json", # bands, nodata, etc.
    ],

    # ------------------------------------------------------------------
    # Summaries (client-friendly structured metadata)
    # Keep conservative: only include what you’re sure of.
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["annual"],
        "variables": ["aboveground_biomass", "aboveground_biomass_std"],
        "units": ["Mg ha-1"],

        "eo:gsd": [100.0],
        "proj:epsg": [4326],

        "product_family": ["ESA CCI Biomass"],
        "data_format": ["zarr"],
    },
    
    "item_assets": {
      "zarr": {
        "title": "Zarr dataset",
        "description": "Annual aboveground biomass (AGB) maps (Mg ha-1).",
        "roles": ["data"],
        "type": "application/vnd.zarr"
      },
      "thumbnail": {
        "title": "Thumbnail",
        "roles": ["thumbnail"],
        "type": "image/png"
      }
    },
        
    # ------------------------------------------------------------------
    # Asset template (add roles + description as you requested)
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/CCI_BIOMASS_v{v}.zarr",
            title=f"ESA CCI Biomass AGB v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store containing annual aboveground biomass (AGB) layers "
                "for the ESA CCI Biomass product."
            ),
        ),
    },
}

