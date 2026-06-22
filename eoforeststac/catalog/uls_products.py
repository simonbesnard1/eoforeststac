import pystac

from eoforeststac.catalog.factory import _build_raster_bands, create_collection
from eoforeststac.core.assets import create_zarr_asset
from eoforeststac.products.uls_products import (
    ULS_PRODUCTS_CFG,
    ULS_RESOLUTIONS,
    REGIONS,
)


def create_uls_products_collection():
    return create_collection(ULS_PRODUCTS_CFG)


def create_uls_products_item(version: str) -> list[pystac.Item]:
    """Return one STAC Item per site, each with one Zarr asset per resolution."""
    cfg = ULS_PRODUCTS_CFG
    items = []
    for region_id, reg in REGIONS.items():
        item_id = f"{reg['zarr_name']}_v{version}"
        item_href = f"{cfg['base_path']}/{item_id}/item.json"

        properties = {
            "product_name": cfg["title"],
            "version": version,
            "region": region_id,
            "start_datetime": reg["start_datetime"].isoformat(),
            "end_datetime": reg["end_datetime"].isoformat(),
            "proj:epsg": reg["proj_epsg"],
            "variables": cfg["summaries"]["variables"],
            "spatial_resolutions": list(ULS_RESOLUTIONS.keys()),
        }

        item = pystac.Item(
            id=item_id,
            geometry=reg["geometry"],
            bbox=reg["bbox"],
            datetime=reg["end_datetime"],
            properties=properties,
            href=item_href,
            stac_extensions=cfg.get("stac_extensions", []),
        )

        all_bands = _build_raster_bands(cfg)
        for res, res_meta in ULS_RESOLUTIONS.items():
            res_vars = set(res_meta["variables"])
            res_bands = [b for b in all_bands if b["name"] in res_vars]
            asset = create_zarr_asset(
                href=f"{cfg['base_path']}/{reg['zarr_name']}_{res}_v{version}.zarr",
                title=f"{res}",
                roles=["data"],
                description=(
                    f"Cloud-optimized Zarr store at {res} resolution for "
                    f"{reg['label']} (EPSG:{reg['proj_epsg']}). "
                    f"Variables: {', '.join(res_meta['variables'])}."
                ),
            )
            if res_bands:
                asset.extra_fields["raster:bands"] = res_bands
            item.add_asset(f"zarr_{res}", asset)

        for link_cfg in cfg.get("links", []):
            if link_cfg["rel"] in ["cite-as", "about", "license"]:
                item.add_link(
                    pystac.Link(
                        rel=link_cfg["rel"],
                        target=link_cfg["href"],
                        media_type=link_cfg.get("type"),
                        title=link_cfg.get("title"),
                    )
                )

        items.append(item)

    return items
