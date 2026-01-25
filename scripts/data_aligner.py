import geopandas as gpd
from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset

from eoforeststac.providers.align import DatasetAligner


provider = ZarrProvider(
    catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

roi = gpd.read_file("/home/simon/Documents/science/GFZ/projects/foreststrucflux/data/geojson/CZ-Lnz.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

ds = provider.open_dataset(
    collection_id="RADD_EUROPE",
    version="1.0",
)

ds_biomass = subset(
    ds,
    geometry=geometry,                 # geometry in EPSG:4326
    time=("2007-01-01", "2020-12-31"))  # optional

ds = provider.open_dataset(
    collection_id="CCI_BIOMASS",
    version="6.0",
)

ds_efda = subset(
    ds,
    geometry=geometry ,                 # geometry in EPSG:4326
    time=("2020-01-01", "2020-12-31"))


aligner = DatasetAligner(
    target="CCI_BIOMASS",
    resampling={
        "CCI_BIOMASS": {"default": "average"},
        "SAATCHI_BIOMASS": {"default": "average"}
        }
)

aligned = aligner.align({
    "CCI_BIOMASS": ds_biomass,
    "SAATCHI_BIOMASS": ds_efda
})

aligned
