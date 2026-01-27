import xarray as xr
from datetime import datetime
from typing import Optional, Dict

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class CCI_BiomassWriter(BaseZarrWriter):
    """
    Writer for the ESA CCI Biomass product (v6+).

    Assumes the native input is already delivered as a Zarr store.
    """

    def load_dataset(
        self,
        input_zarr: str
    ) -> xr.Dataset:
        """
        Load ESA CCI Biomass from an existing Zarr store.
        """
        return xr.open_zarr(input_zarr)

    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        version: str = "6.0",
        chunks: dict | None = None,
    ) -> xr.Dataset:

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

        # --- Variable-level metadata ---
        if "aboveground_biomass" in ds:
            ds["aboveground_biomass"].attrs.update({
                "long_name": "Forest aboveground biomass",
                "units": "Mg/ha",
                "_FillValue": fill_value,
                "description": (
                    "Mass (oven-dry weight) of the woody parts (stem, bark, branches, twigs) "
                    "of all living trees per unit area, excluding stumps and roots."
                ),
                "source": "ESA Climate Change Initiative – Biomass v6, Santoro & Cartus (2025)",
                "grid_mapping": "spatial_ref",
            })

        if "aboveground_biomass_std" in ds:
            ds["aboveground_biomass_std"].attrs.update({
                "long_name": "Standard deviation of aboveground biomass",
                "units": "Mg/ha",
                "_FillValue": fill_value,
                "description": "Per-pixel estimate of aboveground biomass uncertainty (1-sigma).",
                "source": "ESA Climate Change Initiative – Biomass v6",
                "grid_mapping": "spatial_ref",
            })

        # --- Global metadata ---
        meta = {
            "title": f"ESA CCI Biomass v{version} – Global Aboveground Biomass (100 m)",
            "version": version,
            "institution": (
                "European Space Agency (ESA) Climate Change Initiative (CCI); "
                "NERC EDS Centre for Environmental Data Analysis"
            ),
            "source_dataset": "doi:10.5285/95913ffb6467447ca72c4e9d8cf30501",
            "created_by": "Santoro et al.",
            "contact": "Maurizio Santoro (GAMMA RS)",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "description": (
                "Global forest aboveground biomass maps for 2007–2022 derived from "
                "L-band radar (ALOS, ALOS-2), Sentinel-1, ICESat-2 calibration and "
                "multi-year temporal weighting."
            ),
            "spatial_resolution": "100 m",
            "_FillValue": fill_value,
            "crs": crs,
        }

        self.set_global_metadata(ds, meta)

        return ds

    def write(
        self,
        input_zarr: str,
        output_zarr: str,
        version: str = "6.0",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Complete end-to-end writing of ESA CCI biomass to Ceph in Zarr format.
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
            chunks = chunks
        )
        
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
