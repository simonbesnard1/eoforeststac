from eoforeststac.writers.potapov_height import PotapovHeightWriter

writer = PotapovHeightWriter(
    endpoint_url="https://s3.gfz-potsdam.de",
    bucket="dog.atlaseo-glm.eo-gridded-data",
)

writer.write(
    geotiff_path="/path/to/canopy_height_potapov_2020.tif",
    output_zarr="s3://dog.atlaseo-glm.eo-gridded-data/collections/POTAPOV_HEIGHT/POTAPOV_HEIGHT_v1.0.zarr",
    reference_year=2020,
)
