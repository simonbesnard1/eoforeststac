import xarray as xr
import rioxarray
from datetime import datetime
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class JRCGFC2020Writer(BaseZarrWriter):
    """
    Writer for JRC Global Forest Cover 2020 (v3).

    Native input:
      - Single global Cloud-Optimized GeoTIFF (categorical land cover)

    Output:
      - Chunked, compressed Zarr on Ceph/S3
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(self, tif_path: str) -> xr.Dataset:
        """
        Load JRC GFC COG lazily and return Dataset with variable `forest_cover`.
        """

        da = (
            rioxarray.open_rasterio(
                tif_path,
                masked=True,
                chunks="auto",  # let rasterio+dask decide initial tiling
            )
            .squeeze(drop=True)
            .rename("forest_cover")
        )

        return da.to_dataset()

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = 255,
        crs: str = "EPSG:4326",
        version: str = "3.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Harmonize CRS, dimensions, chunking and metadata.
        """

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)

        # --- Rename raster dimensions ---
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

        # --- Chunking (after renaming) ---
        if chunks is not None:
            ds = ds.chunk(chunks)

        # ------------------------------------------------------------------
        # Categorical handling
        # ------------------------------------------------------------------
        # Do NOT zero-mask; keep original semantics
        ds = self.apply_fillvalue(ds, fill_value=fill_value)

        # JRC GFC is categorical → compact integer storage
        ds = ds.astype("uint8")

        # --- Variable metadata ---
        ds["forest_cover"].attrs.update({
            "long_name": "Global Forest Cover",
            "description": "Categorical forest cover classification for reference year 2020",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
            "valid_min": 0,
            "valid_max": 2,
            "source": "JRC Global Forest Cover 2020",
        })

        # --- Global metadata ---
        meta = {
            "title": "JRC Global Forest Cover 2020",
            "description": (
                "Global categorical forest cover map for reference year 2020 "
                "produced by the European Commission Joint Research Centre (JRC). "
                "Distributed as a single global Cloud-Optimized GeoTIFF and "
                "repacked here as chunked Zarr."
            ),
            "version": version,
            "institution": "European Commission – Joint Research Centre (JRC)",
            "references": "https://forobs.jrc.ec.europa.eu/GFC",
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
        version: str = "3.0",
        fill_value: int = 255,
        crs: str = "EPSG:4326",
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
            var: {
                "chunks": (
                    chunks["latitude"],
                    chunks["longitude"],
                ),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }
        
        print(ds)

        # print("Writing Zarr to Ceph/S3…")
        # return self.write_to_zarr(ds, output_zarr, encoding=encoding)
