#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 11 11:35:35 2025

@author: simon
"""

from eoforeststac.catalog.cci_biomass import (
    create_cci_biomass_collection,
    create_cci_biomass_item
)
from eoforeststac.catalog.writer import write_collection, write_item

# Create objects in memory
col = create_cci_biomass_collection()
item = create_cci_biomass_item("5.1")

# Upload to your Ceph bucket
write_collection(col)
write_item(item)

