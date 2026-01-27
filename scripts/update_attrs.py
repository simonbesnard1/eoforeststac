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



path = "s3://dog.atlaseo-glm.eo-gridded-data/collections/HANSEN_GFC/HANSEN_GFC_v1.12.zarr"

storage_options = {
    "client_kwargs": {"endpoint_url": "https://s3.gfz-potsdam.de"},
    "anon": False,
    "key": AWS_ACCESS_KEY_ID,
    "secret": AWS_SECRET_ACCESS_KEY,
}

mapper = fsspec.get_mapper(path, **storage_options)

# 1) Read with xarray to know what are actual data variables
ds = xr.open_zarr(mapper, consolidated=False)  # no need for consolidated to inspect names
data_vars = list(ds.data_vars)
print(f"Found {len(data_vars)} data_vars")

# 2) Patch only those arrays in the Zarr group
zg = zarr.open_group(mapper, mode="r+")  # needs write permission

for v in data_vars:
    arr = zg[v]
    arr.attrs["grid_mapping"] = "spatial_ref"


# 3) Reconsolidate so consolidated=True reads see the updated attrs
consolidate_metadata(mapper)
print("Consolidated metadata updated.")
