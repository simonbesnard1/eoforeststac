"""Discover and build visualization pyramids for reviewed STAC products.

Products and aggregation rules live in ``pyramid_manifest.json``. Jobs run
sequentially to avoid saturating Ceph. The single-product builder handles
level-level resume, so rerunning this command is safe.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

_HTTP = httpx.Client(
    timeout=60,
    headers={"User-Agent": "EOForestSTAC-pyramid-builder/1"},
    transport=httpx.HTTPTransport(retries=3),
)


def read_json(url: str, attempts: int = 4) -> dict[str, Any]:
    """Read catalog JSON with retries for occasional object-store timeouts."""
    for attempt in range(1, attempts + 1):
        try:
            response = _HTTP.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            if attempt == attempts:
                raise
            time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"Unable to read {url}")


def child_links(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [link for link in document.get("links", []) if link.get("rel") == "child"]


def discover_collections(catalog_url: str) -> dict[str, dict[str, str]]:
    """Return collection -> Zarr asset key/URL mappings from a static STAC tree."""
    collections: dict[str, dict[str, str]] = {}
    root = read_json(catalog_url)
    for theme_link in child_links(root):
        theme_url = urljoin(catalog_url, theme_link["href"])
        theme = read_json(theme_url)
        for collection_link in child_links(theme):
            collection_url = urljoin(theme_url, collection_link["href"])
            collection = read_json(collection_url)
            item_link = next(
                (link for link in collection.get("links", []) if link.get("rel") == "item"),
                None,
            )
            if not item_link:
                continue
            item = read_json(urljoin(collection_url, item_link["href"]))
            assets = {
                key: asset["href"]
                for key, asset in item.get("assets", {}).items()
                if asset.get("href", "").rstrip("/").endswith(".zarr")
            }
            if assets:
                collections[collection["id"]] = assets
    return collections


def select_products(
    manifest: dict[str, Any],
    discovered: dict[str, dict[str, str]],
    selected: set[str],
) -> list[tuple[dict[str, Any], str]]:
    jobs: list[tuple[dict[str, Any], str]] = []
    for product in manifest["products"]:
        collection_id = product["collection"]
        if selected and collection_id not in selected:
            continue
        if collection_id not in discovered:
            raise RuntimeError(f"Collection not found in STAC: {collection_id}")
        assets = discovered[collection_id]
        asset_key = product.get("asset", "zarr")
        if asset_key not in assets:
            raise RuntimeError(
                f"{collection_id} has no {asset_key!r} asset; available: {sorted(assets)}"
            )
        jobs.append((product, assets[asset_key]))

    missing = selected - {product["collection"] for product, _ in jobs}
    if missing:
        raise RuntimeError(f"Selected collections are absent from manifest: {sorted(missing)}")
    return jobs


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("pyramid_manifest.json"),
    )
    parser.add_argument(
        "--collection",
        action="append",
        default=[],
        help="Build only this collection; repeat for several",
    )
    parser.add_argument("--target-size", type=int, default=8192)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--profile",
        help="Credential profile from ~/.aws/credentials (or set AWS_PROFILE)",
    )
    parser.add_argument("--output-dtype", default="float32")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true", help="List resolved jobs and exit")
    parser.add_argument("--overwrite-incomplete", action="store_true")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with later products and summarize all failures",
    )
    return parser


def main() -> None:
    args = make_parser().parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    print(f"Discovering STAC catalog: {manifest['catalog']}", flush=True)
    discovered = discover_collections(manifest["catalog"])
    jobs = select_products(manifest, discovered, set(args.collection))
    print(f"Resolved {len(jobs)} pyramid job(s)", flush=True)

    builder = Path(__file__).with_name("build_pyramid.py")
    failures: list[tuple[str, int]] = []
    for number, (product, asset_url) in enumerate(jobs, start=1):
        collection_id = product["collection"]
        command = [
            sys.executable,
            str(builder),
            asset_url,
            "--target-size",
            str(args.target_size),
            "--chunk-size",
            str(args.chunk_size),
            "--workers",
            str(args.workers),
            "--output-dtype",
            args.output_dtype,
        ]
        if args.profile:
            command.extend(["--profile", args.profile])
        for variable, reducer in product.get("reducers", {}).items():
            command.extend(["--reducer", f"{variable}={reducer}"])
        if args.dry_run:
            command.append("--dry-run")
        if args.overwrite_incomplete:
            command.append("--overwrite-incomplete")

        print(f"\n[{number}/{len(jobs)}] {collection_id}", flush=True)
        print(" ".join(command), flush=True)
        if args.list:
            continue
        result = subprocess.run(command, check=False)
        if result.returncode:
            failures.append((collection_id, result.returncode))
            if not args.continue_on_error:
                break

    if failures:
        details = ", ".join(f"{name} (exit {code})" for name, code in failures)
        sys.exit(f"Pyramid workflow failed: {details}")
    if not args.list:
        print("\nAll requested pyramid jobs completed.")


if __name__ == "__main__":
    main()
