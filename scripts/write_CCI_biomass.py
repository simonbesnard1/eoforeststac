from eoforeststac.writers.CCI_biomass import CCI_BiomassWriter

writer = CCI_BiomassWriter(
    endpoint_url="https://s3.gfz-potsdam.de",
    bucket="dog.atlaseo-glm.eo-gridded-data",
    profile="atlaseo-glm",
)

INPUT = "/home/simon/hpc_home/projects/forest-age-upscale/data/cubes/ESACCI_BIOMASS_100m_v6"
OUTPUT = "s3://dog.atlaseo-glm.eo-gridded-data/collections/CCI_BIOMASS/CCI_BIOMASS_v6.0.zarr"

writer.write(
    input_zarr=INPUT,
    output_zarr=OUTPUT,
    version="6.0",
    chunks={"time": 5, "latitude": 1000, "longitude": 1000},
)
