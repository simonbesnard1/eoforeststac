# Visualization pyramids

The explorer draws large stores from map overviews ("pyramids"): coarsened
copies stored next to the native store as `<store>_pyramid.zarr`. The native
store is never modified; it stays level 0.

## Build what is missing

One command, from the installed package, on a server close to GFZ Ceph:

```bash
eoforeststac-pyramids --dry-run            # what exists and what would be built
eoforeststac-pyramids --workers 8 2>&1 | tee pyramids.log
```

(`python -m eoforeststac.pyramids` does the same without the console script.)

For every finished data store on S3 (one with consolidated metadata) it takes
the newest version, skips it if it is at most `--target-size` pixels wide
(8192 by default; it renders fine without overviews), and otherwise checks
its pyramid:

- missing: built;
- partly built (an interrupted run): finished, keeping the completed levels;
- complete: left alone.

It lists the data by scanning the bucket, so stores hidden from the catalog or
nested in site sub-collections (ALS, ULS) are included, and new versions or
countries are picked up automatically. Stores still being written are
reported and skipped until their metadata is consolidated.

Pyramids the explorer no longer uses (older versions, removed or small
stores) are listed as `unused` and deleted only with `--delete-unused`.

Other options:

- `--collection ID`: only this S3 collection folder, e.g. `ALS_BIOMASS_PRODUCTS`;
- `--rebuild NAME`: delete and rebuild a pyramid whose data was rewritten
  (a collection, e.g. `HANSEN_GFC`, or a store name);
- `--profile`: credential profile from `~/.aws/credentials` (default
  `atlaseo-glm`), or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

Run it in tmux or screen: global products take hours. Rerunning is safe.
Afterwards restart titiler on the VM so it drops cached datasets:
`docker compose -f deploy/vm/compose.yaml restart titiler`.

## Reducers

How 2x2 pixels become one is set per variable in the product config, next to
its `analytics` recipe:

```python
"pyramid": {"reducers": {"loss_year": "max", "tree_cover": "mean"}},
```

- `mean`: continuous fields (biomass, height, cover, age);
- `max`: event years and presence flags;
- `first`: classes and masks (the first valid pixel of each 2x2 window).

Variables a config does not list get a reducer inferred from their name and
metadata (`legend`/`flag_values` -> `first`, `year`/`loss`/`gain` -> `max`,
otherwise `mean`). Overviews are for display: averaged uncertainty layers are
not formal error propagation.

Overview values are stored as `float32` in 512 x 512 chunks. Each finished
level gets a `_SUCCESS` marker, which is how an interrupted build resumes.
