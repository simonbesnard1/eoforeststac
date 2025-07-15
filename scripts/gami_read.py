#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 15 12:14:07 2025

@author: simon
"""

from eoforeststac.providers.gami_provider import GAMIProvider

provider = GAMIProvider("s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json")
ds = provider.load_zarr(version="2.1")
print(ds)
