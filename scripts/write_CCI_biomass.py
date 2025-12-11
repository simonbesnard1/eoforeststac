from eoforeststac.writers.cci_biomass import CCI_BiomassWriter

writer = CCI_BiomassWriter(
    endpoint_url="https://s3.gfz-potsdam.de",
    bucket="dog.atlaseo-glm.eo-gridded-data",
)

INPUT = "/home/besnard/projects/forest-age-upscale/data/cubes/ESACCI_BIOMASS_100m_v6"
OUTPUT = "s3://dog.atlaseo-glm.eo-gridded-data/collections/ESA_CCI_BIOMASS/ESA_CCI_BIOMASS_v6.zarr"

writer.write(
    input_zarr=INPUT,
    output_zarr=OUTPUT,
    version="6.0",
    chunks={"time": -1, "latitude": 1000, "longitude": 1000},
)
