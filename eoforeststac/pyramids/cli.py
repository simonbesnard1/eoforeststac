"""Build every missing visualization pyramid.

For each data store on S3 (newest version, larger than the target size) it
checks whether a complete pyramid exists, and builds or finishes it if not.
Pyramids the explorer no longer uses (older versions, removed or small
stores) are listed, and deleted with --delete-unused.

    eoforeststac-pyramids --dry-run          # show what would happen
    eoforeststac-pyramids --workers 8 2>&1 | tee pyramids.log

Run it in a persistent session (tmux/screen): global products take hours.
Rerunning is safe; finished levels are kept. Restart titiler on the VM
afterwards so it drops cached datasets.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import s3fs

from eoforeststac.core.config import BASE_S3_URL, S3_ENDPOINT_URL, S3_PROFILE
from eoforeststac.pyramids.build import add_store_display_ranges, build_pyramid
from eoforeststac.pyramids.maintain import plan, remove_pyramid

SYMBOLS = {
    "build": "build ",
    "finish": "finish",
    "rebuild": "rebuild",
    "ok": "ok    ",
    "small": "small ",
    "unfinished-data": "wait  ",
    "delete": "unused",
}
ORDER = ["rebuild", "build", "finish", "ok", "small", "unfinished-data", "delete"]


def make_fs(profile: str | None) -> s3fs.S3FileSystem:
    kwargs: dict = {
        "client_kwargs": {"endpoint_url": S3_ENDPOINT_URL},
        # Long builds meet a busy Ceph: generous timeouts, adaptive retries
        "config_kwargs": {
            "connect_timeout": 60,
            "read_timeout": 300,
            "retries": {"max_attempts": 10, "mode": "adaptive"},
        },
    }
    if os.environ.get("AWS_ACCESS_KEY_ID") and not profile:
        kwargs["key"] = os.environ["AWS_ACCESS_KEY_ID"]
        kwargs["secret"] = os.environ.get("AWS_SECRET_ACCESS_KEY")
    else:
        kwargs["profile"] = profile or os.environ.get("AWS_PROFILE") or S3_PROFILE
    return s3fs.S3FileSystem(**kwargs)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eoforeststac-pyramids",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print the plan")
    parser.add_argument(
        "--collection",
        action="append",
        default=[],
        help="Only this collection (S3 folder, e.g. ALS_BIOMASS_PRODUCTS); repeatable",
    )
    parser.add_argument(
        "--rebuild",
        action="append",
        default=[],
        metavar="NAME",
        help="Delete and rebuild the pyramid of this collection or store "
        "(e.g. HANSEN_GFC after its data was rewritten); repeatable",
    )
    parser.add_argument(
        "--delete-unused", action="store_true", help="Delete pyramids no longer needed"
    )
    parser.add_argument("--workers", type=int, default=4, help="Dask threads per build")
    parser.add_argument("--target-size", type=int, default=8192)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument(
        "--display-ranges",
        action="store_true",
        help="Calculate missing p2-p98 display ranges from the coarsest pyramid "
        "level and write them to native/overview Zarr metadata",
    )
    parser.add_argument(
        "--overwrite-display-ranges",
        action="store_true",
        help="Recalculate display ranges that are already present (implies "
        "--display-ranges)",
    )
    parser.add_argument("--profile", help=f"Credential profile (default {S3_PROFILE})")
    parser.add_argument("--prefix", default=BASE_S3_URL)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = make_parser().parse_args(argv)
    fs = make_fs(args.profile)
    prefix = args.prefix.removeprefix("s3://").rstrip("/")

    print(f"Looking for data stores under s3://{prefix}", flush=True)
    tasks = plan(
        fs,
        prefix,
        target_size=args.target_size,
        collections=set(args.collection) or None,
        rebuild=set(args.rebuild) or None,
    )
    width = max((len(t.label) for t in tasks), default=10)
    for kind in ORDER:
        for t in (x for x in tasks if x.kind == kind):
            print(f"  {SYMBOLS[kind]}  {t.label:{width}s}  {t.reason}")

    work = [t for t in tasks if t.kind in ("rebuild", "build", "finish")]
    unused = [t for t in tasks if t.kind == "delete"]
    if args.dry_run:
        print(f"\nDry run: {len(work)} pyramid(s) to build, {len(unused)} unused.")
        return

    if unused and args.delete_unused:
        for t in unused:
            print(f"Deleting s3://{t.path} ({t.reason})", flush=True)
            remove_pyramid(fs, t.path, prefix)

    failures = []
    for number, t in enumerate(work, start=1):
        print(f"\n[{number}/{len(work)}] {t.kind} {t.label}", flush=True)
        started = time.time()
        try:
            if t.kind == "rebuild":
                if fs.exists(t.path):
                    remove_pyramid(fs, t.path, prefix)
            build_pyramid(
                fs,
                t.store.path,
                t.reducers,
                target_size=args.target_size,
                chunk_size=args.chunk_size,
                workers=args.workers,
                log=lambda m: print(m, flush=True),
            )
            print(f"  took {(time.time() - started) / 60:.0f} min", flush=True)
        except Exception as exc:  # keep going with the other products
            print(f"  FAILED: {type(exc).__name__}: {exc}", flush=True)
            failures.append(t.label)

    if args.display_ranges or args.overwrite_display_ranges:
        range_tasks = [
            t
            for t in tasks
            if t.store is not None
            and t.kind in ("build", "finish", "rebuild", "ok", "small")
            and t.label not in failures
        ]
        print(f"\nWriting display ranges for {len(range_tasks)} store(s)", flush=True)
        for number, t in enumerate(range_tasks, start=1):
            print(f"[{number}/{len(range_tasks)}] {t.label}", flush=True)
            try:
                add_store_display_ranges(
                    fs,
                    t.store.path,
                    t.reducers,
                    pyramid=t.path,
                    overwrite=args.overwrite_display_ranges,
                    log=lambda m: print(m, flush=True),
                )
            except Exception as exc:
                print(f"  FAILED: {type(exc).__name__}: {exc}", flush=True)
                failures.append(t.label)

    if unused and not args.delete_unused:
        print(
            f"\n{len(unused)} unused pyramid(s) kept; delete them with --delete-unused."
        )
    if failures:
        sys.exit(
            f"Failed: {', '.join(failures)} (rerun to retry; finished levels are kept)"
        )
    print("\nAll pyramids are complete. Restart titiler on the VM to use them.")


if __name__ == "__main__":
    main()
