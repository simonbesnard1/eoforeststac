"""
Loading, subsetting, and aligning datasets
===========================================

This example demonstrates the core EOForestSTAC workflow: opening a dataset,
subsetting it to a region of interest, and aligning two products from different
sources onto a common grid.
"""

# %%
# Setup
# -----

import geopandas as gpd
from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset
from eoforeststac.providers.align import DatasetAligner

CATALOG_URL = (
    "https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data"
    "/collections/public/catalog.json"
)

provider = ZarrProvider(
    catalog_url=CATALOG_URL,
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

# %%
# Open a dataset (lazy — no data transferred yet)
# ------------------------------------------------
#
# :py:meth:`~eoforeststac.providers.zarr.ZarrProvider.open_dataset` returns an
# ``xarray.Dataset`` backed by Dask.  Metadata and coordinates are loaded
# immediately; data chunks are only fetched on ``.compute()``.

ds_biomass = provider.open_dataset(collection_id="CCI_BIOMASS", version="6.0")
print(ds_biomass)

# %%
# Open a multi-resolution dataset
# --------------------------------
#
# Products like GAMI_AGECLASS are available at multiple spatial resolutions.
# Pass ``resolution=`` to select the asset.

ds_age = provider.open_dataset(
    collection_id="GAMI_AGECLASS",
    version="3.0",
    resolution="0.25deg",
)
print(ds_age)
# Available resolutions: "1deg", "0.5deg", "0.25deg", "0.1deg", "0.0833deg"

# %%
# Subset spatially and temporally
# --------------------------------
#
# :py:func:`~eoforeststac.providers.subset.subset` clips the dataset to a polygon
# (EPSG:4326) and an optional time range.  Automatic CRS reprojection is applied.

roi = gpd.read_file("DE-Hai.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

ds_subset = subset(
    ds_biomass,
    geometry=geometry,
    time=("2010-01-01", "2020-12-31"),
)

# Load the subset into memory
ds_loaded = ds_subset.compute()
print(ds_loaded)

# %%
# Load only specific variables
# -----------------------------

ds_agb = provider.open_dataset("CCI_BIOMASS", "6.0", variables=["agb"])
ds_agb_subset = subset(ds_agb, geometry=geometry, time=("2020-01-01", "2020-12-31"))
agb_2020 = ds_agb_subset.sel(time="2020-01-01").compute()
print(
    "AGB 2020 stats:",
    float(agb_2020["agb"].min()),
    "–",
    float(agb_2020["agb"].max()),
    "Mg/ha",
)

# %%
# Align two products to a common grid
# -------------------------------------
#
# :py:class:`~eoforeststac.providers.align.DatasetAligner` reprojects and resamples
# all datasets to match the ``target`` dataset's CRS, resolution, and grid origin.

ds_saatchi = provider.open_dataset("SAATCHI_BIOMASS", "2.0")
ds_saatchi_sub = subset(
    ds_saatchi, geometry=geometry, time=("2020-01-01", "2020-12-31")
)

aligner = DatasetAligner(
    target="CCI_BIOMASS",
    resampling={
        "CCI_BIOMASS": {"default": "average"},
        "SAATCHI_BIOMASS": {"default": "average"},
    },
)

aligned = aligner.align(
    {
        "CCI_BIOMASS": ds_agb_subset.sel(time="2020-01-01"),
        "SAATCHI_BIOMASS": ds_saatchi_sub.sel(time="2020-01-01"),
    }
)

print(aligned)

# %%
# Compare aligned biomass products
# ----------------------------------

import numpy as np  # noqa: E402

cci = aligned["CCI_BIOMASS"]["agb"].values
saatchi = aligned["SAATCHI_BIOMASS"]["agb"].values

mask = np.isfinite(cci) & np.isfinite(saatchi)
diff = cci[mask] - saatchi[mask]
print(f"Mean difference (CCI - Saatchi): {diff.mean():.1f} Mg/ha")
print(f"RMSD: {np.sqrt((diff ** 2).mean()):.1f} Mg/ha")
