# eoforeststac/catalog/root.py

import pystac
from typing import Dict, List

from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.io import write_json
from eoforeststac.catalog.writer import write_collection, write_item

# Import collection/item builders
from eoforeststac.catalog.cci_biomass import (
    create_cci_biomass_collection,
    create_cci_biomass_item,
)
from eoforeststac.catalog.saatchi_biomass import (
    create_saatchi_biomass_collection,
    create_saatchi_biomass_item,
)
from eoforeststac.catalog.tmf import (
    create_tmf_collection,
    create_tmf_item,
)
from eoforeststac.catalog.efda import (
    create_efda_collection,
    create_efda_item,
)
from eoforeststac.catalog.potapov_height import (
    create_potapov_height_collection,
    create_potapov_height_item,
)
from eoforeststac.catalog.gami import (
    create_gami_collection,
    create_gami_item,
)

from eoforeststac.catalog.jrc_gfc import (
    create_jrc_gfc_collection,
    create_jrc_gfc_item,
)

from eoforeststac.catalog.robinson_cr import (
    create_robinson_cr_collection,
    create_robinson_cr_item,
)


# Optional: declare which versions you want to register as items
DEFAULT_VERSIONS: Dict[str, List[str]] = {
    "CCI_BIOMASS": ["6.0"],
    "SAATCHI_BIOMASS": ["2.0"],
    "TMF": ["3.0"],
    "EFDA": ["2.1.1"],
    "POTAPOV_HEIGHT": ["1.0"],
    "GAMI": ["2.0", "2.1", '3.0', '3.1'],
    "JRC_GFC2020": ["1.0", "2.0", "3.0"],
    "ROBINSON_CR": ["1.0"]   
}

def build_root_catalog(
    versions: Dict[str, List[str]] | None = None,
    write: bool = True,
) -> pystac.Catalog:
    """
    Build the root EOForest STAC Catalog, attach all known collections,
    optionally create versioned items, and (optionally) write everything
    to the Ceph/S3 bucket.

    Parameters
    ----------
    versions : dict or None
        Mapping from product ID to list of versions, e.g.:
        {"CCI_BIOMASS": ["6.0", "5.1"]}.
        If None, uses DEFAULT_VERSIONS.
    write : bool
        If True, writes catalog + collections + items to storage.

    Returns
    -------
    pystac.Catalog
        The in-memory root Catalog object.
    """
    if versions is None:
        versions = DEFAULT_VERSIONS

    # ------------------------------------------------------------------
    # 1. Create root catalog
    # ------------------------------------------------------------------
    catalog = pystac.Catalog(
        id="EOFOREST",
        description="Earth Observation Forest STAC catalog (eoforeststac).",
        href=f"{BASE_S3_URL}/catalog.json",
    )

    # ------------------------------------------------------------------
    # 2. Create collections
    # ------------------------------------------------------------------
    collections = {}

    # CCI Biomass
    cci_col = create_cci_biomass_collection()
    catalog.add_child(cci_col)
    collections["CCI_BIOMASS"] = (cci_col, create_cci_biomass_item)

    # Saatchi Biomass
    saatchi_col = create_saatchi_biomass_collection()
    catalog.add_child(saatchi_col)
    collections["SAATCHI_BIOMASS"] = (saatchi_col, create_saatchi_biomass_item)

    # TMF
    tmf_col = create_tmf_collection()
    catalog.add_child(tmf_col)
    collections["TMF"] = (tmf_col, create_tmf_item)

    # EFDA
    efda_col = create_efda_collection()
    catalog.add_child(efda_col)
    collections["EFDA"] = (efda_col, create_efda_item)

    # Potapov Height
    potapov_col = create_potapov_height_collection()
    catalog.add_child(potapov_col)
    collections["POTAPOV_HEIGHT"] = (potapov_col, create_potapov_height_item)

    # GAMI
    gami_col = create_gami_collection()
    catalog.add_child(gami_col)
    collections["GAMI"] = (gami_col, create_gami_item)
    
    # JRC_GFC
    jrc_gfc_col = create_jrc_gfc_collection()
    catalog.add_child(jrc_gfc_col)
    collections["JRC_GFC2020"] = (jrc_gfc_col, create_jrc_gfc_item)
    
    # ROBINSON_CR
    robinson_cr_col = create_robinson_cr_collection()
    catalog.add_child(robinson_cr_col)
    collections["ROBINSON_CR"] = (robinson_cr_col, create_robinson_cr_item)
    
    # ------------------------------------------------------------------
    # 3. Create items for each version (if specified)
    # ------------------------------------------------------------------
    for prod_id, (col, item_factory) in collections.items():
        for v in versions.get(prod_id, []):
            item = item_factory(v)
            col.add_item(item)

    # ------------------------------------------------------------------
    # 4. Normalize HREFs and optionally write everything out
    # ------------------------------------------------------------------
    catalog.normalize_hrefs(BASE_S3_URL)

    if write:
        # Write root catalog
        write_json(catalog.self_href, catalog.to_dict())

        # Write each collection and its items
        for col, _item_factory in collections.values():
            write_collection(col)
            for item in col.get_items():
                write_item(item)

    return catalog
