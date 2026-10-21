"""Republish one theme of the live STAC catalog from code, leaving the rest untouched.

Unlike ``create_catalog.py`` (which rewrites every theme), this only writes the
theme's own ``catalog.json``, collections and items, in both the internal
(s3:// links) and public (https:// links) variants. JSON files under the theme
that the new tree no longer contains (e.g. items moved into site collections)
are deleted. Zarr stores are never touched: only ``.json`` keys are considered.

Dry run by default; pass ``--apply`` to write and delete.

    python scripts/publish_theme.py --theme als-lidar
    python scripts/publish_theme.py --theme als-lidar --apply
"""

from __future__ import annotations

import argparse
import json

import pystac

from eoforeststac.catalog.root import (
    DEFAULT_VERSIONS,
    THEMES,
    _build_base_tree,
    _iter_collections,
)
from eoforeststac.core.config import BASE_S3_URL, S3_HTTP_BASE
from eoforeststac.core.io import get_fs, get_s3_client, write_json

PUBLIC_WRITE_BASE = BASE_S3_URL.rstrip("/") + "/public"


def _theme_docs(theme_id: str, publish_base: str, write_base: str) -> dict[str, dict]:
    """Return {destination s3 url: JSON dict} for every node of one theme."""
    root, _ = _build_base_tree(
        DEFAULT_VERSIONS, catalog_id="EOForestSTAC", description="EOForestSTAC"
    )
    # Child root/parent links carry the root title; take it from the live root
    live_root = json.loads(
        get_fs(write_base).cat(f"{write_base.rstrip('/')}/catalog.json")
    )
    root.title = live_root.get("title")
    root.normalize_hrefs(publish_base)
    theme = root.get_child(theme_id)
    if theme is None:
        raise SystemExit(f"Unknown theme '{theme_id}'")

    nodes: list[pystac.STACObject] = [theme]
    for col in _iter_collections(theme):
        nodes.append(col)
        nodes.extend(col.get_items())

    docs = {}
    for node in nodes:
        d = node.to_dict()
        # Same as _write_browser_variant: absolute self links for STAC Browser
        for link in d.get("links", []):
            if link.get("rel") == "self":
                link["href"] = node.self_href
        dst = write_base.rstrip("/") + node.self_href[len(publish_base.rstrip("/")) :]
        docs[dst] = d
    return docs


def _root_with_theme_link(root: dict, theme_id: str) -> dict | None:
    """
    Return the root catalog dict with a child link to ``theme_id`` added in
    THEMES order, or None if it is already linked. Nothing else is touched, so
    hand edits to the root survive.
    """
    href = f"./{theme_id}/catalog.json"
    links = root.get("links", [])
    if any(l.get("rel") == "child" and l.get("href") == href for l in links):
        return None
    order = list(THEMES)
    rank = {f"./{t}/catalog.json": i for i, t in enumerate(order)}
    new_link = {
        "rel": "child",
        "href": href,
        "type": "application/json",
        "title": str(THEMES[theme_id]["title"]),
    }
    # Insert before the first child link of a theme that comes later in THEMES
    pos = len(links)
    for i, link in enumerate(links):
        if link.get("rel") == "child" and rank.get(link.get("href"), -1) > order.index(
            theme_id
        ):
            pos = i
            break
    return {**root, "links": [*links[:pos], new_link, *links[pos:]]}


def _live_json_keys(prefix: str) -> set[str]:
    fs = get_fs(prefix)
    if not fs.exists(prefix):
        return set()
    return {
        f"s3://{k}"
        for k in fs.find(prefix)
        if k.endswith(".json") and ".zarr/" not in k
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--theme", required=True, help="Theme id, e.g. als-lidar")
    ap.add_argument(
        "--apply", action="store_true", help="Write and delete (default: dry run)"
    )
    args = ap.parse_args()

    fs = get_fs(BASE_S3_URL)
    variants = [
        ("internal", BASE_S3_URL, BASE_S3_URL),
        ("public", S3_HTTP_BASE, PUBLIC_WRITE_BASE),
    ]
    plan = []  # (variant, action, url, doc)
    for name, publish_base, write_base in variants:
        docs = _theme_docs(args.theme, publish_base, write_base)
        for url, doc in sorted(docs.items()):
            try:
                live = json.loads(fs.cat(url))
            except FileNotFoundError:
                live = None
            action = "new" if live is None else ("same" if live == doc else "update")
            plan.append((name, action, url, doc))
        stale = _live_json_keys(f"{write_base}/{args.theme}") - set(docs)
        plan.extend((name, "delete", url, None) for url in sorted(stale))
        # A new theme also needs a link from the root; written after its files
        root_url = f"{write_base.rstrip('/')}/catalog.json"
        new_root = _root_with_theme_link(json.loads(fs.cat(root_url)), args.theme)
        if new_root is not None:
            plan.append((name, "link", root_url, new_root))

    for name, action, url, _ in plan:
        if action != "same":
            print(f"[{name:8}] {action:6} {url}")
    counts = {
        a: sum(1 for p in plan if p[1] == a)
        for a in ("new", "update", "same", "link", "delete")
    }
    print("\n" + ", ".join(f"{n} {a}" for a, n in counts.items()))

    if not args.apply:
        print("Dry run; re-run with --apply to publish.")
        return

    # Write first, delete after, so the theme is never left with dangling links
    for _, action, url, doc in plan:
        if action in ("new", "update", "link"):
            write_json(url, doc)
    client = get_s3_client()
    for _, action, url, _ in plan:
        if action == "delete":
            bucket, key = url.removeprefix("s3://").split("/", 1)
            client.delete_object(Bucket=bucket, Key=key)
    print("Applied.")


if __name__ == "__main__":
    main()
