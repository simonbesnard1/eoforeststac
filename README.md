# eoforeststac: a forest EO data catalog.

**eoforeststac** is a lightweight Python package for discovering and accessing
forest Earth Observation (EO) datasets through **SpatioTemporal Asset Catalogs (STAC)**.

It provides a STAC-first interface to cloud-hosted, analysis-ready datasets
(Zarr and GeoTIFF) stored on S3-compatible object storage.

---

## 🌲 Features

- 📚 Discover EO products and available versions from a STAC catalog
- 📦 Load Zarr datasets directly from S3
- 🔍 Programmatic catalog exploration (collections, versions)
- ⚡ Lazy, on-demand loading with `xarray`
- 🌐 Supports public (anonymous) and authenticated S3 access

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
For a complete and exhaustive overview of all available products, see  
➡️ **[CATALOG.md](CATALOG.md)**


## 📥 Read Data

### Load a Zarr-backed dataset

```python
from eoforeststac.providers.zarr import ZarrProvider

provider = ZarrProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

ds = provider.open_dataset(
    collection_id="CCI_BIOMASS",
    version="6.0",
)

print(ds)


```

## 🔐 Data Access Modes

By default, the data catalog uses anonymous public access to the S3 catalog hosted at:

```
s3://dog.atlaseo-glm.eo-gridded-data/
```
---

## About the authors

Simon Besnard, a senior researcher in the Global Land Monitoring Group at GFZ Helmholtz Centre Potsdam, studies terrestrial ecosystems' dynamics and their feedback on environmental conditions. He specializes in developing methods to analyze large EO and climate datasets to understand ecosystem functioning in a changing climate. His current research focuses on forest structure changes over the past decade and their links to the carbon cycle. 


## Contact

For any questions or inquiries, please contact:
- Simon Besnard (simon.besnard@gfz.de)

## 🤝 Acknowledgements

We acknowledge funding support by the European Union through the [FORWARDS](https://forwards-project.eu/) project. 
---

## 📄 License

This project is licensed under the EUROPEAN UNION PUBLIC LICENCE v.1.2 License - see the LICENSE file for details.
---

## 🌍 Citation

If you use this package in your research, please cite the github repository. 
