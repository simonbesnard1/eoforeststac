import xarray as xr
import rioxarray
from datetime import datetime
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class FORESTPATHSGenus2020Writer(BaseZarrWriter):
    """
    Writer for the European Tree Genus Map (10 m, 2020).

    Native input:
      - Single European mosaic GeoTIFF (EPSG:3035, categorical)

    Output:
      - Chunked, compressed Zarr on Ceph/S3

    Classes (uint8):
      0 Larix 
      1 Picea
      2 Pinus
      3 Fagus
      4 Quercus
      5 Other needleleaf
      6 Other broadleaf
      7 No trees
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(self, tif_path: str) -> xr.Dataset:
        """
        Load genus GeoTIFF lazily and return Dataset with variable `genus`.
        """

        da = (
            rioxarray.open_rasterio(
                tif_path,
                masked=True,
                chunks="auto",   # let rasterio+dask decide tiling
            )
            .squeeze(drop=True)
            .rename("genus")
        )

        return da.to_dataset()

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = 255,
        crs: str = "EPSG:3035",
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Harmonize CRS, dimensions, chunking, dtype, and metadata.
        """

        # --------------------------------------------------------------
        # CRS
        # --------------------------------------------------------------
        ds = self.set_crs(ds, crs=crs)

        # --------------------------------------------------------------
        # Rename raster dimensions (projected!)
        # --------------------------------------------------------------
        rename_dims = {}
        if "x" in ds.dims:
            rename_dims["x"] = "longitude"
        if "y" in ds.dims:
            rename_dims["y"] = "latitude"

        if rename_dims:
            ds = ds.rename(rename_dims)
            for old, new in rename_dims.items():
                if old in ds.coords:
                    ds = ds.rename({old: new})

        # --------------------------------------------------------------
        # Chunking (after renaming)
        # --------------------------------------------------------------
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --------------------------------------------------------------
        # Categorical handling
        # --------------------------------------------------------------
        # Do NOT apply masking logic beyond nodata
        ds = self.apply_fillvalue(ds, fill_value=fill_value)

        # Compact integer storage
        ds = ds.astype("uint16")

        # --------------------------------------------------------------
        # Coordinate metadata (projected meters)
        # --------------------------------------------------------------
        if "longitude" in ds.coords:
            ds["longitude"].attrs.update({
                "long_name": "Projected x coordinate (ETRS89 / LAEA Europe)",
                "standard_name": "projection_x_coordinate",
                "units": "m",
                "axis": "X",
            })

        if "latitude" in ds.coords:
            ds["latitude"].attrs.update({
                "long_name": "Projected y coordinate (ETRS89 / LAEA Europe)",
                "standard_name": "projection_y_coordinate",
                "units": "m",
                "axis": "Y",
            })

        # --------------------------------------------------------------
        # Variable metadata
        # --------------------------------------------------------------
        ds["genus"].attrs.update({
                "long_name": "Tree genus classification",
                "description": (
                    "European tree genus map at 10 m resolution derived from Sentinel-1 "
                    "and Sentinel-2 data for reference year 2020. "
                    "Categorical map describing dominant tree genus or functional group."
                ),
                "grid_mapping": "crs",
                "valid_min": 0,
                "valid_max": 7,
            
                # ---- legend (authoritative, explicit) ----
                "flag_values": [0, 1, 2, 3, 4, 5, 6, 7],
                "flag_meanings": (
                    "larix "
                    "picea "
                    "pinus "
                    "fagus "
                    "quercus "
                    "other_needleleaf "
                    "other_broadleaf "
                    "no_trees"
                ),
            
                # provenance
                "source": "European Tree Genus Map (Sentinel-1 & Sentinel-2)",
                "reference_year": 2020,
            })

        # --------------------------------------------------------------
        # Global metadata
        # --------------------------------------------------------------
        meta = {
            "title": "European Tree Genus Map (10 m, 2020)",
            "product_name": "EU Tree Genus 2020",
            "description": (
                "Early access European tree genus map at 10 m spatial resolution "
                "for the year 2020, derived from Sentinel-1 and Sentinel-2 data. "
                "Distributed as Cloud Optimized GeoTIFFs and repacked here as Zarr."
            ),
            "institution": "European tree genus mapping consortium",
            "references": "https://doi.org/10.5281/zenodo.13341104",
            "version": version,
            "spatial_resolution": "10 m",
            "crs": crs,
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
        version: str = "1.0",
        fill_value: int = 255,
        crs: str = "EPSG:3035",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        End-to-end:
            COG → harmonized Dataset → Zarr-on-Ceph
        """

        if chunks is None:
            chunks = {
                "latitude": 2048,
                "longitude": 2048,
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

        encoding = {
            "genus": {
                "chunks": (
                    chunks["latitude"],
                    chunks["longitude"],
                ),
                "compressor": DEFAULT_COMPRESSOR,
                "dtype": "uint8",
                "_FillValue": fill_value,
            }
        }
        
        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
