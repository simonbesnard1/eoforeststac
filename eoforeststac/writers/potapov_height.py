import xarray as xr
import rioxarray
from datetime import datetime
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class PotapovHeightWriter(BaseZarrWriter):
    """
    Writer for global canopy height product (Potapov et al.).

    Native input: single-band global GeoTIFF.
    Output: chunked, compressed Zarr on Ceph/S3.
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(
        self,
        geotiff_path: str,
        var_name: str = "canopy_height",
    ) -> xr.Dataset:
        """
        Load GeoTIFF lazily and return a Dataset.
        """
        da = (
            rioxarray.open_rasterio(geotiff_path)
            .squeeze(drop=True)
            .rename(var_name)
        )

        return da.to_dataset()

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        var_name: str = "canopy_height",
        reference_year: Optional[int] = 2020,
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Apply fill values, CRS, chunking, and metadata harmonization.
        """

        # --- Fill values + dtype ---
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int16")

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)
        
        # ------------------------------------------------------------------
        # Rename raster dimensions to geodetic ones
        # ------------------------------------------------------------------
        rename_dims = {}
        if "x" in ds.dims:
            rename_dims["x"] = "longitude"
        if "y" in ds.dims:
            rename_dims["y"] = "latitude"
    
        if rename_dims:
            ds = ds.rename(rename_dims)
    
            # also rename coordinates explicitly if present
            for old, new in rename_dims.items():
                if old in ds.coords:
                    ds = ds.rename({old: new})

        # --- Chunking ---
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --- Variable metadata ---
        if var_name in ds:
            ds[var_name].attrs.update({
                "long_name": "Canopy top height",
                "units": "m",
                "grid_mapping": "crs",
                "valid_min": 0,
                "_FillValue": fill_value,
            })

        # --- Global metadata ---
        meta = {
            "title": "Global Canopy Height (Potapov et al.)",
            "product_name": "Global Canopy Height",
            "institution": "University of Maryland / GLAD",
            "created_by": "Potapov et al.",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "spatial_resolution": "100 m",
            "crs": crs,
            "_FillValue": fill_value,
        }

        if reference_year is not None:
            meta["reference_year"] = reference_year

        self.set_global_metadata(ds, meta)

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        geotiff_path: str,
        output_zarr: str,
        var_name: str = "canopy_height",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
        reference_year: Optional[int] = 2020,
    ) -> str:
        """
        End-to-end transform:
            GeoTIFF → Dataset → harmonization → Zarr-on-Ceph
        """

        if chunks is None:
            chunks = {"latitude": 1000, "longitude": 1000}

        print("Loading dataset…")
        ds = self.load_dataset(
            geotiff_path,
            var_name=var_name,
        )

        print("Processing dataset…")
        ds = self.process_dataset(
            ds,
            fill_value=fill_value,
            crs=crs,
            var_name=var_name,
            reference_year=reference_year,
            chunks=chunks,
        )

        # Zarr encoding derived from actual Dask chunks
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

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
