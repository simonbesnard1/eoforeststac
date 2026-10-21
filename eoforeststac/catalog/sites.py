"""Shared builders for multi-site products (ALS, ULS, ...).

These products are exposed as a parent collection with one child collection
per site/country, each holding its own versioned items:

    ALS_PRODUCTS                (parent collection, no items)
      └─ ALS_SPAIN_PNOA         (site collection)
           ├─ ALS_SPAIN_PNOA_v1.0
           └─ ALS_SPAIN_PNOA_v1.1
"""

from typing import Mapping, Optional

import pystac

from eoforeststac.catalog.factory import _build_raster_bands, create_collection
from eoforeststac.core.assets import create_zarr_asset


def create_site_collection(cfg: dict, site_id: str) -> pystac.Collection:
    """Build the child collection for one site of a multi-site product."""
    reg = cfg["regions"][site_id]
    site_cfg = {
        **cfg,
        "id": reg["zarr_name"],
        "title": f"{cfg['short_title']} – {reg['label']}",
        "description": reg["description"],
        "bbox": reg["bbox"],
        "geometry": reg["geometry"],
        "start_datetime": reg["start_datetime"],
        "end_datetime": reg["end_datetime"],
        "collection_href": f"{cfg['base_path']}/{reg['zarr_name']}/collection.json",
        "summaries": {**cfg["summaries"], "proj:epsg": [reg["proj_epsg"]]},
    }
    col = create_collection(site_cfg)
    col.extra_fields["site"] = {"id": site_id, "label": reg["label"]}
    return col


def create_site_item(
    cfg: dict,
    site_id: str,
    version: str,
    resolutions: Optional[Mapping[str, dict]] = None,
) -> pystac.Item:
    """
    Build one versioned item for a site.

    With ``resolutions``, the item gets one ``zarr_{res}`` asset per resolution;
    otherwise a single ``zarr`` asset.
    """
    reg = cfg["regions"][site_id]
    item_id = f"{reg['zarr_name']}_v{version}"

    properties = {
        "product_name": cfg["title"],
        "version": version,
        "region": site_id,
        "start_datetime": reg["start_datetime"].isoformat(),
        "end_datetime": reg["end_datetime"].isoformat(),
        "proj:epsg": reg["proj_epsg"],
        "variables": cfg["summaries"]["variables"],
        "spatial_resolutions": list(resolutions) if resolutions else ["10m"],
    }

    item = pystac.Item(
        id=item_id,
        geometry=reg["geometry"],
        bbox=reg["bbox"],
        datetime=reg["end_datetime"],
        properties=properties,
        href=f"{cfg['base_path']}/{reg['zarr_name']}/{item_id}/item.json",
        stac_extensions=cfg.get("stac_extensions", []),
    )

    if resolutions:
        all_bands = _build_raster_bands(cfg)
        for res, res_meta in resolutions.items():
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
    else:
        item.add_asset(
            "zarr",
            create_zarr_asset(
                href=f"{cfg['base_path']}/{item_id}",
                title="Zarr dataset",
                roles=["data"],
                description=(
                    f"Cloud-optimized Zarr store at 10 m resolution for "
                    f"{reg['label']} (EPSG:{reg['proj_epsg']})."
                ),
            ),
        )

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

    return item


def update_extent_from_sites(col: pystac.Collection) -> None:
    """
    Set a parent collection's extent from its site collections.

    The first bbox is the union; the following ones are the individual sites,
    as recommended by the STAC spec for collections with disjoint subsets.
    """
    sites = [c for c in col.get_children() if isinstance(c, pystac.Collection)]
    if not sites:
        return
    site_bboxes = [s.extent.spatial.bboxes[0] for s in sites]
    union = [
        min(b[0] for b in site_bboxes),
        min(b[1] for b in site_bboxes),
        max(b[2] for b in site_bboxes),
        max(b[3] for b in site_bboxes),
    ]
    intervals = [s.extent.temporal.intervals[0] for s in sites]
    starts = [i[0] for i in intervals if i[0] is not None]
    ends = [i[1] for i in intervals if i[1] is not None]
    col.extent = pystac.Extent(
        spatial=pystac.SpatialExtent([union, *site_bboxes]),
        temporal=pystac.TemporalExtent(
            [[min(starts) if starts else None, max(ends) if ends else None]]
        ),
    )
