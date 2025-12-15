#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 15 10:25:44 2025

@author: simon
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Dec 14 15:37:02 2025

@author: simon
"""

from eoforeststac.writers.efda import EFDAWriter

writer = EFDAWriter(
    endpoint_url="https://s3.gfz-potsdam.de",
    bucket="dog.atlaseo-glm.eo-gridded-data",
    profile="atlaseo-glm",
)

writer.write(
    mosaic_dir="/home/simon/hpc_home/projects/coupling_demography_dist/data/viana-soto_senf_data/EFDA_v211/disturbed_v211",
    agent_dir="/home/simon/hpc_home/projects/coupling_demography_dist/data/viana-soto_senf_data/EFDA_v211/agents_v211",
    years=range(1985, 2023 + 1),
    output_zarr="s3://dog.atlaseo-glm.eo-gridded-data/collections/EFDA/EFDA_v2.1.1.zarr",
    version="2.1.1"
)