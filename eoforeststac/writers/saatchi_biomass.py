import xarray as xr
import rioxarray
import numpy as np
from datetime import datetime
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter


class SaatchiBiomassWriter(BaseZarrWriter):
    """
    Writer for Saatchi et al. 2020 global aboveground biomass (AGB) map.
    Converts a GeoTIFF into a chunked Zarr store on Ceph/S3.
    """

    def load_geotiff(
        self,
        tif_path: str,
        chunks: Optional[Dict[str, int]] = None
    ) -> xr.DataArray:
        """
        Load GeoTIFF lazily with rioxarray, preserving chunking.
        """
        return (
            rioxarray.open_rasterio(tif_path, chunks=chunks or {"x": 500, "y": 500})
            .squeeze(drop=True)
            .rename("agb")
        )

    def process_dataset(
        self,
        da: xr.DataArray,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        version: str = "v2.0"
    ) -> xr.Dataset:

        # Replace NaN + cast to int32
        da = da.where(np.isfinite(da), fill_value).astype("int32")

        # CRS
        da = da.rio.write_crs(crs)

        ds = da.to_dataset()

        # Variable metadata (Saatchi 2020)
        ds["agb"].attrs.update({
            "long_name": "Aboveground biomass (AGB), Saatchi et al. (2020)",
            "units": "Mg/ha",
            "grid_mapping": "crs",
            "valid_min": 0,
            "valid_max": 1000,
            "_FillValue": fill_value,
            "source": "Saatchi et al. 2020 Harmonized Global Biomass dataset",
        })

        # Global metadata
        ds.attrs.update({
            "title": "Global Aboveground Biomass 2020 (Saatchi et al.)",
            "description": (
                "Global harmonized 100m aboveground biomass map for year 2020, "
                "based on Saatchi et al. (2021), harmonized and mosaicked."
            ),
            "version": version,
            "institution": (
                "Jet Propulsion Laboratory, California Institute of Technology, Pasadena, CA, USA"
            ),
            "references": "https://zenodo.org/records/15858551",
            "product_doi": "10.5281/zenodo.15858551",
            "spatial_resolution": "100 m",
            "crs": crs,
            "contact": "Sassan Saatchi (sassan.saatchi@jpl.nasa.gov)",
            "created_by": "Sassan Saatchi",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "_FillValue": fill_value,
        })

        return ds

    def write(
        self,
        tif_path: str,
        output_zarr: str,
        version: str = "v2.0",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        End-to-end transform:
            GeoTIFF → xarray.Dataset → chunking → Zarr-on-S3
        """

        if chunks is None:
            chunks = {"x": 500, "y": 500}

        print("Loading GeoTIFF lazily…")
        da = self.load_geotiff(tif_path, chunks=chunks)

        print("Processing dataset…")
        ds = self.process_dataset(
            da,
            fill_value=fill_value,
            crs=crs,
            version=version,
        )

        print("Chunking dataset…")
        ds = ds.chunk(chunks)

        # Zarr encoding
        encoding = {var: {"chunks": (chunks["y"], chunks["x"])} for var in ds.data_vars}

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
