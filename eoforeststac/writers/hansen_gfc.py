# eoforeststac/writers/hansen_gfc.py

import xarray as xr
import rioxarray
from datetime import datetime
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class HansenGFCWriter(BaseZarrWriter):
    """
    Writer for Hansen Global Forest Change (GFC) v1.12.

    Native input:
      - One VRT per variable (each VRT mosaics global tiles)

    Variables written:
      - data_mask   (uint8)
      - gain        (uint8, boolean)
      - loss        (uint8, boolean)
      - tree_cover  (uint8, percent 0–100)

    CRS:
      - EPSG:4326
    Resolution:
      - 30 m
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(
        self,
        vrt_paths: Dict[str, str],
    ) -> xr.Dataset:
        """
        Load multiple Hansen GFC VRTs lazily and combine into a Dataset.

        Parameters
        ----------
        vrt_paths : dict
            Mapping {variable_name: vrt_path}
        """
        data_vars = {}

        for var, vrt_path in vrt_paths.items():
            da = (
                rioxarray.open_rasterio(
                    vrt_path,
                    masked=True,
                    chunks="auto",   # rasterio + dask decide optimal tiling
                )
                .squeeze(drop=True)
                .rename(var)
            )
            data_vars[var] = da

        return xr.Dataset(data_vars)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        crs: str = "EPSG:4326",
        version: str = "1.12",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Harmonize CRS, dimensions, chunking, dtypes and metadata.
        """

        # --------------------------------------------------
        # CRS
        # --------------------------------------------------
        ds = self.set_crs(ds, crs=crs)

        # --------------------------------------------------
        # Rename raster dimensions
        # --------------------------------------------------
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

        # --------------------------------------------------
        # Chunking (after renaming)
        # --------------------------------------------------
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --------------------------------------------------
        # Dtypes & semantics (Hansen conventions)
        # --------------------------------------------------
        if "tree_cover" in ds:
            ds["tree_cover"] = ds["tree_cover"].astype("uint8")

        for var in ("loss", "gain", "data_mask"):
            if var in ds:
                ds[var] = ds[var].astype("uint8")

        # --------------------------------------------------
        # Variable metadata
        # --------------------------------------------------
        if "tree_cover" in ds:
            ds["tree_cover"].attrs.update({
                "long_name": "Tree canopy cover in year 2000",
                "description": (
                    "Percent tree canopy cover for vegetation taller than 5 m "
                    "in the year 2000."
                ),
                "units": "percent",
                "valid_min": 0,
                "valid_max": 100,
                "grid_mapping": "crs",
            })

        if "loss" in ds:
            ds["loss"].attrs.update({
                "long_name": "Forest cover loss",
                "description": (
                    "Forest loss indicator for the period 2001–2024. "
                    "Value 1 indicates loss; 0 indicates no loss."
                ),
                "valid_min": 0,
                "valid_max": 1,
                "grid_mapping": "crs",
            })

        if "gain" in ds:
            ds["gain"].attrs.update({
                "long_name": "Forest cover gain",
                "description": (
                    "Forest gain indicator for the period 2000–2012. "
                    "Value 1 indicates gain; 0 indicates no gain."
                ),
                "valid_min": 0,
                "valid_max": 1,
                "grid_mapping": "crs",
            })

        if "data_mask" in ds:
            ds["data_mask"].attrs.update({
                "long_name": "Data mask",
                "description": (
                    "Data availability mask distinguishing land, water, "
                    "and areas without valid observations."
                ),
                "grid_mapping": "crs",
            })

        # --------------------------------------------------
        # Global metadata
        # --------------------------------------------------
        meta = {
            "title": "Global Forest Change (Hansen et al.)",
            "description": (
                "Global Forest Change dataset derived from Landsat imagery, "
                "quantifying forest extent, loss, and gain from 2000 to 2024. "
                "Produced by the University of Maryland and partners."
            ),
            "version": version,
            "institution": "University of Maryland, Department of Geographical Sciences",
            "created_by": "Hansen et al.",
            "references": (
                "https://storage.googleapis.com/earthenginepartners-hansen/"
                "GFC-2024-v1.12/download.html"
            ),
            "spatial_resolution": "30 m",
            "crs": crs,
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        self.set_global_metadata(ds, meta)

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        vrt_paths: Dict[str, str],
        output_zarr: str,
        version: str = "1.12",
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        End-to-end:
            VRTs → harmonized Dataset → Zarr-on-Ceph/S3
        """

        if chunks is None:
            chunks = {
                "latitude": 2048,
                "longitude": 2048,
            }

        print("Loading Hansen GFC VRTs…")
        ds = self.load_dataset(vrt_paths)

        print("Processing dataset…")
        ds = self.process_dataset(
            ds,
            crs=crs,
            version=version,
            chunks=chunks,
        )

        encoding = {
            var: {
                "chunks": (
                    chunks["latitude"],
                    chunks["longitude"],
                ),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
