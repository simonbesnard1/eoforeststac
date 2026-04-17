<p align="center">
<a href="https://github.com/simonbesnard1/eoforeststac">
        <img src="https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/logos/eoforestact_logo.png"
         alt="eoforeststac Logo" height="200px" hspace="0px" vspace="30px">
</a>
</p>

# EOForestSTAC: A toolbox for accessing forest Earth Observation datasets through SpatioTemporal Asset Catalogs (STAC)

[![License: EUPL-1.2](https://img.shields.io/badge/License-EUPL--1.2-blue.svg)](https://opensource.org/licenses/EUPL-1.2)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![STAC Browser](https://img.shields.io/badge/STAC-Browser-green)](https://simonbesnard1.github.io/eoforeststac/)

**EOForestSTAC** is an open-source Python package that provides a streamlined interface to discover and load cloud-hosted, analysis-ready forest Earth Observation datasets. All products are stored as Zarr archives on GFZ Ceph object storage and are organised in a STAC (SpatioTemporal Asset Catalog), enabling cloud-native access without downloading data locally.

The package supports a growing catalog of global forest EO products covering biomass, carbon, disturbance, canopy height, forest age, and land use, spanning multiple versions and spatial resolutions.

## Key Features

- **Interactive STAC Browser**: Explore all datasets, versions, and spatial coverage visually at [simonbesnard1.github.io/eoforeststac](https://simonbesnard1.github.io/eoforeststac/)
- **STAC-native discovery**: Browse collections, themes, and versions programmatically
- **Direct Zarr access**: Stream datasets from Ceph/S3 without local downloads
- **Multi-resolution support**: Select spatial resolution for products available at multiple scales
- **Spatial subsetting**: Extract regions of interest with automatic CRS handling
- **Temporal filtering**: Query data by time range
- **Dataset alignment**: Merge multi-source datasets onto a common grid
- **Lazy loading**: Efficient on-demand data access via xarray and Dask

## Why EOForestSTAC?

EOForestSTAC removes the friction of working with large-scale forest EO data by combining a curated STAC metadata catalog with cloud-native Zarr storage. Instead of downloading multi-gigabyte files and managing local copies, users can stream exactly the spatial and temporal subset they need directly into an xarray Dataset. The catalog structure makes it straightforward to discover what is available, compare versions, and combine multiple products on a common grid for integrated analyses.

## Installation

Install directly from GitHub:

```bash
python -m pip install "git+https://github.com/simonbesnard1/eoforeststac.git"
```

Requires Python >= 3.10.

See the [examples/](https://github.com/simonbesnard1/eoforeststac/tree/main/examples) folder for notebooks demonstrating discovery, loading, subsetting, and multi-product alignment.

## Documentation

### Explore the Catalog

The interactive **STAC Browser** is the recommended starting point for new users:

**https://simonbesnard1.github.io/eoforeststac/**

It allows you to explore all collections and versions, inspect spatial footprints on a map, view dataset metadata and provenance, and check asset details before loading in Python.

For a static overview of all available products see [CATALOG.md](CATALOG.md).

### Discover Available Data

```python
from eoforeststac.providers.discovery import DiscoveryProvider

disc = DiscoveryProvider(
    catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

# List all themes
disc.list_themes()
# {'biomass-carbon': 'Biomass & Carbon', 'disturbance-change': 'Disturbance & Change', ...}

# List collections within a theme
disc.list_collections(theme="disturbance-change")

# Overview table for a theme
df = disc.collections_table(theme="biomass-carbon")
```

### Load and Subset Data

```python
import geopandas as gpd
from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset

provider = ZarrProvider(
    catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

# Open a dataset
ds = provider.open_dataset(collection_id="CCI_BIOMASS", version="6.0")

# Open a multi-resolution dataset at a specific resolution
ds_age = provider.open_dataset(
    collection_id="GAMI_AGECLASS",
    version="3.0",
    resolution="0.25deg",
)

# Subset spatially and temporally (geometries in EPSG:4326)
roi = gpd.read_file("DE-Hai.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

ds_subset = subset(
    ds,
    geometry=geometry,
    time=("2007-01-01", "2020-12-31"),
)
```

### Align Multiple Datasets

When combining multiple EO products, `DatasetAligner` reprojects and resamples all datasets onto a common grid:

```python
from eoforeststac.providers.align import DatasetAligner

ds_biomass = provider.open_dataset("CCI_BIOMASS", "6.0")
ds_biomass = subset(ds_biomass, geometry=geometry, time=("2020-01-01", "2020-12-31"))

ds_saatchi = provider.open_dataset("SAATCHI_BIOMASS", "2.0")
ds_saatchi = subset(ds_saatchi, geometry=geometry, time=("2020-01-01", "2020-12-31"))

aligner = DatasetAligner(
    target="CCI_BIOMASS",
    resampling={
        "CCI_BIOMASS": {"default": "average"},
        "SAATCHI_BIOMASS": {"default": "average"},
    },
)

aligned = aligner.align({
    "CCI_BIOMASS": ds_biomass.sel(time="2020-01-01"),
    "SAATCHI_BIOMASS": ds_saatchi.sel(time="2020-01-01"),
})
```

The aligned dataset is guaranteed to share identical CRS, resolution, and grid origin across all products.

## Contributing

Contributions are welcome. Please open an issue or pull request on [GitHub](https://github.com/simonbesnard1/eoforeststac).

## About the authors

Simon Besnard is a senior researcher in the Global Land Monitoring Group at GFZ Helmholtz Centre Potsdam. He studies the dynamics of terrestrial ecosystems and their feedbacks on environmental conditions, specialising in the development of methods to analyse large Earth Observation and climate datasets. His current research focuses on forest structure changes over the past decade and their links to the carbon cycle.

## Contact

For questions or support:
- **Simon Besnard** — [simon.besnard@gfz.de](mailto:simon.besnard@gfz.de)

## Acknowledgments

The development of EOForestSTAC was supported by the European Union through the [FORWARDS](https://forwards-project.eu/) project.

## License

This project is licensed under the European Union Public Licence v1.2 — see the [LICENSE](LICENSE) file for details.

## Citation

If you use EOForestSTAC in your research, please cite this repository:

```
Besnard, S. (2025). EOForestSTAC: A toolbox for accessing the EO forest data catalog.
GitHub repository: https://github.com/simonbesnard1/eoforeststac
```
