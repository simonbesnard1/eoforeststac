from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional

import numpy as np
import xarray as xr

from eoforeststac.core.zarr import DEFAULT_COMPRESSOR
from eoforeststac.products.als_products import ALS_RESOLUTIONS, REGIONS
from eoforeststac.writers.base import BaseZarrWriter

VARIABLE_ATTRS = {
    "chm": {"long_name": "Canopy height model", "units": "m"},
    "dtm": {"long_name": "Digital terrain model", "units": "m"},
    "dsm": {"long_name": "Digital surface model", "units": "m"},
    "gap": {"long_name": "Gap fraction", "units": "fraction"},
    "lai": {"long_name": "Effective leaf area index", "units": "m2 m-2"},
    "biomass": {"long_name": "Above-ground biomass", "units": "Mg ha-1"},
    "h50": {"long_name": "Height 50th percentile", "units": "m"},
    "h75": {"long_name": "Height 75th percentile", "units": "m"},
    "h95": {"long_name": "Height 95th percentile", "units": "m"},
    "hmax": {"long_name": "Maximum height", "units": "m"},
    "hmean": {"long_name": "Mean height", "units": "m"},
    "cc": {"long_name": "Canopy cover", "units": "fraction"},
    "density": {"long_name": "Point density", "units": "pts m-2"},
    "fhd": {"long_name": "Foliage height diversity", "units": "nats"},
    "vci": {"long_name": "Vegetation complexity index", "units": "dimensionless"},
    "crr": {"long_name": "Canopy relief ratio", "units": "dimensionless"},
    "pv_0_2": {"long_name": "Point fraction 0–2 m", "units": "fraction"},
    "pv_2_5": {"long_name": "Point fraction 2–5 m", "units": "fraction"},
    "pv_5_10": {"long_name": "Point fraction 5–10 m", "units": "fraction"},
    "pv_10_20": {"long_name": "Point fraction 10–20 m", "units": "fraction"},
    "pv_20_40": {"long_name": "Point fraction 20–40 m", "units": "fraction"},
    "pv_above40": {"long_name": "Point fraction >40 m", "units": "fraction"},
}


class ALSProductsWriter(BaseZarrWriter):
    """
    Writer for ALS gridded products.

    Reads existing per-resolution Zarr stores produced by the alsdb pipeline,
    rechunks, adds metadata, and writes to Ceph/S3.  Call once per
    region + resolution combination.

    Example::

        writer.write(
            input_zarr="/data/als/spain_pnoa/10m",
            output_zarr="s3://bucket/collections/ALS_PRODUCTS/ALS_SPAIN_PNOA_10m_v1.0.zarr",
            region="spain_pnoa",
            resolution="10m",
        )
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(self, input_zarr: str) -> xr.Dataset:
        return xr.open_zarr(input_zarr)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        region: str,
        resolution: str,
        fill_value: float = -9999.0,
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        reg = REGIONS[region]
        res_meta = ALS_RESOLUTIONS[resolution]

        crs = f"EPSG:{reg['proj_epsg']}"
        ds = self.set_crs(ds, crs=crs)

        if chunks is not None:
            ds = ds.chunk(chunks)

        for var in list(ds.data_vars):
            if var == "spatial_ref":
                continue
            ds[var] = ds[var].astype("float32")
            ds[var] = ds[var].where(np.isfinite(ds[var]), fill_value)

            attrs = VARIABLE_ATTRS.get(var, {}).copy()
            attrs.update(
                {
                    "grid_mapping": "spatial_ref",
                    "_FillValue": fill_value,
                }
            )
            ds[var].attrs.update(attrs)

        expected = set(res_meta["variables"])
        present = {v for v in ds.data_vars if v != "spatial_ref"}
        missing = expected - present
        if missing:
            print(f"Warning: expected variables missing from input: {sorted(missing)}")

        self.set_global_metadata(
            ds,
            {
                "title": f"ALS Products – {reg['label']} {resolution} v{version}",
                "product_name": "ALS Products",
                "region": region,
                "region_label": reg["label"],
                "version": version,
                "spatial_resolution": resolution,
                "gsd_m": res_meta["gsd"],
                "institution": "GFZ Helmholtz Centre Potsdam",
                "created_by": "alsdb pipeline",
                "creation_date": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M UTC"
                ),
                "spatial_ref": crs,
                "proj_epsg": reg["proj_epsg"],
                "_FillValue": fill_value,
            },
        )

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        input_zarr: str,
        output_zarr: str,
        region: str,
        resolution: str,
        version: str = "1.0",
        fill_value: float = -9999.0,
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Repackage an alsdb Zarr store to Ceph/S3.

        Parameters
        ----------
        input_zarr : str
            Path to the source Zarr store, e.g. "/data/als/spain_pnoa/10m".
        output_zarr : str
            S3 destination, e.g.
            "s3://bucket/collections/ALS_PRODUCTS/ALS_SPAIN_PNOA_10m_v1.0.zarr".
        region : str
            Key in REGIONS, e.g. "spain_pnoa".
        resolution : str
            Key in ALS_RESOLUTIONS, e.g. "10m".
        """
        if region not in REGIONS:
            raise ValueError(f"Unknown region '{region}'. Available: {list(REGIONS)}")
        if resolution not in ALS_RESOLUTIONS:
            raise ValueError(
                f"Unknown resolution '{resolution}'. Available: {list(ALS_RESOLUTIONS)}"
            )

        if chunks is None:
            chunks = _default_chunks(resolution)

        label = f"ALS [{REGIONS[region]['label']} / {resolution}]"

        print(f"{label}: loading {input_zarr}…")
        ds = self.load_dataset(input_zarr)

        print(f"{label}: processing…")
        ds = self.process_dataset(
            ds,
            region=region,
            resolution=resolution,
            fill_value=fill_value,
            version=version,
            chunks=chunks,
        )

        encoding = {}
        for var in ds.data_vars:
            if var == "spatial_ref":
                continue
            var_chunks = tuple(chunks.get(dim, ds.sizes[dim]) for dim in ds[var].dims)
            encoding[var] = {
                "dtype": "float32",
                "chunks": var_chunks,
                "compressor": DEFAULT_COMPRESSOR,
                "_FillValue": np.float32(fill_value),
            }

        print(f"{label}: writing to {output_zarr}…")
        result = self.write_to_zarr(ds, output_zarr, encoding=encoding)
        print(f"{label}: done.")
        return result

    def write_region(
        self,
        input_dir: str,
        region: str,
        version: str = "1.0",
        output_prefix: Optional[str] = None,
        fill_value: float = -9999.0,
    ) -> list[str]:
        """
        Write all resolutions for a region.

        Parameters
        ----------
        input_dir : str
            Directory containing one Zarr v2 store per resolution,
            e.g. "/data/als/spain_pnoa/" with children 1m.zarr, 10m.zarr, 100m.zarr.
        output_prefix : str, optional
            S3 prefix for output.  Defaults to
            ``s3://{bucket}/collections/ALS_PRODUCTS``.
        """
        if output_prefix is None:
            output_prefix = f"s3://{self.bucket}/collections/ALS_PRODUCTS"

        reg = REGIONS[region]
        results = []
        for resolution in ALS_RESOLUTIONS:
            input_zarr = f"{input_dir.rstrip('/')}/{resolution}.zarr"
            output_zarr = (
                f"{output_prefix}/{reg['zarr_name']}_{resolution}_v{version}.zarr"
            )
            result = self.write(
                input_zarr=input_zarr,
                output_zarr=output_zarr,
                region=region,
                resolution=resolution,
                version=version,
                fill_value=fill_value,
            )
            results.append(result)
        return results


def _default_chunks(resolution: str) -> Dict[str, int]:
    """Return reasonable chunk sizes based on resolution."""
    defaults = {
        "1m": {"y": 2048, "x": 2048},
        "10m": {"y": 1024, "x": 1024},
        "100m": {"y": 512, "x": 512},
    }
    return defaults.get(resolution, {"y": 1024, "x": 1024})
