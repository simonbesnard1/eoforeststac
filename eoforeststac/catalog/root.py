# eoforeststac/catalog/root.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, Optional, Tuple

import pystac

from eoforeststac.core.config import BASE_S3_URL, S3_HTTP_BASE
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
from eoforeststac.catalog.jrc_tmf import (
    create_jrc_tmf_collection,
    create_jrc_tmf_item,
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
from eoforeststac.catalog.forestpaths_genus import (
    create_forestpaths_genus_collection,
    create_forestpaths_genus_item,
)
from eoforeststac.catalog.hansen_gfc import (
    create_hansen_gfc_collection,
    create_hansen_gfc_item,
)
from eoforeststac.catalog.liu_biomass import (
    create_liu_biomass_collection,
    create_liu_biomass_item,
)

# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------

DEFAULT_VERSIONS: Dict[str, List[str]] = {
    "CCI_BIOMASS": ["6.0"],
    "SAATCHI_BIOMASS": ["2.0"],
    "JRC_TMF": ["2024"],
    "EFDA": ["2.1.1"],
    "POTAPOV_HEIGHT": ["1.0"],
    "GAMI": ["2.0", "2.1", "3.0", "3.1"],
    "JRC_GFC2020": ["3.0"],
    "ROBINSON_CR": ["1.0"],
    "FORESTPATHS_GENUS": ["0.0.1"],
    "HANSEN_GFC": ["1.12"],
    "LIU_BIOMASS": ["0.1"],
}

ItemFactory = Callable[[str], pystac.Item]
CollectionFactory = Callable[[], pystac.Collection]


@dataclass(frozen=True)
class ProductSpec:
    product_id: str
    collection_factory: CollectionFactory
    item_factory: ItemFactory


def _product_specs() -> Tuple[ProductSpec, ...]:
    """Single registry of products and their builders."""
    return (
        ProductSpec("CCI_BIOMASS", create_cci_biomass_collection, create_cci_biomass_item),
        ProductSpec("SAATCHI_BIOMASS", create_saatchi_biomass_collection, create_saatchi_biomass_item),
        ProductSpec("JRC_TMF", create_jrc_tmf_collection, create_jrc_tmf_item),
        ProductSpec("EFDA", create_efda_collection, create_efda_item),
        ProductSpec("POTAPOV_HEIGHT", create_potapov_height_collection, create_potapov_height_item),
        ProductSpec("GAMI", create_gami_collection, create_gami_item),
        ProductSpec("JRC_GFC2020", create_jrc_gfc_collection, create_jrc_gfc_item),
        ProductSpec("ROBINSON_CR", create_robinson_cr_collection, create_robinson_cr_item),
        ProductSpec("FORESTPATHS_GENUS", create_forestpaths_genus_collection, create_forestpaths_genus_item),
        ProductSpec("HANSEN_GFC", create_hansen_gfc_collection, create_hansen_gfc_item),
        ProductSpec("LIU_BIOMASS", create_liu_biomass_collection, create_liu_biomass_item),
    )


def _build_base_tree(
    versions: Mapping[str, List[str]],
    *,
    catalog_id: str,
    description: str,
) -> Tuple[pystac.Catalog, Dict[str, Tuple[pystac.Collection, ItemFactory]]]:
    """
    Build the in-memory tree once (no href normalization yet).
    Returns root catalog and a mapping {product_id: (collection, item_factory)}.
    """
    catalog = pystac.Catalog(id=catalog_id, description=description)
    catalog.catalog_type = pystac.CatalogType.RELATIVE_PUBLISHED

    # Optional: harmless hint for stac-browser
    catalog.extra_fields.setdefault("stac_browser", {"showThumbnailsAsAssets": True})

    collections: Dict[str, Tuple[pystac.Collection, ItemFactory]] = {}

    for spec in _product_specs():
        col = spec.collection_factory()
        catalog.add_child(col)
        collections[spec.product_id] = (col, spec.item_factory)

    # Create versioned items
    for prod_id, (col, item_factory) in collections.items():
        for v in versions.get(prod_id, []):
            col.add_item(item_factory(v))

    return catalog, collections


def _write_internal_with_package_writers(root: pystac.Catalog) -> None:
    """
    Write using existing package writers (write_collection/write_item),
    which expect to write to self_href (typically s3://... or local).
    """
    if root.self_href is None:
        raise ValueError("Catalog has no self_href; call normalize_hrefs() before writing.")

    write_json(root.self_href, root.to_dict())

    # Children are collections
    for col in root.get_children():  # type: ignore[assignment]
        assert isinstance(col, pystac.Collection)
        write_collection(col)
        for item in col.get_items():
            write_item(item)

def _apply_root_metadata(
    catalog: pystac.Catalog,
    *,
    title: Optional[str] = None,
    license_: Optional[str] = None,
    providers: Optional[list[dict]] = None,
    keywords: Optional[list[str]] = None,
    about_url: Optional[str] = None,
    documentation_url: Optional[str] = None,
    stac_browser: Optional[dict] = None,
) -> None:
    """Apply human-facing metadata fields to the root catalog."""
    if title is not None:
        catalog.title = title

    if license_ is not None:
        catalog.extra_fields["license"] = license_

    if providers is not None:
        catalog.extra_fields["providers"] = providers

    if keywords is not None:
        catalog.extra_fields["keywords"] = keywords

    if about_url:
        catalog.add_link(pystac.Link(rel="about", target=about_url, title="Source code"))

    if documentation_url:
        catalog.add_link(
            pystac.Link(rel="documentation", target=documentation_url, title="Documentation")
        )

    if stac_browser is not None:
        catalog.extra_fields.setdefault("stac_browser", {})
        catalog.extra_fields["stac_browser"].update(stac_browser)


def _ensure_absolute_root_self_links(pub_dict: dict, self_href: str) -> dict:
    """
    Optional: force root+self links to be absolute in the serialized JSON.
    Child links may remain relative (that's fine for STAC Browser).
    """
    for link in pub_dict.get("links", []):
        if link.get("rel") in {"self", "root"}:
            link["href"] = self_href
    return pub_dict


def _write_browser_variant(
    base_versions: Mapping[str, List[str]],
    *,
    publish_base: str,
    write_base: str,
    catalog_id: str,
    description: str,
    # ---- new: richer root metadata ----
    title: Optional[str] = None,
    license_: Optional[str] = None,
    providers: Optional[list[dict]] = None,
    keywords: Optional[list[str]] = None,
    about_url: Optional[str] = None,
    documentation_url: Optional[str] = None,
    stac_browser: Optional[dict] = None,
    # ---- new: behavior knobs ----
    force_absolute_root_links: bool = True,
) -> pystac.Catalog:
    """
    Write a browser-facing variant:
      - JSON contains https://... links (publish_base)
      - Files are written to a writable base (write_base, e.g. s3://.../public)

    Implementation:
      - Build two parallel trees:
          pub_tree  normalized to publish_base  -> provides the JSON dicts (https)
          dst_tree  normalized to write_base    -> provides the write destinations (s3)
      - Write pub_tree JSON to dst_tree self_hrefs.

    Returns
    -------
    pystac.Catalog
        The published (https-normalized) root Catalog object.
    """
    pub_root, _ = _build_base_tree(base_versions, catalog_id=catalog_id, description=description)
    dst_root, _ = _build_base_tree(base_versions, catalog_id=catalog_id, description=description)

    # Apply the same human metadata to both trees BEFORE normalization/serialization
    _apply_root_metadata(
        pub_root,
        title=title,
        license_=license_,
        providers=providers,
        keywords=keywords,
        about_url=about_url,
        documentation_url=documentation_url,
        stac_browser=stac_browser,
    )
    _apply_root_metadata(
        dst_root,
        title=title,
        license_=license_,
        providers=providers,
        keywords=keywords,
        about_url=about_url,
        documentation_url=documentation_url,
        stac_browser=stac_browser,
    )

    # Normalize hrefs for traversal / destinations
    pub_root.normalize_hrefs(publish_base)
    dst_root.normalize_hrefs(write_base)

    # Ensure self_hrefs exist
    pub_self = f"{publish_base.rstrip('/')}/catalog.json"
    dst_self = f"{write_base.rstrip('/')}/catalog.json"
    if pub_root.self_href is None:
        pub_root.set_self_href(pub_self)
    else:
        pub_self = pub_root.self_href  # preserve pystac's computed one
    if dst_root.self_href is None:
        dst_root.set_self_href(dst_self)

    # -----------------------
    # Root
    # -----------------------
    root_dict = pub_root.to_dict()
    if force_absolute_root_links:
        root_dict = _ensure_absolute_root_self_links(root_dict, pub_self)
    write_json(dst_root.self_href, root_dict)

    # -----------------------
    # Collections (match by id)
    # -----------------------
    pub_cols = {c.id: c for c in pub_root.get_children() if isinstance(c, pystac.Collection)}
    dst_cols = {c.id: c for c in dst_root.get_children() if isinstance(c, pystac.Collection)}

    for col_id, dst_col in dst_cols.items():
        pub_col = pub_cols.get(col_id)
        if pub_col is None:
            continue

        col_dict = pub_col.to_dict()
        # Optionally make collection self links absolute too (usually nice)
        if force_absolute_root_links and pub_col.self_href:
            for link in col_dict.get("links", []):
                if link.get("rel") == "self":
                    link["href"] = pub_col.self_href

        write_json(dst_col.self_href, col_dict)

        # -----------------------
        # Items (match by id)
        # -----------------------
        pub_items = {it.id: it for it in pub_col.get_items()}
        for dst_item in dst_col.get_items():
            pub_item = pub_items.get(dst_item.id)
            if pub_item is None:
                continue

            item_dict = pub_item.to_dict()
            if force_absolute_root_links and pub_item.self_href:
                for link in item_dict.get("links", []):
                    if link.get("rel") == "self":
                        link["href"] = pub_item.self_href

            write_json(dst_item.self_href, item_dict)

    return pub_root


def build_root_catalog(
    versions: Optional[Mapping[str, List[str]]] = None,
    *,
    write: bool = True,
    # Internal (s3-native) catalog
    internal_href_base: str = BASE_S3_URL,
    # Browser mirror (https links, written to s3)
    build_browser: bool = False,
    browser_publish_base: str = S3_HTTP_BASE,
    browser_write_base: Optional[str] = None,
    # Root metadata
    catalog_id: str = "EOForestSTAC",
    description="Global and regional forest Earth observation datasets.",
    title: str = "EOForestSTAC – Forest EO STAC Catalog",
    providers: Optional[list[dict]] = None,
    license_: str = "various",
    keywords: Optional[list[str]] = None,
    about_url: Optional[str] = "https://github.com/simonbesnard1/eoforeststac",
    documentation_url: Optional[str] = None,
) -> pystac.Catalog:
    """
    Build the internal EOFOREST root catalog and optionally also write a browser-friendly mirror.

    Internal catalog:
      - links & write destinations are internal_href_base (typically s3://...)

    Browser mirror:
      - JSON links use browser_publish_base (https://...), but files are written to
        browser_write_base (typically s3://.../public) to avoid https write errors.

    Returns
    -------
    pystac.Catalog
        The internal (s3://) catalog object.
    """
    versions = DEFAULT_VERSIONS if versions is None else dict(versions)

    # -----------------------
    # Build internal catalog
    # -----------------------
    internal_root, _ = _build_base_tree(
        versions,
        catalog_id=catalog_id,
        description=description,
    )

    # Root catalog "human" metadata (STAC Browser will surface this)
    internal_root.title = title
    internal_root.extra_fields["license"] = license_

    if providers is None:
        providers = [
            {
                "name": "GFZ Helmholtz Centre Potsdam",
                "roles": ["producer", "processor", "host"],
                "url": "https://www.gfz.de",
            }
        ]
    internal_root.extra_fields["providers"] = providers

    if keywords is None:
        keywords = [
            "forest",
            "earth observation",
            "biomass",
            "disturbance",
            "canopy height",
            "forest age",
            "STAC",
        ]
    internal_root.extra_fields["keywords"] = keywords

    # Helpful links for humans
    if about_url:
        internal_root.add_link(
            pystac.Link(rel="about", target=about_url, title="Source code")
        )
    if documentation_url:
        internal_root.add_link(
            pystac.Link(rel="documentation", target=documentation_url, title="Documentation")
        )

    # stac-browser optional hints
    internal_root.extra_fields.setdefault(
        "stac_browser",
        {
            "showThumbnailsAsAssets": True,
        },
    )

    # Normalize to *writable* base (s3://...) and write with your existing writers
    internal_root.normalize_hrefs(internal_href_base)
    if internal_root.self_href is None:
        internal_root.set_self_href(f"{internal_href_base.rstrip('/')}/catalog.json")

    if write:
        _write_internal_with_package_writers(internal_root)

    # -----------------------
    # Optional: browser mirror
    # -----------------------
    if build_browser:
        if browser_write_base is None:
            # Default: sibling prefix so you don't overwrite internal JSON
            browser_write_base = internal_href_base.rstrip("/") + "/public"

        _write_browser_variant(
            versions,
            publish_base=browser_publish_base,
            write_base=browser_write_base,
            catalog_id=catalog_id,
            description=description,
            # (Optional) forward the same “human” fields if your _write_browser_variant
            # rebuilds a fresh tree. If it doesn’t accept these yet, ignore this.
            title=title,              # type: ignore[arg-type]
            providers=providers,      # type: ignore[arg-type]
            license_=license_,        # type: ignore[arg-type]
            keywords=keywords,        # type: ignore[arg-type]
            about_url=about_url,      # type: ignore[arg-type]
            documentation_url=documentation_url,  # type: ignore[arg-type]
        )

    return internal_root


def build_browser_catalog(
    versions: Optional[Mapping[str, List[str]]] = None,
    *,
    publish_base: str = S3_HTTP_BASE,
    write_base: Optional[str] = None,
    internal_base_for_default: str = BASE_S3_URL,
    catalog_id: str = "EOForestSTAC",
    description: str = "Earth Observation Forest STAC catalog (eoforeststac).",
    title: str = "EOForestSTAC – Forest EO STAC Catalog",
    providers: Optional[list[dict]] = None,
    license_: str = "various",
    keywords: Optional[list[str]] = None,
    about_url: Optional[str] = "https://github.com/simonbesnard1/eoforeststac",
    documentation_url: Optional[str] = None,
) -> pystac.Catalog:
    """
    Convenience wrapper: write only the browser-facing variant and return it.
    """
    versions = DEFAULT_VERSIONS if versions is None else dict(versions)

    if write_base is None:
        write_base = internal_base_for_default.rstrip("/") + "/public"

    if providers is None:
        providers = [
            {
                "name": "GFZ Helmholtz Centre Potsdam",
                "roles": ["producer", "processor", "host"],
                "url": "https://www.gfz.de",
            }
        ]
    if keywords is None:
        keywords = [
            "forest",
            "earth observation",
            "biomass",
            "disturbance",
            "canopy height",
            "forest age",
            "STAC",
        ]

    return _write_browser_variant(
        versions,
        publish_base=publish_base,
        write_base=write_base,
        catalog_id=catalog_id,
        description=description,
        title=title,                    # type: ignore[arg-type]
        providers=providers,            # type: ignore[arg-type]
        license_=license_,              # type: ignore[arg-type]
        keywords=keywords,              # type: ignore[arg-type]
        about_url=about_url,            # type: ignore[arg-type]
        documentation_url=documentation_url,  # type: ignore[arg-type]
    )
