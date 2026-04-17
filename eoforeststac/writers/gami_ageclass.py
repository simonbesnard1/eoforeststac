from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import numpy as np
import xarray as xr

from eoforeststac.core.zarr import DEFAULT_COMPRESSOR
from eoforeststac.writers.base import BaseZarrWriter

# Age class labels used to validate input data
EXPECTED_AGE_CLASSES = [
    "0-20",
    "20-40",
    "40-60",
    "60-80",
    "80-100",
    "100-120",
    "120-140",
    "140-160",
    "160-180",
    "180-200",
    "200-299",
    ">299",
]


class GAMIAgeClassWriter(BaseZarrWriter):
    """
    Writer for GAMI age-class fraction product (multi-resolution).

    Reads an existing Zarr store produced by the age upscaling workflow
    (dimensions: members, age_class, latitude, longitude, time; variable:
    forest_age as fraction 0-1), rechunks it, adds metadata, and writes a
    single annotated Zarr store to Ceph/S3. Call once per resolution.

    Example::

        writer.write(
            input_zarr="/path/to/AgeClass_0.25deg",
            output_zarr="s3://bucket/collections/GAMI_AGECLASS/GAMI_AGECLASS_0.25deg_v3.0.zarr",
            resolution="0.25deg",
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
        resolution: str,
        fill_value: float = -9999.0,
        crs: str = "EPSG:4326",
        version: str = "3.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Harmonize chunking, CRS, dtype, and metadata.

        Parameters
        ----------
        resolution : str
            Resolution label, e.g. "0.25deg". Used in metadata only.
        """
        ds = self.set_crs(ds, crs=crs)

        if chunks is not None:
            ds = ds.chunk(chunks)

        # forest_age is a fraction (0-1): keep as float32
        if "forest_age" in ds:
            ds["forest_age"] = ds["forest_age"].astype("float32")
            ds["forest_age"] = ds["forest_age"].where(
                np.isfinite(ds["forest_age"]), fill_value
            )

            ds["forest_age"].attrs.update(
                {
                    "long_name": "Forest age-class fraction",
                    "description": (
                        "Fractional area of forest within each age class per grid cell. "
                        "Derived from GAMI ensemble age estimates via histogram binning. "
                        "Values sum to 1 across age_class dimension for forested pixels."
                    ),
                    "units": "fraction",
                    "grid_mapping": "spatial_ref",
                    "valid_min": 0.0,
                    "valid_max": 1.0,
                    "age_class_labels": ", ".join(EXPECTED_AGE_CLASSES),
                }
            )

        self.set_global_metadata(
            ds,
            {
                "title": f"GAMI Age-Class Fractions {resolution} v{version}",
                "product_name": "GAMI Age-Class Fractions",
                "version": version,
                "spatial_resolution": resolution,
                "institution": (
                    "Helmholtz Centre Potsdam - GFZ German Research Centre for Geosciences; "
                    "Max Planck Institute for Biogeochemistry"
                ),
                "created_by": "Simon Besnard",
                "contact": "Simon Besnard (GFZ Potsdam)",
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "spatial_ref": crs,
                "ensemble_members": 20,
                "age_classes": ", ".join(EXPECTED_AGE_CLASSES),
                "reference_years": "2010, 2020",
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
        resolution: str,
        version: str = "3.0",
        fill_value: float = -9999.0,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Repackage a native GAMI age-class Zarr store to Ceph.

        Parameters
        ----------
        input_zarr : str
            Path to the native Zarr store, e.g.
            "/path/to/AgeClass_0.25deg".
        output_zarr : str
            S3 destination, e.g.
            "s3://bucket/collections/GAMI_AGECLASS/GAMI_AGECLASS_0.25deg_v3.0.zarr".
        resolution : str
            Resolution label matching GAMI_AGECLASS_RESOLUTIONS keys,
            e.g. "0.25deg".
        """
        if chunks is None:
            # Default: collapse small dims, use moderate spatial chunks.
            # members=20, age_class=12, time=2 are all small → collapse to -1.
            # Spatial chunks ~4 MB per chunk at float32:
            #   time=2, members=20, age_class=12, lat=90, lon=180
            #   → 2*20*12*90*180*4 bytes ≈ 31 MB  (large but typical for global)
            # Use smaller spatial for higher resolutions:
            spatial = _default_spatial_chunks(resolution)
            chunks = {
                "time": -1,
                "members": -1,
                "age_class": -1,
                "latitude": spatial,
                "longitude": spatial * 2,
            }

        print(f"GAMI AgeClass [{resolution}]: loading {input_zarr}…")
        ds = self.load_dataset(input_zarr)

        print(f"GAMI AgeClass [{resolution}]: processing…")
        ds = self.process_dataset(
            ds,
            resolution=resolution,
            fill_value=fill_value,
            crs=crs,
            version=version,
            chunks=chunks,
        )

        # Build encoding from actual chunk layout
        time_size = ds.sizes.get("time", 1)
        members_size = ds.sizes.get("members", 20)
        age_class_size = ds.sizes.get("age_class", 12)
        lat_chunk = (
            chunks["latitude"] if chunks["latitude"] != -1 else ds.sizes["latitude"]
        )
        lon_chunk = (
            chunks["longitude"] if chunks["longitude"] != -1 else ds.sizes["longitude"]
        )

        encoding = {
            var: {
                "dtype": "float32",
                "chunks": (
                    members_size,
                    age_class_size,
                    lat_chunk,
                    lon_chunk,
                    time_size,
                ),
                "compressor": DEFAULT_COMPRESSOR,
                "_FillValue": np.float32(fill_value),
            }
            for var in ds.data_vars
            if var != "spatial_ref"
        }

        print(f"GAMI AgeClass [{resolution}]: writing to {output_zarr}…")
        result = self.write_to_zarr(ds, output_zarr, encoding=encoding)
        print(f"GAMI AgeClass [{resolution}]: done.")
        return result


def _default_spatial_chunks(resolution: str) -> int:
    """Return a reasonable latitude chunk size for a given resolution label."""
    mapping = {
        "1deg": 90,
        "0.5deg": 90,
        "0.25deg": 90,
        "0.1deg": 90,
        "0.083deg": 90,
    }
    return mapping.get(resolution, 90)
