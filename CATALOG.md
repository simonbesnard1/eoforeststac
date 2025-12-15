
---

# 2️⃣ `CATALOG.md` — Exhaustive Product Table

This file is **generated**, not hand-written.

```markdown
# EOForestSTAC – Product Catalog

This document provides an **exhaustive overview of all EOForestSTAC collections**
and their available versions.

The table below is generated directly from the STAC catalog to ensure consistency
with the data that can actually be loaded.

---

## 📊 Available Products

| Collection ID | Title | Description | Versions | Backend | Spatial Coverage |
|--------------|-------|-------------|----------|---------|------------------|
| GAMI | Global Age Mapping Integration | Global forest age and uncertainty metrics | 2.1, 3.0, 3.1 | Zarr | Global |
| CCI_BIOMASS | ESA CCI Biomass | Global above-ground biomass maps | 6.0 | Zarr | Global |
| EFDA | European Forest Disturbance Atlas | Forest disturbance agents and masks | 2.1.1 | GeoTIFF | Europe |
| ROBINSON_CR | Chapman–Richards Carbon Parameters | Pixel-level CR growth parameters and derived metrics | 1.0 | Zarr | Global |
| JRC_GFC2020 | JRC Global Forest Cover 2020 | Global forest cover classification | 3 | GeoTIFF | Global |

---

## 🧭 Notes

- **Versions** correspond to loadable STAC Items
- All datasets are accessible via the `DiscoveryProvider` and appropriate data providers
- Spatial coverage and backend type are informational; STAC assets are authoritative

---

## 🔁 Regenerating this Table

This table is generated programmatically:

```python
from eoforeststac.providers.discovery import DiscoveryProvider

disc = DiscoveryProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

df = disc.collections_table()

# optional enrichment before export
df["versions"] = df["versions"].apply(lambda v: ", ".join(v))

print(df.to_markdown(index=False))
