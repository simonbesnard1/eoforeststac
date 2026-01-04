import geopandas as gpd
from eoforeststac.providers.zarr import ZarrProvider
from eoforeststac.providers.subset import subset

from eoforeststac.providers.align import DatasetAligner


provider = ZarrProvider(
    catalog_url="s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json",
    endpoint_url="https://s3.gfz-potsdam.de",
    anon=True,
)

roi = gpd.read_file("/home/simon/Documents/science/GFZ/projects/foreststrucflux/data/geojson/BR-Sa3.geojson")
geometry = roi.to_crs("EPSG:4326").geometry.union_all()

ds = provider.open_dataset(
    collection_id="JRC_TMF",
    version="2024",
)

ds_biomass = subset(
    ds,
    geometry=geometry,                 # geometry in EPSG:4326
    time=("2007-01-01", "2020-12-31"))  # optional

ds = provider.open_dataset(
    collection_id="SAATCHI_BIOMASS",
    version="2.0",
)

ds_efda = subset(
    ds,
    geometry=geometry,                 # geometry in EPSG:4326
    time=("2020-01-01", "2020-12-31"))


aligner = DatasetAligner(
    target="CCI_BIOMASS",
    resampling={
        "CCI_BIOMASS": {"default": "average"},
        "EFDA": {"default": "average"}
        }
)

aligned = aligner.align({
    "CCI_BIOMASS": ds_biomass,
    "EFDA": ds_efda
})

aligned
