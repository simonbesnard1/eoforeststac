from eoforeststac.writers.saatchi_biomass import SaatchiBiomassWriter

writer = SaatchiBiomassWriter(
    endpoint_url="https://s3.gfz-potsdam.de",
    bucket="dog.atlaseo-glm.eo-gridded-data",
)

INPUT_TIF = (
    "/home/besnard/projects/forest-age-upscale/"
    "data/global_product/0d00083_annual/biomass_saatchi2020/"
    "global_agb_100m_combined_mosaic_2020_cog.tif"
)

OUTPUT_ZARR = (
    "s3://dog.atlaseo-glm.eo-gridded-data/"
    "collections/Biomass_Saatchi2020/biomass_2020_v2.0.zarr"
)

writer.write(
    tif_path=INPUT_TIF,
    output_zarr=OUTPUT_ZARR,
    version="v2.0",
    chunks={"x": 500, "y": 500},
)
