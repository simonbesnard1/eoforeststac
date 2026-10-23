"""Where the lidar footprints are: footprint counts per 1-degree cell.

Built from TileDB's fragment index (each fragment's data-tile bounding boxes
and record counts), so no footprint is read and a run takes minutes. Reading
that index needs permission to list the database bucket, which anonymous
access does not have: run it with credentials that can, e.g. on the
ingestion server:

    AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... \\
        python deploy/footprints/coverage.py --upload --profile atlaseo-glm

It writes coverage_gedi.json and coverage_icesat2.json next to the catalog
(collections/footprints/ on the eoforeststac bucket, public), which the
footprint service serves at /coverage/<provider> and the explorer shows
below the zoom where footprints load. Rerun after the databases grow.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Iterable

import numpy as np

CELL_DEG = 1.0
DATABASES = {
    "gedi": "s3://dog-ext.gedidb.gedi-l2-l4-v002.0/array_uri",
    "icesat2": "s3://dog-ext.icesat2db.icesat2-atl08-v007/array_uri",
}
COVERAGE_PREFIX = "dog.atlaseo-glm.eo-gridded-data/collections/footprints"


def grid_counts(
    boxes: Iterable[tuple[float, float, float, float, float]], cell: float = CELL_DEG
) -> np.ndarray:
    """Spread (lat0, lat1, lon0, lon1, records) boxes over a global grid.

    Each box's records go to the cells it overlaps, in proportion to the
    overlap area. Row 0 is the northernmost band (90 N), column 0 at 180 W.
    """
    rows, cols = int(180 / cell), int(360 / cell)
    counts = np.zeros((rows, cols))
    for lat0, lat1, lon0, lon1, n in boxes:
        if n <= 0:
            continue
        lat0, lat1 = max(-90.0, min(lat0, lat1)), min(90.0, max(lat0, lat1))
        lon0, lon1 = max(-180.0, min(lon0, lon1)), min(180.0, max(lon0, lon1))
        # A point-sized box (one footprint) still covers its cell
        eps = 1e-9
        r0 = int((90 - lat1) // cell)
        r1 = int((90 - lat0 - eps) // cell)
        c0 = int((lon0 + 180) // cell)
        c1 = int((lon1 + 180 - eps) // cell)
        r0, r1 = max(0, min(r0, rows - 1)), max(0, min(r1, rows - 1))
        c0, c1 = max(0, min(c0, cols - 1)), max(0, min(c1, cols - 1))
        # A point exactly on a cell edge belongs to the cell below/right of it
        r1, c1 = max(r1, r0), max(c1, c0)
        area = max((lat1 - lat0) * (lon1 - lon0), 0.0)
        if area == 0 or (r0 == r1 and c0 == c1):
            counts[r0 : r1 + 1, c0 : c1 + 1] += n / ((r1 - r0 + 1) * (c1 - c0 + 1))
            continue
        for r in range(r0, r1 + 1):
            top = 90 - r * cell
            dlat = min(lat1, top) - max(lat0, top - cell)
            for c in range(c0, c1 + 1):
                left = -180 + c * cell
                dlon = min(lon1, left + cell) - max(lon0, left)
                if dlat > 0 and dlon > 0:
                    counts[r, c] += n * dlat * dlon / area
    return counts


def fragment_boxes(uri: str, ctx) -> list[tuple[float, float, float, float, float]]:
    """(lat0, lat1, lon0, lon1, records) per data tile, from the fragment index.

    Data tiles hold about the same number of records, so a fragment's count
    is split evenly over its tile bounding boxes (MBRs); a fragment without
    MBRs counts as one box over its non-empty domain.
    """
    import tiledb

    boxes = []
    for frag in tiledb.array_fragments(uri, include_mbrs=True, ctx=ctx):
        mbrs = getattr(frag, "mbrs", None) or []
        if mbrs:
            per = frag.cell_num / len(mbrs)
            for mbr in mbrs:
                (lat0, lat1), (lon0, lon1) = mbr[0], mbr[1]
                boxes.append((lat0, lat1, lon0, lon1, per))
        else:
            (lat0, lat1), (lon0, lon1) = (
                frag.nonempty_domain[0],
                frag.nonempty_domain[1],
            )
            boxes.append((lat0, lat1, lon0, lon1, frag.cell_num))
    return boxes


def coverage_document(provider: str, counts: np.ndarray) -> dict:
    return {
        "provider": provider,
        "cell_deg": CELL_DEG,
        "origin": [90, -180],
        "rows": counts.shape[0],
        "cols": counts.shape[1],
        "total": int(round(counts.sum())),
        # Rounded counts, row by row from the north; zeros dominate
        "counts": np.rint(counts).astype(int).tolist(),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--provider", choices=list(DATABASES), action="append", default=[])
    ap.add_argument(
        "--upload", action="store_true", help="Write the JSON to S3 (else to ./)"
    )
    ap.add_argument("--profile", help="Profile for writing to the eoforeststac bucket")
    args = ap.parse_args()

    import tiledb

    ctx = tiledb.Ctx(
        {
            "vfs.s3.endpoint_override": os.getenv("FOOTPRINT_S3_HOST", "s3.gfz.de"),
            "vfs.s3.scheme": "https",
            "vfs.s3.use_virtual_addressing": "false",
            "vfs.s3.region": "eu-central-1",
            "vfs.s3.aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID", ""),
            "vfs.s3.aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        }
    )
    fs = None
    if args.upload:
        import s3fs

        fs = s3fs.S3FileSystem(
            profile=args.profile, client_kwargs={"endpoint_url": "https://s3.gfz.de"}
        )
    for provider in args.provider or list(DATABASES):
        counts = grid_counts(fragment_boxes(DATABASES[provider], ctx))
        doc = json.dumps(
            coverage_document(provider, counts), separators=(",", ":")
        ).encode()
        name = f"coverage_{provider}.json"
        if fs is not None:
            fs.pipe_file(
                f"{COVERAGE_PREFIX}/{name}", doc, ContentType="application/json"
            )
            print(
                f"{provider}: {int(counts.sum()):,} footprints -> s3://{COVERAGE_PREFIX}/{name}"
            )
        else:
            with open(name, "wb") as f:
                f.write(doc)
            print(f"{provider}: {int(counts.sum()):,} footprints -> {name}")


if __name__ == "__main__":
    main()
