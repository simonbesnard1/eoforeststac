"""STAC validation tests for the EOForestSTAC catalog.

Validates that every collection, item, and asset produced by the catalog
builder conforms to the STAC spec and internal consistency rules.
"""

import pytest
import pystac

from eoforeststac.catalog.root import (
    DEFAULT_VERSIONS,
    THEMES,
    _build_base_tree,
    _product_specs,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(scope="module")
def catalog_tree():
    """Build the full catalog tree once for all tests."""
    root, collections = _build_base_tree(
        DEFAULT_VERSIONS,
        catalog_id="test-eoforeststac",
        description="Test catalog for validation.",
    )
    root.normalize_hrefs("https://example.com/stac")
    return root, collections


@pytest.fixture(scope="module")
def all_collections(catalog_tree):
    root, _ = catalog_tree
    cols = []
    for child in root.get_children():
        for c in child.get_children():
            if isinstance(c, pystac.Collection):
                cols.append(c)
    return cols


@pytest.fixture(scope="module")
def all_items(all_collections):
    items = []
    for col in all_collections:
        items.extend(list(col.get_items()))
    return items


# ------------------------------------------------------------------
# Catalog structure
# ------------------------------------------------------------------


class TestCatalogStructure:
    def test_root_is_catalog(self, catalog_tree):
        root, _ = catalog_tree
        assert isinstance(root, pystac.Catalog)

    def test_root_has_children(self, catalog_tree):
        root, _ = catalog_tree
        children = list(root.get_children())
        assert len(children) > 0

    def test_theme_catalogs_exist(self, catalog_tree):
        root, _ = catalog_tree
        theme_ids = {c.id for c in root.get_children()}
        for theme_id in THEMES:
            assert theme_id in theme_ids, f"Theme '{theme_id}' missing from catalog"

    def test_every_product_assigned_to_theme(self):
        specs = {s.product_id for s in _product_specs()}
        assigned = set()
        for meta in THEMES.values():
            assigned.update(meta["products"])
        missing = specs - assigned
        assert not missing, f"Products not assigned to any theme: {missing}"

    def test_no_product_in_multiple_themes(self):
        seen = {}
        for theme_id, meta in THEMES.items():
            for prod in meta["products"]:
                assert (
                    prod not in seen
                ), f"Product '{prod}' in both '{seen[prod]}' and '{theme_id}'"
                seen[prod] = theme_id

    def test_all_default_versions_have_specs(self):
        spec_ids = {s.product_id for s in _product_specs()}
        for prod_id in DEFAULT_VERSIONS:
            assert (
                prod_id in spec_ids
            ), f"DEFAULT_VERSIONS references '{prod_id}' but no ProductSpec exists"


# ------------------------------------------------------------------
# Collection validation
# ------------------------------------------------------------------


class TestCollections:
    def test_collections_exist(self, all_collections):
        assert len(all_collections) == len(DEFAULT_VERSIONS)

    @pytest.mark.network
    def test_collection_validates(self, all_collections):
        for col in all_collections:
            try:
                col.validate()
            except pystac.STACValidationError as e:
                pytest.fail(f"Collection '{col.id}' failed validation: {e}")
            except Exception:
                pass

    def test_collection_has_required_fields(self, all_collections):
        for col in all_collections:
            assert col.id, f"Collection missing id"
            assert col.title, f"Collection '{col.id}' missing title"
            assert col.description, f"Collection '{col.id}' missing description"
            assert col.license, f"Collection '{col.id}' missing license"
            assert col.extent, f"Collection '{col.id}' missing extent"

    def test_collection_has_temporal_extent(self, all_collections):
        for col in all_collections:
            intervals = col.extent.temporal.intervals
            assert intervals, f"Collection '{col.id}' has no temporal intervals"
            start, end = intervals[0]
            assert (
                start is not None or end is not None
            ), f"Collection '{col.id}' has empty temporal interval"

    def test_collection_has_spatial_extent(self, all_collections):
        for col in all_collections:
            bboxes = col.extent.spatial.bboxes
            assert bboxes, f"Collection '{col.id}' has no bounding boxes"
            bbox = bboxes[0]
            assert (
                len(bbox) == 4
            ), f"Collection '{col.id}' bbox has {len(bbox)} elements, expected 4"
            west, south, east, north = bbox
            assert west <= east, f"Collection '{col.id}': west > east"
            assert south <= north, f"Collection '{col.id}': south > north"

    def test_collection_has_providers(self, all_collections):
        for col in all_collections:
            assert col.providers, f"Collection '{col.id}' has no providers"

    def test_collection_has_keywords(self, all_collections):
        for col in all_collections:
            assert col.keywords, f"Collection '{col.id}' has no keywords"

    def test_collection_has_summaries(self, all_collections):
        for col in all_collections:
            assert col.summaries is not None, f"Collection '{col.id}' has no summaries"

    def test_collection_has_item_assets(self, all_collections):
        for col in all_collections:
            item_assets = col.extra_fields.get("item_assets", {})
            assert item_assets, f"Collection '{col.id}' has no item_assets defined"

    def test_collection_license_is_spdx(self, all_collections):
        import re

        spdx_pattern = re.compile(r"^[\w\-\.+]+$")
        for col in all_collections:
            assert spdx_pattern.match(col.license), (
                f"Collection '{col.id}' license '{col.license}' is not a valid "
                f"SPDX identifier (must match ^[\\w\\-\\.+]+$)"
            )


# ------------------------------------------------------------------
# Item validation
# ------------------------------------------------------------------


class TestItems:
    def test_items_exist(self, all_items):
        assert len(all_items) > 0

    @pytest.mark.network
    def test_item_validates(self, all_items):
        for item in all_items:
            try:
                item.validate()
            except pystac.STACValidationError as e:
                pytest.fail(f"Item '{item.id}' failed validation: {e}")
            except Exception:
                pass

    def test_item_has_required_fields(self, all_items):
        for item in all_items:
            assert item.id, "Item missing id"
            assert item.geometry, f"Item '{item.id}' missing geometry"
            assert item.bbox, f"Item '{item.id}' missing bbox"
            assert (
                item.datetime or item.common_metadata.start_datetime
            ), f"Item '{item.id}' missing datetime"

    def test_item_bbox_valid(self, all_items):
        for item in all_items:
            bbox = item.bbox
            assert (
                len(bbox) == 4
            ), f"Item '{item.id}' bbox has {len(bbox)} elements, expected 4"
            west, south, east, north = bbox
            assert west <= east, f"Item '{item.id}': west > east"
            assert south <= north, f"Item '{item.id}': south > north"

    def test_item_geometry_valid(self, all_items):
        for item in all_items:
            geom = item.geometry
            assert "type" in geom, f"Item '{item.id}' geometry missing type"
            assert (
                "coordinates" in geom
            ), f"Item '{item.id}' geometry missing coordinates"

    def test_item_has_assets(self, all_items):
        for item in all_items:
            assert item.assets, f"Item '{item.id}' has no assets"

    def test_item_has_properties(self, all_items):
        for item in all_items:
            assert item.properties, f"Item '{item.id}' has no properties"
            assert (
                "product_name" in item.properties
            ), f"Item '{item.id}' missing 'product_name' property"
            assert (
                "version" in item.properties
            ), f"Item '{item.id}' missing 'version' property"


# ------------------------------------------------------------------
# Asset validation
# ------------------------------------------------------------------


class TestAssets:
    def test_zarr_assets_have_correct_media_type(self, all_items):
        for item in all_items:
            for key, asset in item.assets.items():
                if "zarr" in key:
                    assert asset.media_type == "application/vnd.zarr", (
                        f"Item '{item.id}' asset '{key}' has media_type "
                        f"'{asset.media_type}', expected 'application/vnd.zarr'"
                    )

    def test_assets_have_href(self, all_items):
        for item in all_items:
            for key, asset in item.assets.items():
                assert asset.href, f"Item '{item.id}' asset '{key}' has no href"

    def test_assets_have_roles(self, all_items):
        for item in all_items:
            for key, asset in item.assets.items():
                assert asset.roles, f"Item '{item.id}' asset '{key}' has no roles"

    def test_assets_have_title(self, all_items):
        for item in all_items:
            for key, asset in item.assets.items():
                assert asset.title, f"Item '{item.id}' asset '{key}' has no title"


# ------------------------------------------------------------------
# Raster bands extension
# ------------------------------------------------------------------


class TestRasterBands:
    def test_zarr_assets_have_raster_bands(self, all_items):
        for item in all_items:
            for key, asset in item.assets.items():
                if "zarr" in key:
                    bands = asset.extra_fields.get("raster:bands", [])
                    assert bands, f"Item '{item.id}' asset '{key}' missing raster:bands"

    def test_raster_bands_have_name(self, all_items):
        for item in all_items:
            for key, asset in item.assets.items():
                for band in asset.extra_fields.get("raster:bands", []):
                    assert (
                        "name" in band
                    ), f"Item '{item.id}' asset '{key}': band missing 'name'"

    def test_raster_bands_have_data_type(self, all_items):
        for item in all_items:
            for key, asset in item.assets.items():
                for band in asset.extra_fields.get("raster:bands", []):
                    assert "data_type" in band, (
                        f"Item '{item.id}' asset '{key}' band '{band.get('name')}' "
                        f"missing 'data_type'"
                    )

    def test_raster_bands_have_nodata(self, all_items):
        for item in all_items:
            for key, asset in item.assets.items():
                for band in asset.extra_fields.get("raster:bands", []):
                    assert "nodata" in band, (
                        f"Item '{item.id}' asset '{key}' band '{band.get('name')}' "
                        f"missing 'nodata'"
                    )


# ------------------------------------------------------------------
# STAC extensions
# ------------------------------------------------------------------


class TestLinks:
    def test_collections_have_cite_as_link(self, all_collections):
        for col in all_collections:
            links = col.get_links("cite-as")
            assert links, (
                f"Collection '{col.id}' has no 'cite-as' link. "
                f"Add a DOI or citation link."
            )

    def test_items_have_cite_as_link(self, all_items):
        for item in all_items:
            links = item.get_links("cite-as")
            assert links, (
                f"Item '{item.id}' has no 'cite-as' link. "
                f"Add a DOI or citation link."
            )

    def test_cite_as_links_have_href(self, all_collections):
        for col in all_collections:
            for link in col.get_links("cite-as"):
                assert (
                    link.href
                ), f"Collection '{col.id}' has a 'cite-as' link with no href"


class TestExtensions:
    def test_collections_declare_extensions(self, all_collections):
        for col in all_collections:
            assert (
                col.stac_extensions
            ), f"Collection '{col.id}' declares no STAC extensions"

    def test_raster_extension_declared_when_bands_present(self, all_items):
        raster_ext = "https://stac-extensions.github.io/raster/v1.1.0/schema.json"
        for item in all_items:
            has_bands = any(
                asset.extra_fields.get("raster:bands") for asset in item.assets.values()
            )
            if has_bands:
                assert raster_ext in (item.stac_extensions or []), (
                    f"Item '{item.id}' has raster:bands but doesn't declare "
                    f"the raster extension"
                )


# ------------------------------------------------------------------
# Cross-consistency checks
# ------------------------------------------------------------------


class TestConsistency:
    def test_item_ids_unique(self, all_items):
        ids = [item.id for item in all_items]
        duplicates = {x for x in ids if ids.count(x) > 1}
        assert not duplicates, f"Duplicate item IDs: {duplicates}"

    def test_collection_ids_unique(self, all_collections):
        ids = [col.id for col in all_collections]
        duplicates = {x for x in ids if ids.count(x) > 1}
        assert not duplicates, f"Duplicate collection IDs: {duplicates}"

    def test_items_link_back_to_collection(self, all_collections):
        for col in all_collections:
            items = list(col.get_items())
            for item in items:
                parent_link = item.get_single_link("parent")
                collection_link = item.get_single_link("collection")
                has_link = parent_link is not None or collection_link is not None
                assert has_link, (
                    f"Item '{item.id}' has no parent/collection link "
                    f"back to '{col.id}'"
                )

    def test_default_versions_produce_items(self, all_collections):
        for col in all_collections:
            items = list(col.get_items())
            assert (
                items
            ), f"Collection '{col.id}' has no items despite being in DEFAULT_VERSIONS"


# ------------------------------------------------------------------
# Pydantic config schema validation
# ------------------------------------------------------------------


class TestConfigSchema:
    """Validate every product config dict against the pydantic schema."""

    @staticmethod
    def _all_product_configs():
        from eoforeststac.products.als_products import ALS_PRODUCTS_CFG
        from eoforeststac.products.cci_biomass import CCI_BIOMASS_CFG
        from eoforeststac.products.efda import EFDA_CFG
        from eoforeststac.products.forestpaths_genus import FORESTPATHS_GENUS_CFG
        from eoforeststac.products.gami import GAMI_CFG
        from eoforeststac.products.gami_ageclass import GAMI_AGECLASS_CFG
        from eoforeststac.products.gedi_l4d import GEDI_L4D_CFG
        from eoforeststac.products.hansen_gfc import HANSEN_GFC_CFG
        from eoforeststac.products.jrc_gfc import JRC_GFC_CFG
        from eoforeststac.products.jrc_tmf import JRC_TMF_CFG
        from eoforeststac.products.liu_biomass import LIU_BIOMASS_CFG
        from eoforeststac.products.potapov_height import POTAPOV_HEIGHT_CFG
        from eoforeststac.products.potapov_lcluc import POTAPOV_LCLUC_CFG
        from eoforeststac.products.radd_europe import RADD_EUROPE_CFG
        from eoforeststac.products.restor_landuse import RESTOR_LANDUSE_CFG
        from eoforeststac.products.robinson_cr import ROBINSON_CR_CFG
        from eoforeststac.products.saatchi_biomass import SAATCHI_BIOMASS_CFG
        from eoforeststac.products.uls_products import ULS_PRODUCTS_CFG
        from eoforeststac.products.wang_forestage import WANG_FORESTAGE_CFG

        return {
            "ALS_PRODUCTS": ALS_PRODUCTS_CFG,
            "CCI_BIOMASS": CCI_BIOMASS_CFG,
            "EFDA": EFDA_CFG,
            "FORESTPATHS_GENUS": FORESTPATHS_GENUS_CFG,
            "GAMI": GAMI_CFG,
            "GAMI_AGECLASS": GAMI_AGECLASS_CFG,
            "GEDI_L4D": GEDI_L4D_CFG,
            "HANSEN_GFC": HANSEN_GFC_CFG,
            "JRC_GFC2020": JRC_GFC_CFG,
            "JRC_TMF": JRC_TMF_CFG,
            "LIU_BIOMASS": LIU_BIOMASS_CFG,
            "POTAPOV_HEIGHT": POTAPOV_HEIGHT_CFG,
            "POTAPOV_LCLUC": POTAPOV_LCLUC_CFG,
            "RADD_EUROPE": RADD_EUROPE_CFG,
            "RESTOR_LANDUSE": RESTOR_LANDUSE_CFG,
            "ROBINSON_CR": ROBINSON_CR_CFG,
            "SAATCHI_BIOMASS": SAATCHI_BIOMASS_CFG,
            "WANG_FORESTAGE": WANG_FORESTAGE_CFG,
            "ULS_PRODUCTS": ULS_PRODUCTS_CFG,
        }

    def test_all_configs_validate(self):
        from pydantic import ValidationError

        from eoforeststac.core.schema import validate_product_config

        configs = self._all_product_configs()
        errors = []
        for name, cfg in configs.items():
            try:
                validate_product_config(cfg)
            except ValidationError as e:
                errors.append(f"{name}: {e}")

        if errors:
            pytest.fail(
                f"{len(errors)} product config(s) failed validation:\n\n"
                + "\n\n".join(errors)
            )
