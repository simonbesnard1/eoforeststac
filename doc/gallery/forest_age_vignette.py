"""
Forest age-class fractions: a global vignette
==============================================

End-to-end showcase of the EOForestSTAC GAMI_AGECLASS product.  The notebook
covers:

* loading the GAMI age-class fraction dataset at 0.25° resolution
* subsetting to a region of interest
* visualising the age-class distribution and ensemble spread
"""

# %%
# 0 · Setup
# ----------

import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd

from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset

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
# 1 · Load GAMI Age-Class Fractions at 0.25° resolution
# -------------------------------------------------------
#
# The dataset has dimensions (members=20, age_class=12, latitude, longitude, time=2).
# ``members`` holds 20 ensemble realisations; ``age_class`` holds 12 age bins.

ds = provider.open_dataset(
    collection_id="GAMI_AGECLASS",
    version="3.0",
    resolution="0.25deg",
)
print(ds)
print("\nAge class coordinate:", ds["age_class"].values)

# %%
# 2 · Subset to Central Europe
# -----------------------------

roi = gpd.GeoDataFrame(
    geometry=gpd.GeoSeries.from_wkt(["POLYGON((5 45, 25 45, 25 60, 5 60, 5 45))"]),
    crs="EPSG:4326",
)
geometry = roi.geometry.union_all()

ds_sub = subset(ds, geometry=geometry).compute()

# %%
# 3 · Ensemble mean for year 2020
# --------------------------------
#
# Average over the 20 ensemble members to get the expected age-class distribution.

ds_2020 = ds_sub.sel(time="2020-01-01")
mean_2020 = ds_2020["forest_age"].mean(dim="members")  # (age_class, lat, lon)

# Dominant age class (argmax over age_class dimension)
dominant_age = mean_2020.argmax(dim="age_class")

# %%
# 4 · Visualise dominant age class
# ----------------------------------

age_labels = ds["age_class"].values.tolist()

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Dominant age class map
im = axes[0].imshow(
    dominant_age.values,
    origin="upper",
    extent=[
        float(ds_sub.longitude.min()),
        float(ds_sub.longitude.max()),
        float(ds_sub.latitude.min()),
        float(ds_sub.latitude.max()),
    ],
    cmap="tab20",
    vmin=0,
    vmax=len(age_labels) - 1,
    interpolation="nearest",
)
cb = plt.colorbar(im, ax=axes[0], ticks=range(len(age_labels)))
cb.set_ticklabels(age_labels)
cb.set_label("Dominant age class")
axes[0].set_title(
    "GAMI Age-Class Fractions — Dominant class (2020, 0.25°)", fontsize=10
)
axes[0].set_xlabel("Longitude")
axes[0].set_ylabel("Latitude")

# Regional mean age-class histogram
region_mean = mean_2020.mean(dim=["latitude", "longitude"]).values
axes[1].bar(range(len(age_labels)), region_mean, color="steelblue", alpha=0.8)
axes[1].set_xticks(range(len(age_labels)))
axes[1].set_xticklabels(age_labels, rotation=45, ha="right", fontsize=8)
axes[1].set_ylabel("Mean fraction")
axes[1].set_xlabel("Age class")
axes[1].set_title(
    "Regional mean age-class distribution (Central Europe, 2020)", fontsize=10
)

plt.tight_layout()
plt.savefig("gami_ageclass_vignette.png", dpi=150, bbox_inches="tight")
plt.show()

# %%
# 5 · Ensemble uncertainty
# -------------------------
#
# The inter-member spread quantifies uncertainty in the age-class estimates.

iqr_2020 = ds_2020["forest_age"].quantile(0.75, dim="members") - ds_2020[
    "forest_age"
].quantile(
    0.25, dim="members"
)  # (age_class, lat, lon)

# Mean IQR across all age classes and pixels (scalar)
mean_iqr = float(iqr_2020.mean())
print(f"Mean ensemble IQR across all age classes and pixels: {mean_iqr:.4f}")
