import xarray as xr
from datetime import datetime
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class GAMIWriter(BaseZarrWriter):
    """
    Writer for the Global Age Mapping Integration (GAMI) product.

    Assumes the native input is already a Zarr store produced by the
    age upscaling workflow.
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(
        self,
        input_zarr: str,
    ) -> xr.Dataset:
        """
        Load GAMI dataset from an existing Zarr store.
        """
        return xr.open_zarr(input_zarr)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        version: str = "3.1",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Apply harmonized processing: fill values, CRS, chunking,
        and metadata.
        """

        # --- Fill values and dtype ---
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int16")

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)

        # --- Chunking ---
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --- Variable-level metadata ---
        if "forest_age" in ds:
            ds["forest_age"].attrs.update({
                "long_name": "Forest age using ML + Landsat-based time since disturbance fusion",
                "units": "years",
                "grid_mapping": "crs",
                "valid_min": 1,
                "valid_max": 300,
                "_FillValue": fill_value,
            })

        # --- Global metadata ---
        meta = {
            "title": f"Global Age Mapping Integration (GAMI) v{version}",
            "product_name": "Global Age Mapping Integration (GAMI)",
            "version": version,
            "institution": (
                "Helmholtz Centre Potsdam – GFZ German Research Centre for Geosciences; "
                "Max Planck Institute for Biogeochemistry"
            ),
            "created_by": "Simon Besnard",
            "contact": "Simon Besnard (GFZ Potsdam)",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "spatial_resolution": "100 m",
            "_FillValue": fill_value,
            "crs": crs,
        }

        self.set_global_metadata(ds, meta)

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        input_zarr: str,
        output_zarr: str,
        version: str = "3.1",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        End-to-end writing of GAMI to Ceph in Zarr format.
        """

        if chunks is None:
            chunks = {"time": -1, "latitude": 500, "longitude": 500}

        print("Loading dataset...")
        ds = self.load_dataset(input_zarr)

        print("Processing dataset...")
        ds = self.process_dataset(
            ds,
            fill_value=fill_value,
            crs=crs,
            version=version,
            chunks=chunks,
        )

        # 🔑 Encoding derived from *actual* Dask chunks
        encoding = {
                var: {
                    "chunks": (
                        chunks["latitude"],
                        chunks["longitude"],
                        chunks["time"],
                    ),
                    "compressor": DEFAULT_COMPRESSOR,
                }
                for var in ds.data_vars
            }


        print("Writing Zarr to Ceph…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
