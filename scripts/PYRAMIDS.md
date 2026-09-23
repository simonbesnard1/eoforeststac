# EOForestSTAC visualization-pyramid workflow

This workflow builds resumable map overviews for the reviewed high-resolution
global and pan-tropical products in the public STAC catalog. It writes new
`*_pyramid.zarr` stores alongside the native stores; it never modifies or
duplicates the native level.

The pyramids are visualization products. Their aggregation rules are recorded
in `pyramid_manifest.json` and in the output Zarr metadata:

- `mean`: continuous biomass, canopy height, cover, and forest-age fields;
- `max`: event years and binary presence/event fields;
- `first`: categorical class and mask fields.

Review these policies before a production run. In particular, spatially
averaged uncertainty layers are useful for display but are not formal error
propagation.

## Environment

Use a server close to GFZ Ceph with adequate scratch memory and install the
dedicated, reproducible pyramid environment. It intentionally pins Zarr 2,
which matches the source stores and the pyramid writer:

```bash
micromamba create -f ci/requirements/pyramid.yml
micromamba activate eoforeststac-pyramid
```

Configure credentials that can create objects beside the native stores:

```bash
export AWS_S3_ENDPOINT=https://s3.gfz-potsdam.de
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

Do not place credentials in the repository or command history.

Prefer an existing shared credential profile when one is available. Profiles
are read from `~/.aws/credentials`, so secret values never appear in the
command or repository:

```bash
python scripts/build_catalog_pyramids.py \
  --profile atlaseo-glm \
  --dry-run
```

The equivalent environment setting is `export AWS_PROFILE=atlaseo-glm`.

## Validate before writing

Resolve the catalog jobs without opening the stores:

```bash
python scripts/build_catalog_pyramids.py --list
```

Open every store, validate variable names and print the complete plan without
writing:

```bash
python scripts/build_catalog_pyramids.py --dry-run
```

Test one product first:

```bash
python scripts/build_catalog_pyramids.py \
  --collection CCI_BIOMASS \
  --workers 8
```

Then run the reviewed catalog workflow in a persistent terminal session:

```bash
python scripts/build_catalog_pyramids.py \
  --workers 8 \
  --continue-on-error 2>&1 | tee pyramid-build.log
```

The runner processes products sequentially. Within a product, Dask uses the
configured number of threads. Each completed level contains `_SUCCESS`.
Rerunning the same command skips completed levels and continues from the first
unfinished one.

If a process is interrupted during a level, inspect the output and explicitly
replace only incomplete levels with:

```bash
python scripts/build_catalog_pyramids.py \
  --workers 8 \
  --overwrite-incomplete
```

## Sizing

By default, levels are added until both spatial dimensions of the coarsest
level are at most approximately 8192 pixels. Overview values are stored as
`float32`, cutting their logical size in half relative to decoded `float64`
source arrays. Change these defaults only after testing:

```bash
python scripts/build_catalog_pyramids.py \
  --target-size 4096 \
  --chunk-size 512 \
  --workers 8
```

Monitor memory, Ceph request rate, and output growth during the first product.
Start with four to eight workers; additional threads may increase object-store
contention without improving throughput.
