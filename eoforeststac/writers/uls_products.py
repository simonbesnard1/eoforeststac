from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Any

import numpy as np
import xarray as xr

from eoforeststac.core.zarr import DEFAULT_COMPRESSOR
from eoforeststac.products.uls_products import REGIONS, ULS_RESOLUTIONS
from eoforeststac.writers.als_products import VARIABLE_ATTRS
from eoforeststac.writers.base import BaseZarrWriter


class ULSProductsWriter(BaseZarrWriter):
    """
    Writer for ULS (UAV laser scanning) gridded products.

    Reads Zarr stores produced by the ULS R pipeline, rechunks,
    adds metadata, and writes to Ceph/S3.  Call once per
    site + resolution combination.

    Example::

        writer.write(
            input_zarr="/data/uls/hainich/10m",
            output_zarr="s3://bucket/collections/ULS_PRODUCTS/ULS_HAINICH_10m_v1.0.zarr",
            region="hainich",
            resolution="10m",
        )
    """

    def load_dataset(
        self,
        input_zarr: str,
    ) -> xr.Dataset:

        ds = xr.open_zarr(input_zarr)

        rename_dims = {
            old: new for old, new in [("X", "x"), ("Y", "y")] if old in ds.dims
        }

        return ds.rename_dims(rename_dims)

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
        res_meta = ULS_RESOLUTIONS[resolution]

        crs = f"EPSG:{reg['proj_epsg']}"
        ds = self.set_crs(ds, crs=crs)

        if chunks is not None:
            ds = ds.chunk(chunks)

        # fix encoding
        if "species" in ds:
            ds["species"].encoding = {}

        for var in list(ds.data_vars):
            if var == "spatial_ref":
                continue
            ds[var] = ds[var].astype("float32")
            ds[var] = ds[var].where(np.isfinite(ds[var]), fill_value)

            # attrs = VARIABLE_ATTRS.get(var, {}).copy()
            # attrs.update(
            #     {
            #         "grid_mapping": "spatial_ref",
            #         "_FillValue": fill_value,
            #     }
            # )
            # ds[var].attrs.update(attrs)

        expected = set(res_meta["variables"])
        present = {v for v in ds.data_vars if v != "spatial_ref"}
        missing = expected - present
        if missing:
            print(f"Warning: expected variables missing from input: {sorted(missing)}")

        self.set_global_metadata(
            ds,
            {
                "title": f"ULS Products – {reg['label']} {resolution} v{version}",
                "product_name": "ULS Products",
                "region": region,
                "region_label": reg["label"],
                "version": version,
                "spatial_resolution": resolution,
                "gsd_m": res_meta["gsd"],
                "institution": "GFZ Helmholtz Centre Potsdam",
                "created_by": "ULS R pipeline",
                "creation_date": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M UTC"
                ),
                "spatial_ref": crs,
                "proj_epsg": reg["proj_epsg"],
                "_FillValue": fill_value,
            },
        )

        return ds

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
        if region not in REGIONS:
            raise ValueError(f"Unknown region '{region}'. Available: {list(REGIONS)}")
        if resolution not in ULS_RESOLUTIONS:
            raise ValueError(
                f"Unknown resolution '{resolution}'. Available: {list(ULS_RESOLUTIONS)}"
            )

        if chunks is None:
            chunks = _default_chunks(resolution)

        label = f"ULS [{REGIONS[region]['label']} / {resolution}]"

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

    def _find_input(
        self,
        input_dir: str,
        resolution: str,
    ) -> str:
        input_path = Path(input_dir)

        matching_paths = [
            path
            for path in input_path.iterdir()
            if path.is_dir() and resolution in path.name
        ]

        if not matching_paths:
            raise FileNotFoundError(
                f"No directory found for resolution '{resolution}' in {input_dir}"
            )

        if len(matching_paths) > 1:
            raise RuntimeError(
                f"Multiple directories found for resolution '{resolution}': "
                f"{matching_paths}"
            )

        zarrs = list(matching_paths[0].glob("*.zarr"))

        if not zarrs:
            raise FileNotFoundError(f"No Zarr found in {matching_paths[0]}")

        if len(zarrs) > 1:
            raise RuntimeError(f"Multiple Zarrs found in {matching_paths[0]}: {zarrs}")

        return str(zarrs[0])

    def write_region(
        self,
        input_dir: str,
        region: str,
        version: str = "1.0",
        output_prefix: Optional[str] = None,
        fill_value: float = -9999.0,
    ) -> list[str]:
        if output_prefix is None:
            output_prefix = f"s3://{self.bucket}/collections/ULS_PRODUCTS"

        reg = REGIONS[region]
        results = []
        for resolution in ULS_RESOLUTIONS:
            input_zarr = self._find_input(input_dir, resolution)

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
    defaults = {
        "10m": {"species": 16, "y": 2048, "x": 2048},
        "20m": {"species": 16, "y": 1024, "x": 1024},
        "100m": {"species": 16, "y": 512, "x": 512},
    }
    return defaults.get(resolution, {"species": 16, "y": 1024, "x": 1024})
