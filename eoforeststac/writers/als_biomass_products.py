import xarray as xr
import rioxarray

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class ALSBiomassProductsWriter(BaseZarrWriter):
    """
    Writer for ALS Biomass Products (v1.0).

    Native input:
        - One GeoTIFF per year

    Output:
        - Single Zarr store
        - One variable per year:
          biomass_2019(y, x)
          biomass_2020(y, x)
          ...
    """

    VARIABLES = {
        "biomass": {
            "dtype": "float32",
            "long_name": "Forest biomass",
            "description": (
                "Forest biomass derived from airborne laser scanning."
            ),
        }
    }

    def load_single_dataset(
        self,
        tif_path: Path,
    ) -> xr.DataArray:
        """
        Load a single yearly ALS Biomass GeoTIFF lazily.
        """

        da = (
            rioxarray.open_rasterio(
                tif_path,
                masked=True,
                chunks="auto",
            )
            .squeeze(drop=True)
            .rename("biomass")
        )

        return da

    def load_dataset(
        self,
        data_dir: str,
    ) -> xr.Dataset:
        """
        Load all yearly ALS Biomass GeoTIFFs into
        a single Dataset.

        Each year remains on its original spatial grid.
        """

        data_dir = Path(data_dir)

        tif_files = sorted(
            data_dir.glob("*_biomass.tif")
        )

        if not tif_files:
            raise FileNotFoundError(
                f"No biomass GeoTIFFs found in {data_dir}"
            )

        data_vars = {}

        for tif_path in tif_files:
            # Example:
            # Finland_2019_biomass.tif
            year = int(
                tif_path.stem.split("_")[1]
            )

            print(
                f"Loading biomass for {year}: "
                f"{tif_path.name}"
            )

            da = self.load_single_dataset(
                tif_path
            )

            # Keep each year's original spatial grid.
            data_vars[f"biomass_{year}"] = da

        return xr.Dataset(data_vars)

    def process_dataset(
        self,
        ds: xr.Dataset,
        crs: str,
        version: str = "1.0",
    ) -> xr.Dataset:

        ds = self.set_crs(
            ds,
            crs=crs,
        )

        for name in ds.data_vars:
            if not name.startswith("biomass_"):
                continue

            ds[name] = ds[name].astype(
                self.VARIABLES["biomass"]["dtype"]
            )

            ds[name].attrs.update(
                {
                    "description": (
                        self.VARIABLES["biomass"]["description"]
                    ),
                    "long_name": (
                        self.VARIABLES["biomass"]["long_name"]
                    ),
                    "grid_mapping": "spatial_ref",
                }
            )

        self.set_global_metadata(
            ds,
            {
                "title": "ALS-derived biomass (Europe)",
                "description": (
                    "Biomass maps at 10 m resolution derived "
                    "from National Forest Inventories and "
                    "Airborne Laser Scanning in selected "
                    "European countries (2006, 2011-2024)."
                ),
                "product_version": version,
                "spatial_resolution": "10 m",
                "spatial_ref": crs,
                "creation_date": datetime.now().strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
        )

        return ds

    def write(
        self,
        data_dir: str,
        product: str,
        crs: str,
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:

        if chunks is None:
            chunks = {
                "x": 1024,
                "y": 1024,
            }

        print(
            "Loading ALS Biomass GeoTIFFs..."
        )

        ds = self.load_dataset(
            data_dir
        )

        print(
            "Processing ALS Biomass dataset..."
        )

        ds = self.process_dataset(
            ds,
            crs=crs,
            version=version,
        )

        ds = ds.chunk({
            "x": chunks["x"],
            "y": chunks["y"],
        })

        encoding = {
            name: {
                "compressor": DEFAULT_COMPRESSOR,
            }
            for name in ds.data_vars
        }

        output_zarr = (
            "dog.atlaseo-glm.eo-gridded-data/"
            "collections/ALS_BIOMASS_PRODUCTS/"
            + product
        )

        print(
            "Writing Zarr to Ceph/S3..."
        )

        return self.write_to_zarr(
            ds,
            output_zarr,
            encoding=encoding,
        )