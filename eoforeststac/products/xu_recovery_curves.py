import datetime
from eoforeststac.core.config import S3_HTTP_BASE
from eoforeststac.core.assets import create_zarr_asset

# Disturbance types and their human descriptions
DISTURBANCE_TYPES = {
    "dryfire": "dry-forest fire",
    "humfire": "humid-forest fire",
    "otherdeg": "other (non-fire) degradation",
    "regrowth": "deforestation / regrowth",
}

# Chapman-Richards parameters present in each disturbance-type layer
CR_PARAMS = {
    "agbmax": {
        "units": "Mg ha-1",
        "long_name": "Chapman-Richards asymptote (AGB_max)",
        "description": "Asymptotic maximum aboveground biomass",
    },
    "b": {
        "units": "1",
        "long_name": "Chapman-Richards growth-rate parameter (b)",
    },
    "c": {
        "units": "1",
        "long_name": "Chapman-Richards shape parameter (c)",
    },
    "d": {
        "units": "Mg ha-1",
        "long_name": "Chapman-Richards offset parameter (d)",
        "description": (
            "Starting biomass; non-zero for degradation types because fire and "
            "non-fire degradation do not always remove all biomass."
        ),
    },
}

XU_RECOVERY_CURVES_CFG = {
    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    "id": "XU_RECOVERY_CURVES",
    "title": (
        "Xu et al. – Tropical forest biomass recovery curves "
        "(Chapman-Richards parameters, 1 deg)"
    ),
    "description": (
        "Global, 1-degree-resolution Chapman-Richards curve parameters describing "
        "aboveground biomass (AGB) recovery in tropical forests following four types "
        "of disturbance: humid-forest fire, dry-forest fire, other (non-fire) "
        "degradation, and deforestation/regrowth.\n\n"
        "The recovery model follows the Chapman-Richards function:\n"
        "    AGB(age) = AGB_max x (1 - exp(-b x age))^c + d\n"
        "where AGB is in Mg ha-1 and age is in years.\n\n"
        "Parameters were fitted using CCI-Biomass v4 (2020), TMF v2023, and GABAM "
        "fire data. Grid cells with insufficient observations were gap-filled by "
        "spatial nearest-neighbour interpolation across the tropics.\n\n"
        "Curves for degradation types (humfire, dryfire, otherdeg) may start with a "
        "non-zero offset (d > 0) because these disturbances do not always remove all "
        "biomass. Regrowth curves start at zero.\n\n"
        "This collection provides an analysis-ready Zarr packaging for cloud-native "
        "access. Please cite the original Zenodo dataset and the associated publication "
        "when using these curves (see links)."
    ),
    # ------------------------------------------------------------------
    # Spatial / temporal extent
    # ------------------------------------------------------------------
    "bbox": [-180.0, -90.0, 180.0, 90.0],
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [-180.0, -90.0],
                [-180.0, 90.0],
                [180.0, 90.0],
                [180.0, -90.0],
                [-180.0, -90.0],
            ]
        ],
    },
    # Static model output — fitted on 2020 CCI-Biomass epoch
    "start_datetime": datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    "end_datetime": datetime.datetime(2026, 12, 31, tzinfo=datetime.timezone.utc),
    # ------------------------------------------------------------------
    # HREF layout
    # ------------------------------------------------------------------
    "collection_href": f"{S3_HTTP_BASE}/XU_RECOVERY_CURVES/collection.json",
    "base_path": f"{S3_HTTP_BASE}/XU_RECOVERY_CURVES",
    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    "license": "CC-BY-4.0",
    "providers": [
        {
            "name": "LSCE / CEA-CNRS-UVSQ (Xu et al.)",
            "roles": ["producer"],
            "url": "https://www.lsce.ipsl.fr",
        },
        {
            "name": "Zenodo",
            "roles": ["host"],
            "url": "https://zenodo.org/records/18168285",
        },
        {
            "name": "GFZ Helmholtz Centre Potsdam",
            "roles": ["processor", "host"],
            "url": "https://www.gfz.de",
        },
    ],
    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------
    "keywords": [
        "biomass recovery",
        "forest regrowth",
        "Chapman-Richards",
        "growth curves",
        "aboveground biomass",
        "tropical forests",
        "forest disturbance",
        "fire",
        "deforestation",
        "degradation",
        "carbon accumulation",
        "zarr",
        "stac",
    ],
    "themes": ["carbon", "forest dynamics", "disturbance", "model parameters"],
    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------
    "links": [
        {
            "rel": "cite-as",
            "href": "https://doi.org/10.5281/zenodo.18168285",
            "type": "text/html",
            "title": "Dataset DOI (Zenodo 18168285): Xu et al. biomass recovery curves",
        },
        {
            "rel": "related",
            "href": "https://doi.org/10.5281/zenodo.18168285",
            "type": "text/html",
            "title": (
                "Xu et al. – Small persistent humid forest clearings drive "
                "tropical forest biomass losses"
            ),
        },
        {
            "rel": "documentation",
            "href": "https://zenodo.org/records/18168285",
            "type": "text/html",
            "title": "Zenodo record with README and code",
        },
    ],
    # ------------------------------------------------------------------
    # Extensions
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
    # Summaries
    # ------------------------------------------------------------------
    "summaries": {
        "temporal_resolution": ["static"],
        "proj:epsg": [4326],
        "eo:gsd": [111320.0],  # ~1 degree at equator in metres
        "disturbance_types": list(DISTURBANCE_TYPES.keys()),
        "variables": list(CR_PARAMS.keys()),
        "units_by_variable": {p: meta["units"] for p, meta in CR_PARAMS.items()},
        "data_format": ["zarr"],
        "notes": [
            "AGB(age) = AGB_max x (1 - exp(-b x age))^c + d  [Mg ha-1]",
            "Parameters fitted on CCI-Biomass v4 2020, TMF v2023, GABAM fire.",
            "Cells without sufficient observations gap-filled by nearest-neighbour interpolation.",
            "Please cite Xu et al. (Zenodo 18168285) and the associated publication.",
        ],
    },
    # ------------------------------------------------------------------
    # Raster band metadata (for STAC raster extension)
    # ------------------------------------------------------------------
    "raster_bands": {p: {"data_type": "float32", "nodata": -9999.0} for p in CR_PARAMS},
    # ------------------------------------------------------------------
    # Item assets template
    # ------------------------------------------------------------------
    "item_assets": {
        "zarr": {
            "title": "Zarr dataset",
            "description": (
                "Cloud-optimized Zarr store containing Chapman-Richards parameters "
                "(agbmax, b, c, d) for four disturbance types "
                "(dryfire, humfire, otherdeg, regrowth)."
            ),
            "roles": ["data"],
            "type": "application/vnd.zarr",
        }
    },
    # ------------------------------------------------------------------
    # Asset factory
    # ------------------------------------------------------------------
    "asset_template": {
        "key": "zarr",
        "factory": lambda cfg, v: create_zarr_asset(
            href=f"{cfg['base_path']}/XU_RECOVERY_CURVES_v{v}.zarr",
            title=f"Xu et al. recovery curve parameters v{v} (Zarr)",
            roles=["data"],
            description=(
                "Cloud-optimized Zarr store of Chapman-Richards parameters for four "
                "tropical-forest disturbance types (Xu et al., Zenodo 18168285). "
                "Original distribution: GeoTIFF at 1-degree resolution, EPSG:4326."
            ),
        ),
    },
    # ------------------------------------------------------------------
    # Version notes
    # ------------------------------------------------------------------
    "version_notes": {
        "1.0": "Initial ingestion from Zenodo record 18168285 (published 2026-01-06).",
    },
}
