"""
Discovering the EOForestSTAC catalog
=====================================

This example shows how to explore the STAC catalog using
:py:class:`eoforeststac.providers.discovery.DiscoveryProvider` — listing themes,
collections, and available versions without loading any data.
"""

# %%
# Connect to the catalog
# -----------------------
#
# :py:class:`~eoforeststac.providers.discovery.DiscoveryProvider` reads the STAC
# JSON hierarchy.  Use ``anon=True`` for public, read-only access.

from eoforeststac.providers.discovery import DiscoveryProvider

CATALOG_URL = (
    "https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data"
    "/collections/public/catalog.json"
)

disc = DiscoveryProvider(
    catalog_url=CATALOG_URL,
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

# %%
# List themes
# -----------
#
# The catalog is organised into thematic groups.

themes = disc.list_themes()
for theme_id, title in themes.items():
    print(f"  {theme_id:30s}  {title}")

# %%
# List collections within a theme
# --------------------------------

collections = disc.list_collections(theme="biomass-carbon")
for col_id, title in collections.items():
    print(f"  {col_id:25s}  {title}")

# %%
# Discovery table
# ---------------
#
# ``collections_table()`` returns a ``pandas.DataFrame`` with one row per
# collection, including available versions.

df = disc.collections_table(theme="biomass-carbon")
print(df[["collection_id", "title", "versions", "n_versions"]].to_string(index=False))

# %%
# List versions for a specific collection
# ----------------------------------------

versions = disc.list_versions("CCI_BIOMASS")
print("CCI_BIOMASS versions:", versions)

versions_age = disc.list_versions("GAMI_AGECLASS")
print("GAMI_AGECLASS versions:", versions_age)

# %%
# Inspect a collection directly via pystac
# -----------------------------------------
#
# Use ``get_collection()`` for fine-grained access to STAC metadata.

col = disc.get_collection("CCI_BIOMASS")
print("Title:", col.title)
print("Spatial extent:", col.extent.spatial.bboxes)
print("Temporal extent:", col.extent.temporal.intervals)

item = col.get_item("CCI_BIOMASS_v6.0")
print("Assets:", list(item.assets.keys()))
print("Zarr href:", item.assets["zarr"].href)
