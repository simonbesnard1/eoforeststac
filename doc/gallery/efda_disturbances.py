"""
Forest disturbances: loading and visualising EFDA
==================================================

This example shows how to load the European Forest Disturbance Atlas (EFDA)
and explore annual disturbance events across European forests.
"""

# %%
# Load the EFDA dataset
# ----------------------
#
# EFDA covers annual forest disturbances (fire, wind, bark beetle, etc.)
# as a gridded binary product (1 = disturbed in forest, 0 = undisturbed forest,
# NaN = non-forest).

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

ds = provider.open_dataset(collection_id="EFDA", version="2.0")
print(ds)

# %%
# Subset to Germany
# ------------------

roi = gpd.GeoDataFrame(
    geometry=gpd.GeoSeries.from_wkt(["POLYGON((6 47, 15 47, 15 55, 6 55, 6 47))"]),
    crs="EPSG:4326",
)
geometry = roi.geometry.union_all()

ds_de = subset(
    ds,
    geometry=geometry,
    time=("2000-01-01", "2022-12-31"),
).compute()

# %%
# Annual disturbance area
# ------------------------
#
# Sum disturbed pixels (value == 1) per year to get a time series of
# disturbed area. Each pixel covers ~1 ha at native resolution.

disturbance = ds_de["disturbance"]

annual_area = (disturbance == 1).sum(dim=["latitude", "longitude"]).compute()

fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(
    annual_area["time"].dt.year.values,
    annual_area.values,
    color="firebrick",
    alpha=0.8,
    width=0.8,
)
ax.set_xlabel("Year")
ax.set_ylabel("Disturbed pixels")
ax.set_title("Annual forest disturbance area — Germany (EFDA v2.0)")
plt.tight_layout()
plt.savefig("efda_germany_timeseries.png", dpi=150, bbox_inches="tight")
plt.show()

# %%
# Map the worst disturbance year
# --------------------------------

worst_year_idx = int(annual_area.argmax())
worst_year = int(annual_area["time"].dt.year.values[worst_year_idx])
print(f"Worst disturbance year: {worst_year}")

worst_map = disturbance.sel(time=str(worst_year)).values

fig, ax = plt.subplots(figsize=(8, 7))
ax.imshow(
    worst_map,
    origin="upper",
    extent=[
        float(ds_de.longitude.min()),
        float(ds_de.longitude.max()),
        float(ds_de.latitude.min()),
        float(ds_de.latitude.max()),
    ],
    cmap="Reds",
    vmin=0,
    vmax=1,
    interpolation="nearest",
)
ax.set_title(f"EFDA disturbance map — Germany {worst_year}", fontsize=11)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
plt.tight_layout()
plt.savefig(f"efda_germany_{worst_year}.png", dpi=150, bbox_inches="tight")
plt.show()
