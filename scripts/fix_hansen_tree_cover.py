"""Give Hansen tree cover its own no-data code, so 0 % counts as a real value.

The Hansen GFC store was written with fill value 0 for tree_cover, so every
treeless pixel was read as missing and mean tree cover came out too high.
This sets the fill value to 255 and writes 255 wherever data_mask is 0 (no
observations); 0 % stays 0 elsewhere, including over water. The other
variables are not touched.

Run it where reading the whole layer is fast (mefe3); it is resumable, so an
interrupted run continues from the chunks it has not finished:

    python scripts/fix_hansen_tree_cover.py --dry-run --limit 200  # sample, no writes
    python scripts/fix_hansen_tree_cover.py --workers 16

The overview pyramid was built from the old encoding, and finished levels are
never rebuilt, so delete it and build it again afterwards:

    aws --profile atlaseo-glm --endpoint-url https://s3.gfz.de s3 rm --recursive \
        s3://dog.atlaseo-glm.eo-gridded-data/collections/HANSEN_GFC/HANSEN_GFC_v1.12_pyramid.zarr
    python scripts/build_catalog_pyramids.py --collection HANSEN_GFC
"""

from __future__ import annotations

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import s3fs
import zarr

from eoforeststac.core.config import BASE_S3_URL, S3_ENDPOINT_URL, S3_PROFILE
from eoforeststac.writers.hansen_gfc import TREE_COVER_FILL

STORE = f"{BASE_S3_URL}/HANSEN_GFC/HANSEN_GFC_v1.12.zarr"


def set_fill_value(fs: s3fs.S3FileSystem, root: str) -> None:
    """Declare TREE_COVER_FILL as tree_cover's fill value (metadata only)."""
    path = f"{root}/tree_cover/.zarray"
    meta = json.loads(fs.cat(path))
    if meta["fill_value"] == TREE_COVER_FILL:
        return
    meta["fill_value"] = TREE_COVER_FILL
    fs.pipe(path, json.dumps(meta, indent=4, sort_keys=True).encode())
    zarr.consolidate_metadata(fs.get_mapper(root))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--store", default=STORE)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="Check only this many chunks")
    ap.add_argument(
        "--progress",
        default="fix_hansen_tree_cover.done",
        help="File listing finished chunks, for resuming",
    )
    ap.add_argument("--profile", default=S3_PROFILE)
    args = ap.parse_args()

    fs = s3fs.S3FileSystem(
        profile=args.profile, client_kwargs={"endpoint_url": S3_ENDPOINT_URL}
    )
    root = fs._strip_protocol(args.store).rstrip("/")
    group = zarr.open_group(fs.get_mapper(root), mode="r" if args.dry_run else "r+")
    tree_cover, data_mask = group["tree_cover"], group["data_mask"]
    if tree_cover.shape != data_mask.shape or tree_cover.chunks != data_mask.chunks:
        raise SystemExit("tree_cover and data_mask must share shape and chunks")

    progress = Path(args.progress)
    done = set(progress.read_text().split()) if progress.exists() else set()
    grid = [-(-s // c) for s, c in zip(tree_cover.shape, tree_cover.chunks)]
    todo = [
        (i, j) for i in range(grid[0]) for j in range(grid[1]) if f"{i}.{j}" not in done
    ]
    if args.limit:
        todo = todo[:: max(1, len(todo) // args.limit)][: args.limit]
    print(f"{len(todo)} of {grid[0] * grid[1]} chunks to check")

    if not args.dry_run:
        set_fill_value(fs, root)
        group = zarr.open_group(fs.get_mapper(root), mode="r+")
        tree_cover = group["tree_cover"]

    lock = threading.Lock()
    counts = {"changed": 0, "pixels": 0}

    def fix(i: int, j: int) -> str:
        ci, cj = tree_cover.chunks
        sel = (slice(i * ci, (i + 1) * ci), slice(j * cj, (j + 1) * cj))
        mask = data_mask[sel]
        unobserved = mask == 0
        n = int(unobserved.sum())
        if n:
            block = tree_cover[sel]
            if not (block[unobserved] == TREE_COVER_FILL).all():
                if not args.dry_run:
                    block[unobserved] = TREE_COVER_FILL
                    tree_cover[sel] = block
                with lock:
                    counts["changed"] += 1
                    counts["pixels"] += n
        return f"{i}.{j}"

    log = None if args.dry_run else progress.open("a")
    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(fix, i, j) for i, j in todo]
        for k, fut in enumerate(as_completed(futures), 1):
            key = fut.result()
            if log:
                log.write(key + "\n")
                if k % 500 == 0:
                    log.flush()
            if k % 2000 == 0 or k == len(futures):
                print(
                    f"{k}/{len(futures)} chunks, {counts['changed']} "
                    f"{'to rewrite' if args.dry_run else 'rewritten'}"
                )

    if log:
        log.close()
    verb = "would change" if args.dry_run else "changed"
    print(f"Done: {verb} {counts['pixels']:,} pixels in {counts['changed']} chunks")
    if not args.dry_run:
        print("Next: delete and rebuild the HANSEN_GFC pyramid, then restart titiler")


if __name__ == "__main__":
    main()
