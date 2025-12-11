from eoforeststac.writers.gami import GAMIWriter

writer = GAMIWriter(
    endpoint_url="https://s3.gfz-potsdam.de",
    key="...",
    secret="..."
)

writer.write(
    "/project/glm/.../AgeUpscale_100m",
    "s3://dog.atlaseo-glm.eo-gridded-data/collections/GAMI/GAMI_v3.1.zarr"
)
