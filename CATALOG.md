
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

| collection_id   | title                                                                         | description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | versions           |   n_versions |
|:----------------|:------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------|-------------:|
| CCI_BIOMASS     | ESA CCI Biomass Global Annual Maps                                            | Aboveground biomass (AGB) product from ESA Climate Change Initiative.                                                                                                                                                                                                                                                                                                                                                                                                                                                       | 6.0                |            1 |
| SAATCHI_BIOMASS | Global Aboveground Biomass (Saatchi et al.)                                   | Global AGB estimates derived from radar and field datasets (Saatchi et al. 2020).                                                                                                                                                                                                                                                                                                                                                                                                                                           | 2.0                |            1 |
| TMF             | Tropical Moist Forest Change (TMF)                                            | Forest disturbance and regrowth dataset for the tropical moist forest biome.                                                                                                                                                                                                                                                                                                                                                                                                                                                | 3.0                |            1 |
| EFDA            | European Forest Disturbance Atlas (EFDA)                                      | Continental-scale forest disturbance data for Europe, 1985–2023.                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 2.1.1              |            1 |
| POTAPOV_HEIGHT  | Global Canopy Height (Potapov et al.)                                         | Global canopy height dataset derived from Landsat and ICESat-2.                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 1.0                |            1 |
| GAMI            | Global Age Mapping Integration (GAMI)                                         | Forest age derived from machine learning and remote sensing.                                                                                                                                                                                                                                                                                                                                                                                                                                                                | 2.0, 2.1, 3.0, 3.1 |            4 |
| JRC_GFC2020     | JRC Global Forest Cover 2020                                                  | Global Forest Cover (GFC) map produced by the Joint Research Centre (JRC). The product provides a global categorical forest cover classification for the reference year 2020, derived from Copernicus Sentinel data.                                                                                                                                                                                                                                                                                                        | 1.0, 2.0, 3.0      |            3 |
| ROBINSON_CR     | Global Chapman-Richards Curve Parameters for Secondary Forest Carbon Dynamics | Global pixel-level Chapman–Richards (CR) growth curve parameters and derived metrics describing aboveground carbon accumulation in secondary forests. The dataset provides spatially explicit estimates of CR parameters (a, b, k), their associated standard errors, and derived quantities such as maximum carbon accumulation rate, age at maximum rate, and relative carbon removal potential. The product supports analysis of forest regrowth dynamics and optimal protection strategies for young secondary forests. | 1.0                |            1 |

---

## 🧭 Notes

- **Versions** correspond to loadable STAC Items
- All datasets are accessible via the `DiscoveryProvider` and appropriate data providers
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
```