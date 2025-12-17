import xarray as xr
import rioxarray
from datetime import datetime
from typing import Dict, Optional
import numpy as np

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class SaatchiBiomassWriter(BaseZarrWriter):
    """
    Writer for Saatchi et al. (2020) global aboveground biomass (AGB).

    Native input: single-band GeoTIFF (100 m).
    Output: chunked, compressed Zarr on Ceph/S3.
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(
        self,
        tif_path: str
    ) -> xr.Dataset:
        """
        Load GeoTIFF lazily and return a Dataset with variable name `agb`.
        """
    
        da = (
            rioxarray.open_rasterio(
                tif_path,
                masked=True,       
            )
            .squeeze(drop=True)
            .rename("agb")
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
        version: str = "2.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Apply fill values, CRS, dimension harmonization, chunking,
        and metadata harmonization.
        """
    
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
   
        # --------------------------------------------------
        # Add reference time coordinate (single epoch)
        # --------------------------------------------------
        if "time" not in ds.coords:
            ds = ds.assign_coords(
                time=np.datetime64("2020-01-01")
            )

        # --- Chunking (after renaming!) ---
        if chunks is not None:
            ds = ds.chunk(chunks)
            
        # --- Zero → NaN → fill_value → dtype (SAFE) ---
        for var in ds.data_vars:
            ds[var] = (
                ds[var]
                .where(ds[var] != 0)
            )
            
        # --- Fill values + dtype ---
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int32")
    
        # --- Variable metadata ---
        if "agb" in ds:
            ds["agb"].attrs.update({
                "long_name": "Aboveground biomass (AGB), Saatchi et al. (2020)",
                "units": "Mg/ha",
                "grid_mapping": "crs",
                "valid_min": 0,
                "valid_max": 1000,
                "_FillValue": fill_value,
                "scale_factor": 0.1,
                "add_offset": 0.0,
                "source": "Saatchi et al. 2020 Harmonized Global Biomass dataset",
            })

        # --- Global metadata ---
        meta = {
            "title": "Global Aboveground Biomass 2020 (Saatchi et al.)",
            "description": (
                "Global harmonized 100 m aboveground biomass map for year 2020 "
                "based on Saatchi et al. (2021), harmonized and mosaicked."
            ),
            "version": version,
            "institution": (
                "Jet Propulsion Laboratory, California Institute of Technology, "
                "Pasadena, CA, USA"
            ),
            "references": "https://zenodo.org/records/15858551",
            "product_doi": "10.5281/zenodo.15858551",
            "spatial_resolution": "100 m",
            "crs": crs,
            "contact": "Sassan Saatchi (sassan.saatchi@jpl.nasa.gov)",
            "created_by": "Sassan Saatchi",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "_FillValue": fill_value,
        }
    
        self.set_global_metadata(ds, meta)
    
        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        tif_path: str,
        output_zarr: str,
        version: str = "2.0",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        End-to-end transform:
            GeoTIFF → Dataset → harmonization → Zarr-on-Ceph
        """

        if chunks is None:
            chunks = {
                "latitude": 500,
                "longitude": 500,
            }

        print("Loading dataset…")
        ds = self.load_dataset(tif_path)

        print("Processing dataset…")
        ds = self.process_dataset(
            ds,
            fill_value=fill_value,
            crs=crs,
            version=version,
            chunks=chunks,
        )

        # Zarr encoding derived from actual Dask chunks
        encoding = {
            var: {
                "chunks": (
                    chunks["latitude"],
                    chunks["longitude"]
                ),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
