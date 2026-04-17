import xarray as xr
import rioxarray
from datetime import datetime
from typing import Dict, Optional
import numpy as np

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class ForestPathsGenusWriter(BaseZarrWriter):
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
                chunks="auto",  # let rasterio+dask decide tiling
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

        # --------------------------------------------------
        # Add reference time coordinate (single epoch)
        # --------------------------------------------------
        if "time" not in ds.coords:
            ds = ds.assign_coords(time=np.datetime64("2020-01-01"))

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
        if "x" in ds.coords:
            ds["x"].attrs.update(
                {
                    "long_name": "Projected x coordinate (ETRS89 / LAEA Europe)",
                    "standard_name": "projection_x_coordinate",
                    "units": "m",
                    "axis": "X",
                }
            )

        if "y" in ds.coords:
            ds["y"].attrs.update(
                {
                    "long_name": "Projected y coordinate (ETRS89 / LAEA Europe)",
                    "standard_name": "projection_y_coordinate",
                    "units": "m",
                    "axis": "Y",
                }
            )

        # --------------------------------------------------------------
        # Variable metadata
        # --------------------------------------------------------------
        ds["genus"].attrs.update(
            {
                "long_name": "Tree genus classification",
                "description": (
                    "European tree genus map at 10 m resolution derived from Sentinel-1 "
                    "and Sentinel-2 data for reference year 2020. "
                    "Categorical map describing dominant tree genus or functional group."
                ),
                "grid_mapping": "spatial_ref",
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
            }
        )

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
            "spatial_ref": crs,
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
                "y": 2048,
                "x": 2048,
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
            var: {
                "chunks": (chunks["y"], chunks["x"]),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
