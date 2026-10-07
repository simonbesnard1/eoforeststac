import xarray as xr
import rioxarray
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class ALSBiomassProductsWriter(BaseZarrWriter):
    """
    Writer for ALS Biomass Products (v1.0)

    Native input:
      - One VRT per variable (global mosaics)

    Output:
      - Single Zarr store with harmonized Hansen variables
    """

    # ------------------------------------------------------------------
    # Dataset definition
    # ------------------------------------------------------------------
    VARIABLES = {
        "biomass": {
            "dtype": "float32",
            "long_name": "Forest biomass",
            "description": "Forest biomass derived from airborne laser scanning.",
        }
    }

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_single_dataset(self, vrt_path: Path) -> xr.DataArray:
        """
        Load a single ALS Biomass VRT lazily.
        """
        da = (
            rioxarray.open_rasterio(
                vrt_path,
                masked=True,
                chunks="auto",
            )
            .squeeze(drop=True)
            .rename("biomass")
        )
        return da

    def load_dataset(self, vrt_dir: str) -> xr.Dataset:
        """
        Load all ALS Biomass VRT layers into a single Dataset.
        """
        data_vars = {}
        vrt_dir = Path(vrt_dir)

        tif_files = sorted(vrt_dir.glob("*.tif"))

        if not tif_files:
            raise FileNotFoundError(f"No TIFF files found in: {vrt_dir}")

        for tif_path in tif_files:
            data_vars[tif_path.stem] = self.load_single_dataset(
                tif_path
            )

        return xr.Dataset(data_vars)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        crs: str,
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Harmonize CRS, dimensions, chunking, semantics and metadata.
        """

        # --------------------------------------------------
        # CRS
        # --------------------------------------------------
        ds = self.set_crs(ds, crs=crs)

        # --------------------------------------------------
        # Chunking
        # --------------------------------------------------
        if chunks is not None:
            ds = ds.chunk(chunks)



        # --------------------------------------------------
        # Handle remaining variables
        # --------------------------------------------------
        for name, meta in self.VARIABLES.items():
            if name not in ds:
                continue

            ds[name] = ds[name].astype(meta["dtype"])
            ds[name].attrs.update(
                {
                    "description": meta["description"],
                    "long_name": meta["long_name"],
                    "grid_mapping": "spatial_ref",
                }
            )

        # --------------------------------------------------
        # Global metadata
        # --------------------------------------------------
        self.set_global_metadata(
            ds,
            {
                "title": "ALS-derived biomass (Europe)",
                "description": (
                    "Biomass maps at 10 m resolution derived from National Forest Inventorie" 
                    "and Airborne Laser Scanning in selected European countries (2006, 2011-2024)."
                ),
                "product_version": version,
                "spatial_resolution": "10 m",
                "spatial_ref": crs,
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        vrt_dir: str,
        output_zarr: str,
        crs: str,
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        End-to-end ALS Biomass GFC write:
            VRTs → Dataset → harmonized Zarr
        """

        if chunks is None:
            chunks = {"x": 2048, "y": 2048}

        print("Loading ALS Biomass GFC VRTs…")
        ds = self.load_dataset(vrt_dir)

        print("Processing ALS Biomass GFC dataset…")
        ds = self.process_dataset(
            ds,
            crs=crs,
            version=version,
            chunks=chunks,
        )

        encoding = {
            v: {
                "chunks": (chunks["y"], chunks["x"]),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for v in ds.data_vars
        }

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
