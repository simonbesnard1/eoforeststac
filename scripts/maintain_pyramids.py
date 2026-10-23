"""Bring the visualization pyramids on S3 in line with the manifest.

Compares every ``*_pyramid.zarr`` under the catalog prefix with what the
explorer needs: one complete pyramid for the newest version of each product
in ``pyramid_manifest.json``. Each pyramid gets one action:

  ok        complete and built from the current source
  build     missing
  resume    some levels unfinished (completed levels are kept)
  rebuild   reducers changed, or the source encoding changed since the build
  check     the source store changed after the build, and the pyramid is too
            old to tell whether that matters; pass --rebuild or --accept
  delete    not needed: an older version, a product no longer in the
            manifest, or a pyramid whose native store is gone

Without --apply it only prints the plan. With --apply it deletes, rebuilds,
builds and resumes, one product at a time (build_pyramid.py does the work),
and records the source fingerprint on complete pyramids that lack one, so
later source changes are detected exactly.

    python scripts/maintain_pyramids.py                      # plan only
    python scripts/maintain_pyramids.py --apply --workers 8 2>&1 | tee pyramids.log
    python scripts/maintain_pyramids.py --apply --rebuild HANSEN_GFC
    python scripts/maintain_pyramids.py --apply --accept POTAPOV_HEIGHT

Run it in a persistent session (tmux/screen): a global build takes hours.
Rerunning is safe; it continues where it stopped.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import s3fs

from build_catalog_pyramids import discover_collections, pyramid_command
from build_pyramid import make_s3, normalize_s3_url, s3_path, source_fingerprint

CATALOG_PREFIX = "dog.atlaseo-glm.eo-gridded-data/collections"


@dataclass
class Pyramid:
    path: str  # bucket/key of the *_pyramid.zarr store
    levels: list[str] = field(default_factory=list)
    complete: list[str] = field(default_factory=list)
    reducers: dict[str, str] | None = None
    fingerprint: str | None = None
    source: str | None = None
    built: Any = None  # time of the newest _SUCCESS marker

    @property
    def finished(self) -> bool:
        return bool(self.levels) and self.complete == self.levels


@dataclass
class Action:
    kind: str
    collection: str
    pyramid: str
    reason: str
    product: dict[str, Any] | None = None
    asset_url: str | None = None


def inventory(s3: s3fs.S3FileSystem, prefix: str) -> dict[str, Pyramid]:
    """Every pyramid store under the prefix, with its level status."""
    found: dict[str, Pyramid] = {}
    for folder in s3.ls(prefix, detail=False):
        try:
            entries = s3.ls(folder, detail=False)
        except (FileNotFoundError, NotADirectoryError):
            continue
        for path in entries:
            path = path.lstrip("/")  # some filesystems list "/bucket/key"
            if not path.endswith("_pyramid.zarr"):
                continue
            pyr = Pyramid(path)
            try:
                multiscales = json.loads(s3.cat(f"{path}/.zattrs"))["multiscales"][0]
            except (FileNotFoundError, KeyError, IndexError, ValueError):
                found[path] = pyr  # no root metadata: treat as unfinished
                continue
            meta = multiscales.get("metadata", {})
            pyr.levels = [d["path"] for d in multiscales.get("datasets", [])]
            pyr.reducers = meta.get("reducers")
            pyr.fingerprint = meta.get("source_fingerprint")
            pyr.source = meta.get("native_source")
            for level in pyr.levels:
                marker = f"{path}/{level}/_SUCCESS"
                if s3.exists(marker):
                    pyr.complete.append(level)
                    modified = s3.info(marker).get("LastModified")
                    if modified and (pyr.built is None or modified > pyr.built):
                        pyr.built = modified
            found[path] = pyr
    return found


def source_changed_after(s3: s3fs.S3FileSystem, source: str, built: Any) -> bool:
    try:
        modified = s3.info(f"{s3_path(source)}/.zmetadata").get("LastModified")
    except FileNotFoundError:
        return False
    return bool(built and modified and modified > built)


def plan(
    s3: s3fs.S3FileSystem,
    manifest: dict[str, Any],
    discovered: dict[str, dict[str, str]],
    pyramids: dict[str, Pyramid],
    rebuild: set[str],
    accept: set[str],
) -> list[Action]:
    actions: list[Action] = []
    wanted: set[str] = set()
    for product in manifest["products"]:
        cid = product["collection"]
        asset_url = discovered.get(cid, {}).get(product.get("asset", "zarr"))
        if not asset_url:
            print(f"warning: {cid} has no Zarr asset in the catalog; skipped")
            continue
        source = normalize_s3_url(asset_url)
        target = s3_path(source).removesuffix(".zarr") + "_pyramid.zarr"
        wanted.add(target)
        pyr = pyramids.get(target)
        reducers = product.get("reducers", {})

        def act(kind: str, reason: str) -> None:
            actions.append(Action(kind, cid, target, reason, product, asset_url))

        if pyr is None:
            act("build", "no pyramid yet")
            continue
        if cid in rebuild:
            act("rebuild", "requested with --rebuild")
            continue
        if pyr.reducers is not None and pyr.reducers != reducers:
            act("rebuild", f"reducers changed: {pyr.reducers} -> {reducers}")
            continue
        if pyr.fingerprint:
            current = source_fingerprint(s3, source, list(reducers))
            if current != pyr.fingerprint:
                act("rebuild", "source encoding changed since the build")
                continue
        elif cid not in accept and source_changed_after(s3, source, pyr.built):
            act("check", "source store changed after the pyramid was built")
            continue
        if not pyr.finished:
            done = f"{len(pyr.complete)}/{len(pyr.levels) or '?'}"
            act("resume", f"{done} levels complete")
        elif not pyr.fingerprint:
            act("ok", "complete; fingerprint will be recorded")
        else:
            act("ok", "complete")

    newest = {
        s3_path(normalize_s3_url(a))
        for assets in discovered.values()
        for a in assets.values()
    }
    for path, pyr in sorted(pyramids.items()):
        if path in wanted:
            continue
        native = path.removesuffix("_pyramid.zarr") + ".zarr"
        if not s3.exists(native):
            reason = "native store is gone"
        elif native in newest:
            reason = "product is not in the pyramid manifest"
        else:
            reason = "older version; the explorer shows the newest"
        actions.append(Action("delete", Path(native).stem, path, reason))
    return actions


ORDER = ["delete", "rebuild", "build", "resume", "check", "ok"]


def print_plan(actions: list[Action]) -> None:
    width = max((len(a.collection) for a in actions), default=10)
    for kind in ORDER:
        for a in (x for x in actions if x.kind == kind):
            print(f"  {a.kind:8s} {a.collection:{width}s}  {a.reason}")
            if kind == "delete":
                print(f"  {'':8s} {'':{width}s}  s3://{a.pyramid}")


def record_fingerprint(s3: s3fs.S3FileSystem, action: Action) -> None:
    source = normalize_s3_url(action.asset_url)
    fingerprint = source_fingerprint(s3, source, list(action.product["reducers"]))
    path = f"{action.pyramid}/.zattrs"
    attrs = json.loads(s3.cat(path))
    attrs["multiscales"][0].setdefault("metadata", {})[
        "source_fingerprint"
    ] = fingerprint
    s3.pipe(path, json.dumps(attrs, indent=4).encode())


def remove(s3: s3fs.S3FileSystem, path: str, prefix: str) -> None:
    # Never touch anything but a pyramid store under the catalog prefix
    if not (path.startswith(prefix + "/") and path.endswith("_pyramid.zarr")):
        raise RuntimeError(f"Refusing to delete {path}")
    s3.rm(path, recursive=True)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("pyramid_manifest.json"),
    )
    parser.add_argument("--prefix", default=CATALOG_PREFIX)
    parser.add_argument("--apply", action="store_true", help="Carry out the plan")
    parser.add_argument(
        "--rebuild",
        action="append",
        default=[],
        metavar="COLLECTION",
        help="Delete and rebuild this product's pyramid; repeatable",
    )
    parser.add_argument(
        "--accept",
        action="append",
        default=[],
        metavar="COLLECTION",
        help="Keep this product's pyramid although its source changed "
        "(e.g. only attributes were edited); repeatable",
    )
    parser.add_argument(
        "--keep-unused",
        action="store_true",
        help="Do not delete pyramids the explorer no longer uses",
    )
    parser.add_argument("--target-size", type=int, default=8192)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output-dtype", default="float32")
    parser.add_argument(
        "--profile",
        help="Credential profile from ~/.aws/credentials (or set AWS_PROFILE)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with later products and summarize all failures",
    )
    return parser


def main() -> None:
    args = make_parser().parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    known = {p["collection"] for p in manifest["products"]}
    unknown = (set(args.rebuild) | set(args.accept)) - known
    if unknown:
        sys.exit(f"Not in the pyramid manifest: {sorted(unknown)}")

    s3 = make_s3(args.profile)
    print(f"Reading the catalog: {manifest['catalog']}", flush=True)
    discovered = discover_collections(manifest["catalog"])
    print(f"Listing pyramids under s3://{args.prefix}", flush=True)
    pyramids = inventory(s3, args.prefix)
    actions = plan(
        s3, manifest, discovered, pyramids, set(args.rebuild), set(args.accept)
    )
    if args.keep_unused:
        actions = [a for a in actions if a.kind != "delete"]

    print(f"\nPlan ({len(pyramids)} pyramids on S3):")
    print_plan(actions)
    if not args.apply:
        print("\nNothing changed. Rerun with --apply to carry out the plan.")
        return

    failures: list[str] = []
    for a in (x for x in actions if x.kind == "delete"):
        print(f"\nDeleting s3://{a.pyramid} ({a.reason})", flush=True)
        remove(s3, a.pyramid, args.prefix)

    work = [
        a for kind in ("rebuild", "build", "resume") for a in actions if a.kind == kind
    ]
    for number, a in enumerate(work, start=1):
        print(
            f"\n[{number}/{len(work)}] {a.kind} {a.collection}: {a.reason}", flush=True
        )
        if a.kind == "rebuild":
            remove(s3, a.pyramid, args.prefix)
        command = pyramid_command(a.product, a.asset_url, args)
        if a.kind == "resume":
            command.append("--overwrite-incomplete")
        print(" ".join(command), flush=True)
        if subprocess.run(command, check=False).returncode:
            failures.append(a.collection)
            if not args.continue_on_error:
                break

    for a in (x for x in actions if x.kind == "ok" and "recorded" in x.reason):
        record_fingerprint(s3, a)
        print(f"Recorded the source fingerprint of {a.collection}")

    checks = [a.collection for a in actions if a.kind == "check"]
    if checks:
        print(
            "\nStill to decide (source changed after the build): "
            + ", ".join(checks)
            + "\n  --rebuild <id> if its data or encoding changed,"
            " --accept <id> if only attributes were edited."
        )
    if failures:
        sys.exit(f"Failed: {', '.join(failures)}")
    print("\nDone. Restart titiler on the VM so it drops cached datasets.")


if __name__ == "__main__":
    main()
