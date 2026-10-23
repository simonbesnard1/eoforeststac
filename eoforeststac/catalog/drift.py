"""Does the live catalog match what the code generates?

Builds every theme from code, exactly as ``scripts/publish_theme.py`` would
publish it, and compares each document with the live one over public HTTPS
(no credentials needed). Reports documents that differ, are missing live, or
exist live but not in code, and exits with status 1 when there is drift.

    python -m eoforeststac.catalog.drift
    python -m eoforeststac.catalog.drift --theme biomass-carbon --variant public

Drift means the live catalog was edited by hand, or the code changed and was
not published: publish with ``scripts/publish_theme.py --theme <id> --apply``.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

import pystac

from eoforeststac.catalog.root import (
    DEFAULT_VERSIONS,
    INTERNAL_THEMES,
    THEMES,
    _build_base_tree,
    _iter_collections,
)
from eoforeststac.core.config import BASE_S3_URL, S3_HTTP_BASE, S3_HTTP_PUBLIC_BASE

# publish base (hrefs inside documents) -> where the documents live over HTTPS
VARIANTS = {
    "public": (S3_HTTP_PUBLIC_BASE, S3_HTTP_PUBLIC_BASE),
    "internal": (BASE_S3_URL, S3_HTTP_BASE),
}


def _get(url: str) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return None
        raise


def generated_docs(theme_id: str, publish_base: str, http_base: str) -> dict[str, dict]:
    """{https url: document} for one theme, as publish_theme.py writes it."""
    root, _ = _build_base_tree(
        DEFAULT_VERSIONS, catalog_id="EOForestSTAC", description="EOForestSTAC"
    )
    live_root = _get(f"{http_base.rstrip('/')}/catalog.json") or {}
    root.title = live_root.get("title")
    root.normalize_hrefs(publish_base)
    theme = root.get_child(theme_id)
    nodes: list[pystac.STACObject] = [theme]
    for col in _iter_collections(theme):
        nodes.append(col)
        nodes.extend(col.get_items())
    docs = {}
    for node in nodes:
        d = json.loads(json.dumps(node.to_dict()))  # int dict keys -> str, as published
        for link in d.get("links", []):
            if link.get("rel") == "self":
                link["href"] = node.self_href
        docs[
            http_base.rstrip("/") + node.self_href[len(publish_base.rstrip("/")) :]
        ] = d
    return docs


def differences(new, live, path: str = "") -> list[str]:
    if isinstance(new, dict) and isinstance(live, dict):
        out = []
        for key in sorted(set(new) | set(live)):
            if key not in live:
                out.append(f"{path}/{key}: only in code")
            elif key not in new:
                out.append(f"{path}/{key}: only live")
            else:
                out += differences(new[key], live[key], f"{path}/{key}")
        return out
    if isinstance(new, list) and isinstance(live, list) and len(new) == len(live):
        return [
            d
            for i, (a, b) in enumerate(zip(new, live))
            for d in differences(a, b, f"{path}[{i}]")
        ]
    if json.dumps(new, sort_keys=True) != json.dumps(live, sort_keys=True):
        return [f"{path}: live {json.dumps(live)[:70]} -> code {json.dumps(new)[:70]}"]
    return []


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--theme", action="append", default=[], help="Only this theme; repeatable"
    )
    ap.add_argument("--variant", choices=list(VARIANTS), action="append", default=[])
    args = ap.parse_args(argv)

    drift = 0
    for variant in args.variant or list(VARIANTS):
        publish_base, http_base = VARIANTS[variant]
        for theme in args.theme or list(THEMES):
            if variant == "public" and theme in INTERNAL_THEMES:
                # Must not be public: neither linked from the root nor present
                root = _get(f"{http_base.rstrip('/')}/catalog.json") or {}
                linked = any(
                    l.get("rel") == "child" and f"/{theme}/" in l.get("href", "")
                    for l in root.get("links", [])
                )
                if linked or _get(f"{http_base.rstrip('/')}/{theme}/catalog.json"):
                    print(f"[public] internal theme is public: {theme}")
                    drift += 1
                continue
            docs = generated_docs(theme, publish_base, http_base)
            for url, new in docs.items():
                live = _get(url)
                name = url[len(http_base.rstrip("/")) + 1 :]
                if live is None:
                    print(f"[{variant}] missing live: {name}")
                    drift += 1
                    continue
                diff = differences(new, live)
                if diff:
                    drift += 1
                    print(f"[{variant}] differs: {name}")
                    for line in diff[:8]:
                        print(f"      {line}")
                    if len(diff) > 8:
                        print(f"      ... {len(diff) - 8} more")
    if drift:
        print(
            f"\n{drift} document(s) differ from the code. Publish with "
            "scripts/publish_theme.py --theme <id> --apply."
        )
        sys.exit(1)
    print("The live catalog matches the code.")


if __name__ == "__main__":
    main()
