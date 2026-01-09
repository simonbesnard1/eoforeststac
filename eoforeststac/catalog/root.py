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

# ---------------------------------------------------------------------
# Themes (atlas-style structure)
# ---------------------------------------------------------------------
THEMES: Dict[str, Dict[str, object]] = {
    "biomass-carbon": {
        "title": "Biomass & Carbon",
        "description": "Biomass stocks, canopy carbon, and regrowth/carbon accumulation products.",
        "keywords": ["biomass", "carbon", "agb", "regrowth", "carbon removal"],
        "products": ["CCI_BIOMASS", "SAATCHI_BIOMASS", "LIU_BIOMASS", "ROBINSON_CR"],
    },
    "disturbance-change": {
        "title": "Disturbance & Change",
        "description": "Forest disturbance, loss, and change layers from continental to global scales.",
        "keywords": ["disturbance", "mortality", "forest loss", "change", "harvest", "fire"],
        "products": ["EFDA", "JRC_TMF", "HANSEN_GFC", "JRC_GFC2020"],
    },
    "structure-demography": {
        "title": "Structure & Demography",
        "description": "Forest age, canopy height, and composition layers to study structure and dynamics.",
        "keywords": ["forest age", "canopy height", "genus", "composition", "demography"],
        "products": ["GAMI", "POTAPOV_HEIGHT", "FORESTPATHS_GENUS"],
    },
}

THEME_THUMBNAILS: dict[str, str] = {
    "biomass-carbon": "https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/thumbnails/theme-biomass-carbon.png",
    "disturbance-change": "https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/thumbnails/theme-disturbance-change.png",
    "structure-demography": "https://raw.githubusercontent.com/simonbesnard1/eoforeststac/main/doc/_static/thumbnails/theme-structure-demography.png",
}

def _set_thumbnail(obj: pystac.STACObject, href: str, *, title: str | None = None) -> None:
    # 1) Non-standard but commonly supported by stac-browser
    obj.extra_fields.setdefault("assets", {})
    obj.extra_fields["assets"]["thumbnail"] = {
        "href": href,
        "type": "image/png",
        "roles": ["thumbnail"],
        **({"title": title} if title else {}),
    }

    # 2) Standard STAC links (more portable across viewers)
    obj.add_link(pystac.Link(rel="preview", target=href, media_type="image/png", title=title))
    obj.add_link(pystac.Link(rel="icon", target=href, media_type="image/png", title=title))


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
    Build an in-memory catalog tree (no href normalization yet).

    Structure:
      root catalog
        ├─ theme subcatalogs (Catalog)
        │    └─ collections
        │         └─ items (versioned)
    Returns root catalog and a mapping {product_id: (collection, item_factory)}.
    """
    root = pystac.Catalog(id=catalog_id, description=description)
    root.catalog_type = pystac.CatalogType.RELATIVE_PUBLISHED

    # Optional: hint for stac-browser
    root.extra_fields.setdefault("stac_browser", {"showThumbnailsAsAssets": True})

    # Build a lookup of product builders
    specs_by_id: Dict[str, ProductSpec] = {s.product_id: s for s in _product_specs()}

    # Track collections we actually created (for items + writing)
    collections: Dict[str, Tuple[pystac.Collection, ItemFactory]] = {}

    # 1) Create theme subcatalogs
    theme_nodes: Dict[str, pystac.Catalog] = {}    
    for theme_id, meta in THEMES.items():
        theme_cat = pystac.Catalog(
            id=theme_id,
            description=str(meta["description"]),
            title=str(meta["title"]),
        )
        theme_cat.catalog_type = pystac.CatalogType.RELATIVE_PUBLISHED

        # ✅ add thumbnail to *this* catalog (the card you're seeing)
        thumb = THEME_THUMBNAILS.get(theme_id)
        if thumb:
            _set_thumbnail(theme_cat, thumb, title=str(meta["title"]))

        root.add_child(theme_cat)
        theme_nodes[theme_id] = theme_cat

    # 2) Attach collections under themes
    assigned: set[str] = set()
    for theme_id, meta in THEMES.items():
        product_ids = list(meta["products"])  # type: ignore[assignment]
        for prod_id in product_ids:
            if prod_id not in specs_by_id:
                raise KeyError(f"Theme '{theme_id}' references unknown product_id '{prod_id}'")

            if prod_id in assigned:
                raise ValueError(f"Product '{prod_id}' is listed in multiple themes; choose one parent only.")
            assigned.add(prod_id)

            spec = specs_by_id[prod_id]
            col = spec.collection_factory()
            theme_nodes[theme_id].add_child(col)
            collections[prod_id] = (col, spec.item_factory)

    # 3) Ensure no product is “orphaned” (unless you intentionally want that)
    all_products = set(specs_by_id.keys())
    missing = sorted(all_products - assigned)
    if missing:
        raise ValueError(
            "Some products are not assigned to any theme: "
            + ", ".join(missing)
            + ". Add them to THEMES or decide an 'other' theme."
        )

    # 4) Create versioned items under each collection
    for prod_id, (col, item_factory) in collections.items():
        for v in versions.get(prod_id, []):
            col.add_item(item_factory(v))

    return root, collections


def _iter_collections(node: pystac.Catalog) -> List[pystac.Collection]:
    cols: List[pystac.Collection] = []
    for child in node.get_children():
        if isinstance(child, pystac.Collection):
            cols.append(child)
        elif isinstance(child, pystac.Catalog):
            cols.extend(_iter_collections(child))
    return cols


def _write_internal_with_package_writers(root: pystac.Catalog) -> None:
    """
    Write using existing package writers (write_collection/write_item).
    Works for themed catalogs (nested Catalog -> Collection -> Item).
    """
    if root.self_href is None:
        raise ValueError("Catalog has no self_href; call normalize_hrefs() before writing.")

    write_json(root.self_href, root.to_dict())

    for col in _iter_collections(root):
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
    # ---- richer root metadata ----
    title: Optional[str] = None,
    license_: Optional[str] = None,
    providers: Optional[list[dict]] = None,
    keywords: Optional[list[str]] = None,
    about_url: Optional[str] = None,
    documentation_url: Optional[str] = None,
    stac_browser: Optional[dict] = None,
    # ---- behavior knobs ----
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
        pub_self = pub_root.self_href
    if dst_root.self_href is None:
        dst_root.set_self_href(dst_self)

    # -----------------------
    # Helper: iterate nested *Catalog* nodes (excluding Collections)
    # -----------------------
    def _iter_catalog_nodes(node: pystac.Catalog) -> list[pystac.Catalog]:
        cats: list[pystac.Catalog] = []
        for child in node.get_children():
            # Collections are Catalog subclasses — exclude them here
            if isinstance(child, pystac.Catalog) and not isinstance(child, pystac.Collection):
                cats.append(child)
                cats.extend(_iter_catalog_nodes(child))
        return cats

    # -----------------------
    # Root
    # -----------------------
    root_dict = pub_root.to_dict()
    if force_absolute_root_links:
        root_dict = _ensure_absolute_root_self_links(root_dict, pub_self)
    write_json(dst_root.self_href, root_dict)

    # -----------------------
    # Theme subcatalogs (Catalog JSONs)
    # -----------------------
    pub_cats = {c.id: c for c in _iter_catalog_nodes(pub_root)}
    dst_cats = {c.id: c for c in _iter_catalog_nodes(dst_root)}

    # Safety: ensure both trees contain same catalog node ids
    if set(pub_cats.keys()) != set(dst_cats.keys()):
        raise RuntimeError(
            "pub/dst theme catalog sets differ; refusing to write inconsistent browser variant."
        )

    for cat_id, dst_cat in dst_cats.items():
        pub_cat = pub_cats[cat_id]

        cat_dict = pub_cat.to_dict()
        if force_absolute_root_links and pub_cat.self_href:
            for link in cat_dict.get("links", []):
                if link.get("rel") == "self":
                    link["href"] = pub_cat.self_href

        # Write theme catalog.json (https JSON -> s3 destination)
        write_json(dst_cat.self_href, cat_dict)

    # -----------------------
    # Collections (match by id)
    # -----------------------
    pub_cols = {c.id: c for c in _iter_collections(pub_root)}
    dst_cols = {c.id: c for c in _iter_collections(dst_root)}

    # Safety: ensure both trees contain same collection ids
    if set(pub_cols.keys()) != set(dst_cols.keys()):
        raise RuntimeError(
            "pub/dst collection sets differ; refusing to write inconsistent browser variant."
        )

    for col_id, dst_col in dst_cols.items():
        pub_col = pub_cols[col_id]

        col_dict = pub_col.to_dict()
        if force_absolute_root_links and pub_col.self_href:
            for link in col_dict.get("links", []):
                if link.get("rel") == "self":
                    link["href"] = pub_col.self_href

        write_json(dst_col.self_href, col_dict)

        # -----------------------
        # Items (match by id)
        # -----------------------
        pub_items = {it.id: it for it in pub_col.get_items()}
        dst_items = list(dst_col.get_items())

        # Optional safety: ensure same item ids
        if set(pub_items.keys()) != {it.id for it in dst_items}:
            raise RuntimeError(
                f"pub/dst item sets differ for collection '{col_id}'; refusing to write inconsistent browser variant."
            )

        for dst_item in dst_items:
            pub_item = pub_items[dst_item.id]

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
    description :str =
        "A thematic atlas of forest Earth observation datasets, bringing together "
        "global and regional products on biomass, carbon cycling, disturbance, "
        "canopy structure, and forest demography to support integrated ecosystem analysis.",
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
    title: str = "EOForestSTAC – EO Forest STAC Catalog",
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
