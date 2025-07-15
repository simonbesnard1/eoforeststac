
# eoforeststac

**eoforeststac** is a lightweight Python package designed to interact with SpatioTemporal Asset Catalogs (STAC) for forest Earth Observation (EO) datasets. It provides streamlined access to cloud-hosted, analysis-ready data such as the Global Age Mapping Integration (GAMI) and the European Forest Disturbance Atlas (EFDA), stored in Zarr and GeoTIFF formats on S3.

---

## 🌲 Features

- 📦 Load forest EO datasets directly from S3-hosted STAC catalogs
- 🔍 Query and explore collections like GAMI (Zarr) and EFDA (GeoTIFF)
- ⚡ Efficient, on-demand loading with `xarray` and `rioxarray`
- 🪶 Lightweight, modular design
- 🌐 Supports both public (anonymous) and authenticated S3 access

---

## 📦 Installation
To install the latest version directly from the GitHub repository:

```bash
pip install git+https://github.com/simonbesnard1/eoforeststac.git
```

---

## 🚀 Quickstart

### Initialize the Reader

```python
from eoforeststac.providers.gami_provider import GAMIProvider

provider = GAMIProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json"
)

ds = provider.load_zarr(version="2.1")
print(ds)
```

### Load EFDA GeoTIFFs

```python
from eoforeststac.providers.efda_provider import EFDAProvider

provider = EFDAProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json"
)

data = provider.load_data(year=2019, version="2.1.1")
data["disturbance"].rio.plot()
```

---

## 📚 Collections

| Collection | Format  | Coverage | Layers / Variables                        | License     |
|------------|---------|----------|-------------------------------------------|-------------|
| GAMI       | Zarr    | Global   | Forest age, uncertainty metrics           | CC-BY-4.0   |
| EFDA       | GeoTIFF | Europe   | Disturbance masks, disturbance agents     | CC-BY-4.0   |

---

## 🧱 Project Structure

```
eoforeststac/
│
├── core/
│   ├── catalog.py
    ├── config.py
│   ├── assets.py
│   └── io.py
│
├── providers/
│   ├── base_provider.py
│   ├── gami_provider.py
│   └── efda_provider.py
│
├── catalog_builders/
│   ├── gami.py
│   └── efda.py
│
└── utils/
```

---

## 🔐 Access Modes

By default, the package uses anonymous public access to the S3 catalog hosted at:

```
s3://dog.atlaseo-glm.eo-gridded-data/
```

For private/authenticated access, update the `BaseProvider` or use AWS credentials and `fsspec` profiles.

---

## 📄 License

This project is licensed under the **MIT License**.

---

## 🤝 Acknowledgements

- Hosted and maintained by **GFZ Potsdam**
- STAC format powered by [PySTAC](https://pystac.readthedocs.io/)
- Cloud storage via [S3 @ GFZ](https://s3.gfz-potsdam.de)

---

## 🌍 Citation

If you use this package in your research, please cite the corresponding dataset publications or project pages for **GAMI** and **EFDA**.
