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
[![DOI](https://zenodo.org/badge/1020058794.svg)](https://doi.org/10.5281/zenodo.22123168)

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
- **Region statistics**: Area-weighted time series (e.g. mean biomass and total stock) for any polygon, the same computation the explorer's Analysis tab uses
- **Lazy loading**: Efficient on-demand data access via xarray and Dask

## Why EOForestSTAC?

EOForestSTAC removes the friction of working with large-scale forest EO data by combining a curated STAC metadata catalog with cloud-native Zarr storage. Instead of downloading multi-gigabyte files and managing local copies, users can stream exactly the spatial and temporal subset they need directly into an xarray Dataset. The catalog structure makes it straightforward to discover what is available, compare versions, and combine multiple products on a common grid for integrated analyses.

## Explore the Catalog Interactively

The recommended starting point for new users is the interactive **STAC Browser**:

### 👉 [https://simonbesnard1.github.io/eoforeststac/](https://simonbesnard1.github.io/eoforeststac/)

The browser lets you browse all collections and versions by theme, inspect spatial footprints on a map, view dataset metadata and provenance, and copy asset URLs directly for use in Python.

The raster explorer adds interactive Zarr rendering, layer styling, pixel
inspection, area downloads and region analysis (area-weighted time series of the
active biomass layers over a drawn area). It runs on a GFZ virtual machine together with its
TiTiler tile service and is reachable from the GFZ network at
**http://eoforeststac.gfz.de**.

### Hosting

GitHub Pages publishes the STAC Browser through `.github/workflows/deploy.yml`.
The explorer and TiTiler are deployed with Docker Compose on the VM; see
[deploy/vm/README.md](deploy/vm/README.md).

For local development, from the repository root (the explorer's
`webapp/config.js` points at `http://localhost:8000`):

```bash
python -m pip install -r deploy/titiler/requirements.txt
PYTHONPATH=. DOWNLOAD_DIR=/tmp/eoforeststac-downloads \
TITILER_XARRAY_API_CORS_ALLOW_METHODS=GET,POST \
  uvicorn app:app --app-dir deploy/titiler --reload --port 8000
python -m http.server 8080 --directory webapp      # then open localhost:8080
```

`POST` must be allowed because the explorer runs on another port and posts
analysis and download jobs; on the VM both share one origin behind nginx.

### Checking stores before publishing

`eoforeststac-check` compares every Zarr store on S3 with the catalog's
conventions (a declared fill value, north-to-south latitude, CF dates, time
first, a CRS link, units, a sane legend range) from metadata alone, in
seconds. It exits with status 1 on an error, so it can gate a release;
writers print the same findings after a write. A product accepts a known
exception in its config, e.g. `"checks": {"accept": ["zero-fill"]}` for
LIU, whose source maps use 0 for no data. The rules are in
[eoforeststac/checks/conventions.py](eoforeststac/checks/conventions.py).

### Building visualization pyramids

Large stores are drawn from precomputed Zarr overview levels. On a server
close to GFZ Ceph, `eoforeststac-pyramids` builds every missing or unfinished
pyramid (`--dry-run` shows the plan first). See
[eoforeststac/pyramids/README.md](eoforeststac/pyramids/README.md) for the
options and the per-variable aggregation rules.

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

CATALOG = "https://s3.gfz.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json"

# Discover what is available
disc = DiscoveryProvider(catalog_url=CATALOG, endpoint_url="https://s3.gfz.de", anon=True)
disc.list_themes()
disc.list_collections(theme="biomass-carbon")

# Stream a dataset (no download needed)
provider = ZarrProvider(catalog_url=CATALOG, endpoint_url="https://s3.gfz.de", anon=True)
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

## Data Ingestion Requests

Want a new dataset, region, or resolution added to the catalog? Use the **Ingestion Queue**:

- **Submit a request**: [Open a data ingestion request](https://github.com/simonbesnard1/eoforeststac/issues/new?template=data-ingestion-request.yml) on GitHub
- **Track progress**: View all requests and their status on the [Ingestion Dashboard](https://doidata.gfz.de/simon/dashboard/)

Requests are tracked via GitHub Issues with status labels (`queued`, `processing`, `done`, `blocked`). Processors and requesters can discuss details directly in the issue thread.

## Contributing

Contributions are welcome. Please open an issue or pull request on [GitHub](https://github.com/simonbesnard1/eoforeststac).

## About the authors

Simon Besnard is a senior researcher in the Global Land Monitoring Group at GFZ Helmholtz Centre Potsdam. He studies the dynamics of terrestrial ecosystems and their feedbacks on environmental conditions, specialising in the development of methods to analyse large Earth Observation and climate datasets. His current research focuses on forest structure changes over the past decade and their links to the carbon cycle.

## Contact

For questions or support:
- **Simon Besnard**: [simon.besnard@gfz.de](mailto:simon.besnard@gfz.de)

## Acknowledgments

The development of EOForestSTAC was supported by the European Union through the [FORWARDS](https://forwards-project.eu/) project.

The web explorer's code was written with [Claude Code](https://claude.com/claude-code) (Anthropic), directed and reviewed by the author, and its interface design is inspired by [Global Forest Watch](https://www.globalforestwatch.org).

The author thanks **Konstantin Ntokas** ([Brockmann Consult](https://www.brockmann-consult.de/)) for technical assistance, and the [EO-LINCS](https://www.eo-lincs.org/) project for valuable feedback on data structure and improvements to the STAC catalog design.

## License

This project is licensed under the European Union Public Licence v1.2 (see the [LICENSE](LICENSE) file for details).

## Citation

If you use EOForestSTAC in your research, please cite this repository:

```
Besnard, S. (2025). EOForestSTAC: A toolbox for accessing the EO forest data catalog.
GitHub repository: https://github.com/simonbesnard1/eoforeststac
```
