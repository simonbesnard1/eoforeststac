#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 15 16:13:42 2025

@author: simon
"""
from eoforeststac.providers.EFDA_provider import EFDAProvider

provider = EFDAProvider("s3://dog.atlaseo-glm.eo-gridded-data/collections/catalog.json")

# Load GeoTIFFs for 2019, version 2.1.1
efda_data = provider.load_data(2019, "2.1.1")

# Access the disturbance and agent layers
disturbance = efda_data["disturbance"]
agent = efda_data["agent"]

print(disturbance)
print(agent)
