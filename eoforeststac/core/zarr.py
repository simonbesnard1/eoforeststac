import re
from typing import Dict, Optional, Sequence

import fsspec
import numpy as np
import zarr
from numcodecs import Blosc

DEFAULT_COMPRESSOR = Blosc(
    cname="zstd",
    clevel=3,
    shuffle=Blosc.BITSHUFFLE,
    blocksize=0,
)

_CHUNK_KEY = re.compile(r"^\d+(\.\d+)*$")


def add_display_range(
    url: str,
    variables: Optional[Sequence[str]] = None,
    max_chunks: int = 256,
    values_per_chunk: int = 50_000,
    seed: int = 0,
    fs: Optional[fsspec.AbstractFileSystem] = None,
    **storage_options,
) -> Dict[str, list]:
    """
    Store a data-derived colour range on each variable of a Zarr v2 store.

    For every floating-point variable with at least two dimensions, the 2nd
    and 98th percentiles of its valid values are written to the variable's
    ``display_range`` attribute (pooled over all other dimensions, e.g. all
    years), and the metadata is reconsolidated. The explorer uses it as the
    legend range for stores too large to measure on the fly.

    Only chunks that are actually stored are read, so sparse stores (most of
    the grid empty) are cheap: at most ``max_chunks`` of them, chosen at
    random, each subsampled at the same rate (``values_per_chunk`` values per
    full chunk).

    Pass ``fs`` to reuse an authenticated filesystem; otherwise one is built
    from ``url`` and ``storage_options``. Returns {variable: [p2, p98]}.
    """
    if fs is None:
        fs, root = fsspec.core.url_to_fs(url, **storage_options)
    else:
        root = fs._strip_protocol(url)
    root = root.rstrip("/")
    group = zarr.open_group(fs.get_mapper(root), mode="r+")
    rng = np.random.default_rng(seed)

    ranges = {}
    for name, arr in group.arrays():
        if variables is not None and name not in variables:
            continue
        if arr.ndim < 2 or np.dtype(arr.dtype).kind != "f":
            continue

        prefix = f"{root}/{name}/"
        keys = [
            k[len(prefix) :].replace("/", ".")
            for k in fs.find(prefix)
            if _CHUNK_KEY.match(k[len(prefix) :].replace("/", "."))
        ]
        if not keys:
            continue
        picked = rng.choice(len(keys), size=min(max_chunks, len(keys)), replace=False)
        # Raw zarr reads keep the fill value (e.g. -9999) as a number
        fill = arr.fill_value
        fills = [float(fill)] if fill is not None and np.isfinite(fill) else []

        samples = []
        for i in picked:
            idx = [int(p) for p in keys[i].split(".")]
            block = np.asarray(
                arr[tuple(slice(j * c, (j + 1) * c) for j, c in zip(idx, arr.chunks))]
            )
            valid = block[np.isfinite(block) & ~np.isin(block, fills)]
            # Same rate for every chunk, so a nearly empty edge chunk does not
            # weigh as much as a full one
            rate = values_per_chunk / block.size
            if rate < 1:
                valid = valid[rng.random(valid.size) < rate]
            samples.append(valid)
        values = np.concatenate(samples) if samples else np.empty(0)
        if values.size == 0:
            continue

        p2, p98 = (float(v) for v in np.percentile(values, [2, 98]))
        arr.attrs.update(
            {
                "display_range": [p2, p98],
                "display_range_method": (
                    "2nd-98th percentile of valid values, sampled from "
                    f"{len(picked)} of {len(keys)} stored chunks"
                ),
            }
        )
        ranges[name] = [p2, p98]

    zarr.consolidate_metadata(fs.get_mapper(root))
    return ranges
