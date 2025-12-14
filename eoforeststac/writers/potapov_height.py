import xarray as xr
from datetime import datetime
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class PotapovHeightWriter(BaseZarrWriter):
    """
    Writer for global canopy height product (Potapov et al.).

    Native input: Zarr cube with dimensions
      (latitude, longitude, time)
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(
        self,
        input_zarr: str,
    ) -> xr.Dataset:
        """
        Load Potapov canopy height Zarr lazily.
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
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Harmonize Potapov canopy height cube.
        """

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)
        
        # --- Chunking ---
        if chunks is not None:
            ds = ds.chunk(chunks)
            
        # --- Zero → NaN → fill_value → dtype (SAFE) ---
        for var in ds.data_vars:
            ds[var] = (
                ds[var]
                .where(ds[var] != 0)
            )
                    
        # --- Fill values and dtype ---
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int32")

        # --- Variable metadata ---
        ds['canopy_height'].attrs.update({
            "long_name": "Canopy top height",
            "units": "m",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
            "valid_min": 0,
            "source": "Potapov et al., University of Maryland / GLAD",
        })

        # --- Global metadata ---
        meta = {
            "title": "Global Canopy Height (Potapov et al.)",
            "version": version,
            "product_name": "Global Canopy Height",
            "institution": "University of Maryland / GLAD",
            "created_by": "Potapov et al.",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "spatial_resolution": "100 m",
            "crs": crs,
            "_FillValue": fill_value,
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
        version: str = "6.0",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:

        print("Loading dataset…")
        ds = self.load_dataset(input_zarr)

        print("Processing dataset…")
        ds = self.process_dataset(
            ds,
            fill_value=fill_value,
            crs=crs,
            chunks=chunks,
        )

        # --- Encoding: derive from actual Dask chunks ---
        encoding = {}
        for var in ds.data_vars:
            # Dask chunks come as tuples per dimension
            chunk_tuple = tuple(
                ds[var].chunksizes[dim][0] for dim in ds[var].dims
            )

            encoding[var] = {
                "chunks": chunk_tuple,
                "compressor": DEFAULT_COMPRESSOR,
            }

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)

