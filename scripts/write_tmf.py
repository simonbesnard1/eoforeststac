from eoforeststac.writers.tmf import TMFWriter

writer = TMFWriter(
    endpoint_url="https://s3.gfz-potsdam.de",
    bucket="dog.atlaseo-glm.eo-gridded-data",
)

writer.write(
    input_dir="/path/to/tmf_geotiffs",
    years=range(1990, 2023 + 1),
    pattern="{year}_tmf_disturb.tif",
    output_zarr="s3://dog.atlaseo-glm.eo-gridded-data/collections/TMF/TMF_v3.0.zarr",
)
