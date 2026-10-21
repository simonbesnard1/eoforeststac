"""Add a data-derived legend range (display_range attribute) to Zarr stores on S3.

The explorer measures p2-p98 on the fly only for stores small enough to read
at once; larger ones (ALS 1 m, ALS biomass countries) need it stored. This
writes ``display_range`` = [p2, p98] on every floating-point variable and
reconsolidates the metadata. Data is not modified.

    python scripts/add_display_range.py --collection ALS_BIOMASS_PRODUCTS
    python scripts/add_display_range.py s3://.../ALS_PRODUCTS/ALS_SPAIN_PNOA_1m_v1.0.zarr
"""

from __future__ import annotations

import argparse

import s3fs

from eoforeststac.core.config import BASE_S3_URL, S3_ENDPOINT_URL, S3_PROFILE
from eoforeststac.core.zarr import add_display_range


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stores", nargs="*", help="s3:// URLs of Zarr stores")
    ap.add_argument(
        "--collection",
        action="append",
        default=[],
        help="Process every *.zarr under collections/<id>/; repeatable",
    )
    ap.add_argument("--profile", default=S3_PROFILE)
    args = ap.parse_args()

    fs = s3fs.S3FileSystem(
        profile=args.profile, client_kwargs={"endpoint_url": S3_ENDPOINT_URL}
    )
    stores = list(args.stores)
    for col in args.collection:
        prefix = f"{BASE_S3_URL}/{col}"
        stores += [f"s3://{p}" for p in sorted(fs.ls(prefix)) if p.endswith(".zarr")]
    if not stores:
        raise SystemExit("Nothing to do: pass store URLs or --collection")

    for url in stores:
        if not fs.exists(f"{url}/.zmetadata"):
            print(f"skip {url}: not consolidated (still being written?)")
            continue
        ranges = add_display_range(url, fs=fs)
        print(
            f"{url}: "
            + ", ".join(f"{v} {lo:.4g}-{hi:.4g}" for v, (lo, hi) in ranges.items())
        )


if __name__ == "__main__":
    main()
