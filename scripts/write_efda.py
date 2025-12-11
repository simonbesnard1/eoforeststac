from eoforeststac.writers.efda import EFDAWriter

writer = EFDAWriter(
    endpoint_url="https://s3.gfz-potsdam.de",
    bucket="dog.atlaseo-glm.eo-gridded-data",
)

writer.write(
    mosaic_dir="/path/to/efda/mosaics",
    agent_dir="/path/to/efda/agents",
    years=range(1985, 2023 + 1),
    output_zarr="s3://dog.atlaseo-glm.eo-gridded-data/collections/EFDA/EFDA_v1.0.zarr",
)
