"""Write ALS biomass country stores to S3, one aligned Zarr per country.

Each ``<data-root>/<Country>/`` folder holds ``*_YYYY_biomass.tif`` files; the
country's CRS is read from them. Countries must be registered in
``products/als_biomass_products.py`` (REGIONS) so the catalog points at the
written store.

    python scripts/write_als_biomass.py --data-root /path/to/Biomass_maps_v1
    python scripts/write_als_biomass.py --data-root ... --country Finland --country Sweden
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import rasterio

from eoforeststac.core.config import S3_ENDPOINT_URL, S3_PROFILE
from eoforeststac.products.als_biomass_products import REGIONS
from eoforeststac.writers.als_biomass_products import ALSBiomassProductsWriter

BUCKET = "dog.atlaseo-glm.eo-gridded-data"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--data-root", required=True, help="Folder with one sub-folder per country"
    )
    ap.add_argument(
        "--country", action="append", default=[], help="Only this country; repeatable"
    )
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--profile", default=S3_PROFILE)
    args = ap.parse_args()

    root = Path(args.data_root)
    countries = args.country or sorted(p.name for p in root.iterdir() if p.is_dir())
    unknown = [c for c in countries if c.lower() not in REGIONS]
    if unknown:
        raise SystemExit(f"Not in REGIONS (add them to the catalog first): {unknown}")

    writer = ALSBiomassProductsWriter(
        endpoint_url=S3_ENDPOINT_URL,
        bucket=BUCKET,
        profile=args.profile,
        connect_timeout=60,
        read_timeout=300,
    )
    for country in countries:
        tifs = writer.find_yearly_tifs(root / country)
        with rasterio.open(next(iter(tifs.values()))) as src:
            crs = f"EPSG:{src.crs.to_epsg()}"
        expected = REGIONS[country.lower()]["proj_epsg"]
        if crs != f"EPSG:{expected}":
            raise SystemExit(f"{country}: data is {crs}, catalog says EPSG:{expected}")

        t0 = time.time()
        out = writer.write(
            root / country, country=country, crs=crs, version=args.version
        )
        print(
            f"{country}: wrote {out} in {(time.time() - t0) / 60:.1f} min\n", flush=True
        )


if __name__ == "__main__":
    main()
