"""Facts the explorer used to guess from file names, written into the catalog.

After the tree is built, every collection gets:

- version links (STAC version extension): ``latest-version`` from the
  collection and each item to the newest item, ``predecessor-version`` and
  ``successor-version`` between items;
- an ``overview`` asset on the newest item for each Zarr asset whose
  visualization pyramid exists on S3 (``<store>_pyramid.zarr``);
- ``gsd`` (metres) on Zarr assets that come in several resolutions, read from
  the asset key ("zarr_0.0833deg", "zarr_10m") when the factory did not set it.

Clients that know these fields need no naming conventions; the explorer still
falls back to the conventions for anything not listed.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Iterable

import pystac

VERSION_EXTENSION = "https://stac-extensions.github.io/version/v1.2.0/schema.json"
_RES = re.compile(r"(\d+(?:\.\d+)?)\s*(deg|km|m)\b", re.I)


def _version_key(item: pystac.Item) -> tuple:
    version = str(item.properties.get("version") or item.id.rsplit("_v", 1)[-1])
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"[._-]", version) if p)


def gsd_from_label(label: str) -> float | None:
    """Metres from a resolution label such as '0.0833deg', '10m' or '1 km'."""
    m = _RES.search(label)
    if not m:
        return None
    value, unit = float(m[1]), m[2].lower()
    return round(
        value * 111_320 if unit == "deg" else value * 1000 if unit == "km" else value, 2
    )


@lru_cache(maxsize=512)
def pyramid_exists(store_href: str) -> bool:
    """Whether ``<store>_pyramid.zarr`` has its root metadata (public HTTPS)."""
    url = (
        store_href.replace("s3://", "https://s3.gfz.de/", 1).removesuffix(".zarr")
        + "_pyramid.zarr/.zattrs"
    )
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, method="HEAD"), timeout=20
        ) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def _zarr_assets(item: pystac.Item) -> list[tuple[str, pystac.Asset]]:
    return [
        (k, a) for k, a in item.assets.items() if a.href.rstrip("/").endswith(".zarr")
    ]


def enrich_collection(
    collection: pystac.Collection, check_pyramids: bool = True
) -> None:
    items = sorted(collection.get_items(), key=_version_key)
    if not items:
        return
    latest = items[-1]

    for rel in ("latest-version",):
        collection.remove_links(rel)
    collection.add_link(
        pystac.Link(
            "latest-version",
            latest,
            media_type="application/json",
            title=f"Latest version ({latest.properties.get('version', '')})",
        )
    )
    for i, item in enumerate(items):
        for rel in ("latest-version", "predecessor-version", "successor-version"):
            item.remove_links(rel)
        if VERSION_EXTENSION not in item.stac_extensions:
            item.stac_extensions.append(VERSION_EXTENSION)
        item.add_link(
            pystac.Link("latest-version", latest, media_type="application/json")
        )
        if i > 0:
            item.add_link(
                pystac.Link(
                    "predecessor-version", items[i - 1], media_type="application/json"
                )
            )
        if i + 1 < len(items):
            item.add_link(
                pystac.Link(
                    "successor-version", items[i + 1], media_type="application/json"
                )
            )

    for item in items:
        zarrs = _zarr_assets(item)
        if len(zarrs) > 1:
            for key, asset in zarrs:
                if "gsd" not in asset.extra_fields:
                    gsd = gsd_from_label(f"{key} {asset.title or ''}")
                    if gsd:
                        asset.extra_fields["gsd"] = gsd

    if check_pyramids:
        for key, asset in _zarr_assets(latest):
            if pyramid_exists(asset.href):
                latest.add_asset(
                    f"{key}_overview",
                    pystac.Asset(
                        href=asset.href.rstrip("/").removesuffix(".zarr")
                        + "_pyramid.zarr",
                        media_type="application/vnd.zarr",
                        title=f"Map overviews of {asset.title or key}",
                        description="Coarsened copies for display (eoforeststac.pyramids); "
                        "level 0 is the data store itself. Not for analysis.",
                        roles=["overview", "visual"],
                    ),
                )


def enrich_tree(
    collections: Iterable[pystac.Collection], check_pyramids: bool = True
) -> None:
    """Enrich every collection that holds items (site collections included)."""
    for collection in collections:
        enrich_collection(collection, check_pyramids=check_pyramids)
