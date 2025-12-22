import xarray as xr
import rioxarray
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class HansenGFCWriter(BaseZarrWriter):
    """
    Writer for Hansen Global Forest Change (GFC) v1.12.

    Native input:
      - One VRT per variable (global mosaics)

    Output:
      - Single Zarr store with harmonized Hansen variables

    Notes
    -----
    - Hansen `loss` encoding (1–24) is converted to calendar year (2001–2024)
      and stored as `loss_year` (int16).
    - This avoids implicit conventions and aligns with TMF-style year products.
    """

    # ------------------------------------------------------------------
    # Dataset definition
    # ------------------------------------------------------------------
    VARIABLES = {
        "tree_cover": {
            "dtype": "uint8",
            "long_name": "Tree canopy cover in year 2000",
            "description": (
                "Percent tree canopy cover for vegetation taller than 5 m "
                "in the year 2000."
            ),
            "units": "percent",
            "valid_min": 0,
            "valid_max": 100,
        },
        "gain": {
            "dtype": "uint8",
            "long_name": "Forest cover gain",
            "description": (
                "Forest gain indicator for the period 2000–2012. "
                "Value 1 indicates gain; 0 indicates no gain."
            ),
            "valid_min": 0,
            "valid_max": 1,
        },
        "data_mask": {
            "dtype": "uint8",
            "long_name": "Data availability mask",
            "description": (
                "Mask distinguishing land, water, and areas without "
                "valid observations."
            ),
        },
        # NOTE: loss is handled specially and converted to loss_year
        "loss": {
            "dtype": "uint8",
        },
    }

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_variable(self, vrt_path: Path, var_name: str) -> xr.DataArray:
        """
        Load a single Hansen VRT lazily.
        """
        da = (
            rioxarray.open_rasterio(
                vrt_path,
                masked=True,
                chunks="auto",
            )
            .squeeze(drop=True)
            .rename(var_name)
        )
        return da

    def load_dataset(self, vrt_dir: str) -> xr.Dataset:
        """
        Load all Hansen VRT layers into a single Dataset.
        """
        data_vars = {}
        vrt_dir = Path(vrt_dir)

        for var_name in self.VARIABLES:
            vrt_path = vrt_dir / f"{var_name}.vrt"
            if not vrt_path.exists():
                raise FileNotFoundError(f"Missing Hansen VRT: {vrt_path}")

            data_vars[var_name] = self.load_variable(vrt_path, var_name)

        return xr.Dataset(data_vars)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        crs: str = "EPSG:4326",
        fill_value: int = 0,
        version: str = "1.12",
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
        # Chunking
        # --------------------------------------------------
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --------------------------------------------------
        # Convert LOSS → LOSS_YEAR (core semantic fix)
        # --------------------------------------------------
        if "loss" in ds:
            loss = ds["loss"]

            loss_year = xr.where(
                loss > 0,
                loss + 2000,
                fill_value,
            ).astype("int16")

            loss_year.attrs.update({
                "long_name": "Year of forest cover loss",
                "description": (
                    "Calendar year in which forest loss occurred. "
                    "Derived from Hansen GFC loss encoding "
                    "(1–24 → 2001–2024)."
                ),
                "units": "year",
                "grid_mapping": "crs",
                "_FillValue": fill_value,
            })

            ds = ds.drop_vars("loss")
            ds["loss_year"] = loss_year

        # --------------------------------------------------
        # Handle remaining variables
        # --------------------------------------------------
        for name, meta in self.VARIABLES.items():
            if name == "loss":
                continue
            if name not in ds:
                continue

            ds[name] = ds[name].astype(meta["dtype"])
            ds[name].attrs.update({
                "long_name": meta["long_name"],
                "description": meta["description"],
                "grid_mapping": "crs",
                "_FillValue": fill_value,
            })

            if "units" in meta:
                ds[name].attrs["units"] = meta["units"]
            if "valid_min" in meta:
                ds[name].attrs["valid_min"] = meta["valid_min"]
            if "valid_max" in meta:
                ds[name].attrs["valid_max"] = meta["valid_max"]

        # --------------------------------------------------
        # Global metadata
        # --------------------------------------------------
        self.set_global_metadata(ds, {
            "title": "Global Forest Change (Hansen et al.)",
            "description": (
                "Global Forest Change dataset derived from Landsat imagery, "
                "quantifying tree cover, forest loss, and forest gain from "
                "2000 to 2024. Loss years are stored as calendar years "
                "(2001–2024)."
            ),
            "product_version": version,
            "institution": (
                "University of Maryland, Department of Geographical Sciences"
            ),
            "created_by": "Hansen et al.",
            "spatial_resolution": "30 m",
            "crs": crs,
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "references": (
                "https://storage.googleapis.com/earthenginepartners-hansen/"
                "GFC-2024-v1.12/download.html"
            ),
        })

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        vrt_dir: str,
        output_zarr: str,
        fill_value: int = 0,
        version: str = "1.12",
        chunks: Optional[Dict[str, int]] = None,
        crs: str = "EPSG:4326",
    ) -> str:
        """
        End-to-end Hansen GFC write:
            VRTs → Dataset → harmonized Zarr
        """

        if chunks is None:
            chunks = {"latitude": 2048, "longitude": 2048}

        print("Loading Hansen GFC VRTs…")
        ds = self.load_dataset(vrt_dir)

        print("Processing Hansen GFC dataset…")
        ds = self.process_dataset(
            ds,
            crs=crs,
            fill_value=fill_value,
            version=version,
            chunks=chunks,
        )

        encoding = {
            v: {
                "chunks": (chunks["latitude"], chunks["longitude"]),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for v in ds.data_vars
        }

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
