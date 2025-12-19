<p align="center">
<a href="https://github.com/simonbesnard1/eoforeststac">
        <img src="https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/logos/eoforestact_logo.png"
         alt="eoforeststac Logo" height="200px" hspace="0px" vspace="30px" align="left">
</a>
</p>

# EOForestSTAC: A toolbox for accessing the EO forest data catalog.

**EOForestSTAC** is a lightweight Python package for discovering and accessing
forest Earth Observation (EO) datasets through **SpatioTemporal Asset Catalogs (STAC)**.

It provides a STAC-first interface to cloud-hosted, analysis-ready datasets
(Zarr) stored on Ceph object storage.

---

## 🌲 Features

- 📚 Discover EO products and available versions from a STAC catalog
- 📦 Load Zarr datasets directly from Ceph
- 🔍 Programmatic catalog exploration (collections, versions)
- ⚡ Lazy, on-demand loading with `xarray`
- 🌐 Supports public (anonymous) and authenticated Ceph access

---

## 📦 Installation

```bash
pip install git+https://github.com/simonbesnard1/eoforeststac.git

```

## 🔍 Explore the Catalog

```python
from eoforeststac.providers.discovery import DiscoveryProvider

disc = DiscoveryProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

```

### List versions for a collection

```python
disc.list_collections()

```

### List available collections

```python
disc.list_versions("GAMI")

```

### Generate a product overview table

```python
df = disc.collections_table()
df

```
<table>
  <tr>
    <td style="vertical-align: middle; padding-right: 2px;">
      For a complete and exhaustive overview of all available products, see  
      ➡️ <strong><a href="CATALOG.md">CATALOG.md</a></strong>
    </td>
    <td>
      <a href="CATALOG.md">
      <img
        src="https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/images/data_catalog.png"
        alt="Data catalog"
        height="200"
      >
    </a>
    </td>
  </tr>
</table>


## 📥 Read Data

### Spatial and temporal subsetting

All datasets can be lazily subset in space and time using the built-in subsetting utilities.
Geometries are always provided in EPSG:4326 and are automatically reprojected to the dataset CRS if needed.

```python
import geopandas as gpd
from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset

```

```python
provider = ZarrProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

ds = provider.open_dataset(
    collection_id="CCI_BIOMASS",
    version="6.0",
)
```
Load a region of interest (any vector format supported by GeoPandas):

```python
roi = gpd.read_file("DE-Hai.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()
```
Subset the dataset in space and time:

```python
ds_sel = subset(
    ds,
    geometry=geometry,                 # geometry in EPSG:4326
    time=("2007-01-01", "2020-12-31"),  # optional
)
```
**Notes**

- If a dataset has **no time dimension**, the time filter is silently ignored.
- Exact geometry masking (`mask=True`) is optional; by default a fast **bounding-box subset** is applied.

### Spatial alignment across datasets

When working with multiple EO datasets, spatial alignment is explicit and reproducible.  
All datasets are reprojected, resampled, and merged onto a **common target grid** using the
`DatasetAligner`.

The aligner enforces a clear spatial contract:

- a single **reference grid** (CRS, resolution, extent, shape),
- explicit **resampling rules** per dataset and per variable,
- optional **pre-coarsening** for fast downsampling,
- strict merge semantics to avoid silent conflicts.

This avoids common pitfalls where datasets appear aligned visually but differ subtly in
resolution, grid origin, or reprojection.

---

#### Example: aligning biomass and disturbance data

```python
import geopandas as gpd

from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset
from eoforeststac.providers.align import DatasetAligner

Open the data catalog and define a region of interest
(geometries are always provided in EPSG:4326):

provider = ZarrProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

roi = gpd.read_file("DE-Hai.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

Load and subset the reference dataset
(used to define the target grid):

ds = provider.open_dataset(
    collection_id="CCI_BIOMASS",
    version="6.0",
)

ds_biomass = subset(
    ds,
    geometry=geometry,
    time=("2007-01-01", "2020-12-31"),
)

Load and subset a second dataset on a different native grid:

ds = provider.open_dataset(
    collection_id="SAATCHI_BIOMASS",
    version="2.0",
)

ds_efda = subset(
    ds,
    geometry=geometry,
    time=("2020-01-01", "2020-12-31"),
)

Define the aligner and specify resampling behaviour:

aligner = DatasetAligner(
    target="CCI_BIOMASS",
    resampling={
        "CCI_BIOMASS": {"default": "average"},
        "EFDA": {"default": "average"},
    },
)

aligned = aligner.align({
    "CCI_BIOMASS": ds_biomass.sel(time="2020-01-01"),
    "EFDA": ds_efda,
})
```
The resulting dataset is guaranteed to:

- share a common CRS, resolution, extent, and grid origin,

- have consistent spatial dimension names,

- preserve variable-specific resampling choices,

**Notes**

- The target grid is derived from the reference dataset (target="CCI_BIOMASS"), unless explicitly overridden.

- All spatial variables are required to carry a CRS; missing CRS metadata is enforced internally.

- Merging is performed with strict conflict checks to avoid silent overwrites.

- Temporal alignment is handled explicitly by the user (e.g. via sel(time=...)).

## 🔐 Data Access Modes

By default, the data catalog uses anonymous public access to the S3 catalog hosted at:

```
s3://dog.atlaseo-glm.eo-gridded-data/
```
---

## About the author

Simon Besnard, a senior researcher in the Global Land Monitoring Group at GFZ Helmholtz Centre Potsdam, studies terrestrial ecosystems' dynamics and their feedback on environmental conditions. He specializes in developing methods to analyze large EO and climate datasets to understand ecosystem functioning in a changing climate. His current research focuses on forest structure changes over the past decade and their links to the carbon cycle. 


## Contact

For any questions or inquiries, please contact:
- Simon Besnard (simon.besnard@gfz.de)

## 🤝 Acknowledgements

We acknowledge funding support by the European Union through the [FORWARDS](https://forwards-project.eu/) project. 


## 📄 License

This project is licensed under the EUROPEAN UNION PUBLIC LICENCE v.1.2 License - see the LICENSE file for details.

## 🌍 Citation

If you use this package in your research, please cite the github repository. 
