#!/usr/bin/env python
from datetime import datetime

import xarray as xr
import rioxarray
import s3fs
#from zarr.codecs import BloscCodec

# ---------------- USER CONFIG ---------------- #

# Years to ingest from AEF
YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024]

# Source AEF bucket (public)
AEF_BUCKET = "us-west-2.opendata.source.coop"
AEF_PREFIX = "tge-labs/aef/v1/annual"

# Target GFZ S3 bucket
TARGET_BUCKET = "dog.atlaseo-glm.eo-gridded-data"
TARGET_PREFIX = "collections/AEF/v1"  # will create AEF_v1_{zone}.zarr under this

# Chunking & data model
CHUNK_X = 1024
CHUNK_Y = 1024
N_FEATURES = 64  # A00–A63
FEATURE_NAMES = [f"A{i:02d}" for i in range(N_FEATURES)]
FILL_VALUE = -128
CRS = "EPSG:32610"  # true for these UTM tiles (zone-specific, but here we label as generic UTM WGS84)

# ---------------- HELPERS ---------------- #

def make_source_fs():
    """S3 filesystem for public AEF bucket."""
    return s3fs.S3FileSystem(
        anon=True,
        client_kwargs={"region_name": "us-west-2"}
    )


def make_target_fs():
    """S3 filesystem for GFZ bucket."""
    return s3fs.S3FileSystem(
        key="",
        secret="IrePH6qa1irAvHFamRFhr7L2EsKPHkiYPqxULCuS",
        client_kwargs={
            "endpoint_url": "https://s3.gfz-potsdam.de",
            "region_name": "eu-central-1",
        },
    )


def list_zones(fs_src):
    """
    Discover all zones available for the first year in YEARS.
    Returns e.g. ["1S", "1N", "2S", "2N", ...]
    """
    year0 = YEARS[0]
    base = f"{AEF_BUCKET}/{AEF_PREFIX}/{year0}"
    entries = fs_src.ls(base, detail=False)
    zones = [p.split("/")[-1] for p in entries]
    zones = sorted(zones)
    return zones


def list_vrt_tiles_for_year_zone(fs_src, year, zone):
    """
    List all .vrt tiles for a given year and zone in AEF bucket.
    Returns full S3 paths WITHOUT 's3://' prefix.
    """
    prefix = f"{AEF_BUCKET}/{AEF_PREFIX}/{year}/{zone}"
    pattern = f"{prefix}/*.vrt"
    return sorted(fs_src.glob(pattern))


def open_mosaic_for_year_zone(year, zone, fs_src):
    """
    Open and mosaic all tiles (VRTs) for one year & zone as a single
    lazy DataArray with dims: (band, y, x).
    """
    vrt_paths = list_vrt_tiles_for_year_zone(fs_src, year, zone)
    if not vrt_paths:
        raise RuntimeError(f"No VRT tiles found for {year} {zone}")

    print(f"  {zone} {year}: found {len(vrt_paths)} tiles")

    # Build S3 URLs
    urls = [f"s3://{p}" for p in vrt_paths]
    
    # Open lazily
    tiles = [
        rioxarray.open_rasterio(
            url,
            chunks={"x": CHUNK_X, "y": CHUNK_Y},
            masked=True,
            # Important for public S3 w/o creds:
            **{"aws_unsigned": True, "aws_region": "us-west-2"}
        )
        for url in urls
    ]

    # Mosaic by coordinates
    da = xr.combine_by_coords(tiles, combine_attrs="override")

    # Enforce feature naming and dtype
    da = da.assign_coords(band=FEATURE_NAMES).rename({"band": "feature"})
    da = da.astype("int8")

    # Add time dimension
    da = da.expand_dims(time=[year])

    return da


def build_zone_dataset(zone, fs_src):
    """
    Build an xarray.Dataset for one zone across all YEARS.
    Result dims: (time, feature, y, x)
    """
    print(f"\nProcessing zone: {zone}")
    mosaics = []
    for year in YEARS:
        mosaics.append(open_mosaic_for_year_zone(year, zone, fs_src))

    # Stack years along time
    da_all = xr.concat(mosaics, dim="time")

    ds = da_all.to_dataset(name="embedding")

    # Nodata handling: keep -128 as nodata
    ds = ds.where(ds != FILL_VALUE, FILL_VALUE)
    ds["embedding"].attrs.update({
        "long_name": "AlphaEarth Foundation embeddings (A00–A63)",
        "units": "unitless",
        "_FillValue": FILL_VALUE,
        "grid_mapping": "crs",
    })

    ds = ds.assign_coords(feature=("feature", FEATURE_NAMES))

    ds.attrs.update({
        "title": f"AlphaEarth Foundations v1 embeddings – zone {zone}",
        "description": (
            "Multi-year AlphaEarth Foundations (AEF) embeddings for UTM zone "
            f"{zone}. Features A00–A63, 10m resolution, years {YEARS[0]}–{YEARS[-1]}."
        ),
        "crs": CRS,
        "resolution": "10 m",
        "time_range": f"{YEARS[0]}–{YEARS[-1]}",
        "feature_names": ",".join(FEATURE_NAMES),
        "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_bucket": AEF_BUCKET,
        "source_prefix": AEF_PREFIX,
    })

    return ds


def write_zone_zarr(ds, zone, fs_tgt):
    """
    Write zone dataset as Zarr to GFZ S3.
    """
    zarr_path = f"s3://{TARGET_BUCKET}/{TARGET_PREFIX}/AEF_v1_{zone}.zarr"
    print(f"  Writing Zarr for zone {zone} → {zarr_path}")

    store = s3fs.S3Map(root=zarr_path, s3=fs_tgt, check=False)

    # Clean old store if exists
    if fs_tgt.exists(f"{TARGET_BUCKET}/{TARGET_PREFIX}/AEF_v1_{zone}.zarr"):
        print("  Removing existing Zarr before writing...")
        fs_tgt.rm(f"{TARGET_BUCKET}/{TARGET_PREFIX}/AEF_v1_{zone}.zarr", recursive=True)

    #compressor = BloscCodec(cname="zstd", clevel=3, shuffle="shuffle")
    encoding = {
        "embedding": {
            "chunks": (1, N_FEATURES, CHUNK_Y, CHUNK_X),  # (time, feature, y, x)
            #"compressor": compressor,
            "dtype": "int8",
            "_FillValue": FILL_VALUE,
        }
    }

    ds.to_zarr(store=store, mode="w", encoding=encoding, consolidated=True)

    print(f"  Done zone {zone}.")


# ---------------- MAIN ---------------- #

fs_src = make_source_fs()
fs_tgt = make_target_fs()

zones = list_zones(fs_src)
print("Discovered zones:", zones)

for zone in zones[0:2]:
    ds_zone = build_zone_dataset(zone, fs_src)
    write_zone_zarr(ds_zone, zone, fs_tgt)

print("\nAll zones processed.")
