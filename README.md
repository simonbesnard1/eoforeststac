<p align="center">
<a href="https://github.com/simonbesnard1/eoforeststac">
        <img src="https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/logos/eoforestact_logo.png"
         alt="eoforeststac Logo" height="200px" hspace="0px" vspace="30px">
</a>
</p>

# EOForestSTAC: A toolbox for accessing forest Earth Observation datasets through SpatioTemporal Asset Catalogs (STAC)

[![License: EUPL-1.2](https://img.shields.io/badge/License-EUPL--1.2-blue.svg)](https://opensource.org/licenses/EUPL-1.2)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docs](https://readthedocs.org/projects/eoforeststac/badge/?version=latest)](https://eoforeststac.readthedocs.io/en/latest/)
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

## Explore the Catalog Interactively

The recommended starting point for new users is the interactive **STAC Browser**:

### 👉 [https://simonbesnard1.github.io/eoforeststac/](https://simonbesnard1.github.io/eoforeststac/)

The browser lets you browse all collections and versions by theme, inspect spatial footprints on a map, view dataset metadata and provenance, and copy asset URLs directly for use in Python.

## Installation

Install directly from GitHub:

```bash
python -m pip install "git+https://github.com/simonbesnard1/eoforeststac.git"
```

Requires Python >= 3.10.

See the [examples/](https://github.com/simonbesnard1/eoforeststac/tree/main/examples) folder for notebooks demonstrating discovery, loading, subsetting, and multi-product alignment.

## Quick Start

```python
from eoforeststac.providers.discovery import DiscoveryProvider
from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset

CATALOG = "https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json"

# Discover what is available
disc = DiscoveryProvider(catalog_url=CATALOG, endpoint_url="https://s3.gfz-potsdam.de", anon=True)
disc.list_themes()
disc.list_collections(theme="biomass-carbon")

# Stream a dataset (no download needed)
provider = ZarrProvider(catalog_url=CATALOG, endpoint_url="https://s3.gfz-potsdam.de", anon=True)
ds = provider.open_dataset(collection_id="CCI_BIOMASS", version="6.0")
ds_subset = subset(ds, geometry=geometry, time=("2010-01-01", "2020-12-31"))
```

See the [documentation](https://eoforeststac.readthedocs.io/en/latest/) and [examples](https://eoforeststac.readthedocs.io/en/latest/auto_examples/index.html) for full workflows including multi-resolution products, spatial subsetting, and multi-product alignment.

## Documentation

Full documentation is available at **https://eoforeststac.readthedocs.io/en/latest/**.

It includes:
- [User Guide](https://eoforeststac.readthedocs.io/en/latest/user/index.html): catalog structure, loading datasets, subsetting, and alignment
- [API Reference](https://eoforeststac.readthedocs.io/en/latest/user/api.html): all public classes and functions
- [Catalog Overview](https://eoforeststac.readthedocs.io/en/latest/user/catalog_overview.html): all available products by theme
- [Examples](https://eoforeststac.readthedocs.io/en/latest/auto_examples/index.html): gallery of worked examples

## Contributing

Contributions are welcome. Please open an issue or pull request on [GitHub](https://github.com/simonbesnard1/eoforeststac).

## About the authors

Simon Besnard is a senior researcher in the Global Land Monitoring Group at GFZ Helmholtz Centre Potsdam. He studies the dynamics of terrestrial ecosystems and their feedbacks on environmental conditions, specialising in the development of methods to analyse large Earth Observation and climate datasets. His current research focuses on forest structure changes over the past decade and their links to the carbon cycle.

## Contact

For questions or support:
- **Simon Besnard**: [simon.besnard@gfz.de](mailto:simon.besnard@gfz.de)

## Acknowledgments

The development of EOForestSTAC was supported by the European Union through the [FORWARDS](https://forwards-project.eu/) project.

The author thanks **Konstantin Ntokas** ([Brockmann Consult](https://www.brockmann-consult.de/)) for technical assistance, and the [EO-LINCS](https://www.eo-lincs.org/) project for valuable feedback on data structure and improvements to the STAC catalog design.

## License

This project is licensed under the European Union Public Licence v1.2 (see the [LICENSE](LICENSE) file for details).

## Citation

If you use EOForestSTAC in your research, please cite this repository:

```
Besnard, S. (2025). EOForestSTAC: A toolbox for accessing the EO forest data catalog.
GitHub repository: https://github.com/simonbesnard1/eoforeststac
```
