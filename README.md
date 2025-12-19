<p align="center">
<a href="https://github.com/simonbesnard1/eoforeststac">
        <img src="https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/logos/eoforestact_logo.png"
         alt="eoforeststac Logo" height="200px" hspace="0px" vspace="30px" align="left">
</a>
</p>

# EOForestSTAC: A Python toolbox for accessing forest Earth Observation datasets through SpatioTemporal Asset Catalogs (STAC).

**EOForestSTAC** provides a streamlined interface to discover and load cloud-hosted, analysis-ready forest EO datasets stored as Zarr archives on Ceph object storage.

## Features

- **STAC-native discovery** — Browse collections and versions programmatically
- **Direct Zarr access** — Load datasets from Ceph without downloads
- **Spatial subsetting** — Extract regions of interest with automatic CRS handling
- **Temporal filtering** — Query data by time range
- **Dataset alignment** — Merge multi-source datasets onto a common grid
- **Lazy loading** — Efficient on-demand data access via xarray

## Installation

```bash
pip install git+https://github.com/simonbesnard1/eoforeststac.git
```

## Quick Start

### Discover Available Data

```python
from eoforeststac.providers.discovery import DiscoveryProvider

# Connect to the catalog
disc = DiscoveryProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

# List all collections
disc.list_collections()

# List versions for a specific collection
disc.list_versions("GAMI")

# Generate an overview table
df = disc.collections_table()
```

For a complete catalog of available products, see **[CATALOG.md](CATALOG.md)**.

### Load and Subset Data

```python
import geopandas as gpd
from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset

# Initialize data provider
provider = ZarrProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

# Open a dataset
ds = provider.open_dataset(
    collection_id="CCI_BIOMASS",
    version="6.0",
)

# Load region of interest (EPSG:4326)
roi = gpd.read_file("DE-Hai.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

# Subset spatially and temporally
ds_subset = subset(
    ds,
    geometry=geometry,
    time=("2007-01-01", "2020-12-31"),
)
```

**Note:** Geometries must be provided in EPSG:4326 and are automatically reprojected to match the dataset CRS.

### Align Multiple Datasets

When working with multiple EO products, the `DatasetAligner` ensures all datasets share a common grid.

```python
from eoforeststac.providers.align import DatasetAligner

# Load first dataset (reference grid)
ds_biomass = provider.open_dataset("CCI_BIOMASS", "6.0")
ds_biomass = subset(ds_biomass, geometry=geometry, time=("2020-01-01", "2020-12-31"))

# Load second dataset
ds_saatchi = provider.open_dataset("SAATCHI_BIOMASS", "2.0")
ds_saatchi = subset(ds_saatchi, geometry=geometry, time=("2020-01-01", "2020-12-31"))

# Configure alignment
aligner = DatasetAligner(
    target="CCI_BIOMASS",
    resampling={
        "CCI_BIOMASS": {"default": "average"},
        "SAATCHI_BIOMASS": {"default": "average"},
    },
)

# Align datasets to common grid
aligned = aligner.align({
    "CCI_BIOMASS": ds_biomass.sel(time="2020-01-01"),
    "SAATCHI_BIOMASS": ds_saatchi.sel(time="2020-01-01"),
})
```

The aligned dataset is guaranteed to have:
- Identical CRS, resolution, and grid origin
- Consistent spatial dimension names
- Variable-specific resampling applied correctly

## Data Access

The catalog uses anonymous public access by default via the S3 endpoint:

```
s3://dog.atlaseo-glm.eo-gridded-data/
```

Authenticated access is also supported for restricted collections.

## About

**EOForestSTAC** is developed by Simon Besnard, senior researcher in the Global Land Monitoring Group at GFZ Helmholtz Centre Potsdam. The project focuses on analyzing terrestrial ecosystem dynamics using large-scale Earth Observation datasets, with particular emphasis on forest structure changes and carbon cycle feedbacks.

## Contact

For questions or support:
- **Simon Besnard** — [simon.besnard@gfz.de](mailto:simon.besnard@gfz.de)

## Acknowledgements

This work is supported by the European Union through the [FORWARDS](https://forwards-project.eu/) project.

## License

Licensed under the European Union Public Licence v1.2. See [LICENSE](LICENSE) for details.

## Citation

If you use EOForestSTAC in your research, please cite this repository:

```
Besnard, S. (2025). EOForestSTAC: A toolbox for accessing the EO forest data catalog.
GitHub repository: https://github.com/simonbesnard1/eoforeststac
```