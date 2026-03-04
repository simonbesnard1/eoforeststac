#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 27 13:55:26 2026

@author: simon
"""

import fsspec
import zarr
from zarr.convenience import consolidate_metadata
import xarray as xr

AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""

storage_options = {
    "client_kwargs": {"endpoint_url": "https://s3.gfz-potsdam.de"},
    "anon": False,
    "key": AWS_ACCESS_KEY_ID,
    "secret": AWS_SECRET_ACCESS_KEY,
}


paths = ["s3://dog.atlaseo-glm.eo-gridded-data/collections/JRC_GFC2020/JRC_GFC2020_v3.0.zarr",
         "s3://dog.atlaseo-glm.eo-gridded-data/collections/JRC_TMF/JRC_TMF_v2024.zarr",
         "s3://dog.atlaseo-glm.eo-gridded-data/collections/GAMI/GAMI_v2.0.zarr",
         "s3://dog.atlaseo-glm.eo-gridded-data/collections/GAMI/GAMI_v2.1.zarr",
         "s3://dog.atlaseo-glm.eo-gridded-data/collections/GAMI/GAMI_v3.0.zarr",
         "s3://dog.atlaseo-glm.eo-gridded-data/collections/GAMI/GAMI_v3.1.zarr"
         ]

for path in paths:
    mapper = fsspec.get_mapper(path, **storage_options)
    zg = zarr.open_group(mapper, mode="r+")  # needs write permission
    if "crs" in zg.attrs:
        zg.attrs["spatial_ref"] = zg.attrs["crs"]
        del zg.attrs["crs"]
    
    # 3) Reconsolidate so consolidated=True reads see the updated attrs
    consolidate_metadata(mapper)
    print("Consolidated metadata updated.")



# 1) Read with xarray to know what are actual data variables
# ds = xr.open_zarr(
#     mapper, consolidated=False
# )  # no need for consolidated to inspect names
# data_vars = list(ds.data_vars)
# print(f"Found {len(data_vars)} data_vars")

# 2) Patch only those arrays in the Zarr group
zg = zarr.open_group(mapper, mode="r+")  # needs write permission

# for v in data_vars:
#     arr = zg[v]
#     arr.attrs["grid_mapping"] = "spatial_ref"


#zg.attrs["crs"] = "spatial_ref"

# 3) Reconsolidate so consolidated=True reads see the updated attrs
#consolidate_metadata(mapper)
#print("Consolidated metadata updated.")


