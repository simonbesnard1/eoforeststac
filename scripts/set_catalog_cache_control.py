"""Set Cache-Control: no-cache on every catalog JSON already on S3.

Objects written before core/io.py set the header are cached heuristically by
browsers (for hours, if unchanged for days), so STAC Browser keeps following
links that a republish removed. This rewrites only the object metadata, in
place, keeping Content-Type application/json; contents are untouched. Zarr
stores are skipped.

    python scripts/set_catalog_cache_control.py            # dry run
    python scripts/set_catalog_cache_control.py --apply
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor

from eoforeststac.core.config import BASE_S3_URL
from eoforeststac.core.io import get_fs, get_s3_client


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    bucket, prefix = BASE_S3_URL.removeprefix("s3://").split("/", 1)
    fs = get_fs(BASE_S3_URL)

    # Walk folder by folder, never descending into Zarr stores (millions of
    # chunk keys under collections/)
    keys, todo_dirs = [], [f"{bucket}/{prefix}"]
    while todo_dirs:
        for entry in fs.ls(todo_dirs.pop(), detail=True):
            name = entry["name"]
            if entry["type"] == "directory":
                if not name.endswith(".zarr"):
                    todo_dirs.append(name)
            elif name.endswith(".json"):
                keys.append(name.split("/", 1)[1])
    client = get_s3_client()

    def needs_update(key: str) -> bool:
        head = client.head_object(Bucket=bucket, Key=key)
        return head.get("CacheControl") != "no-cache"

    with ThreadPoolExecutor(16) as ex:
        todo = [k for k, n in zip(keys, ex.map(needs_update, keys)) if n]
    print(f"{len(todo)} of {len(keys)} catalog JSON files need Cache-Control: no-cache")
    if not args.apply:
        print("Dry run; re-run with --apply.")
        return

    def update(key: str) -> None:
        client.copy_object(
            Bucket=bucket,
            Key=key,
            CopySource={"Bucket": bucket, "Key": key},
            MetadataDirective="REPLACE",
            ContentType="application/json",
            CacheControl="no-cache",
        )

    with ThreadPoolExecutor(16) as ex:
        list(ex.map(update, todo))
    print("Applied.")


if __name__ == "__main__":
    main()
