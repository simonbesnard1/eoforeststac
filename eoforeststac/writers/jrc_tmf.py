import xarray as xr
import rioxarray
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class JRCTMFWriter(BaseZarrWriter):
    """
    Writer for Tropical Moist Forest (TMF) products (v1-2024).

    Native input:
      - Static TMF layers as VRTs
      - AnnualChange as yearly VRTs (1990–2024)

    Output:
      - One Zarr store with:
          * static TMF layers (no time dim)
          * AnnualChange(time, latitude, longitude)
    """

    # ------------------------------------------------------------------
    # Static variables
    # ------------------------------------------------------------------
    STATIC_VARIABLES = {
        "DeforestationYear": {
            "dtype": "int16",
            "long_name": "Year of deforestation",
            "description": "Year when deforestation started.",
            "units": "year",
        },
        "DegradationYear": {
            "dtype": "int16",
            "long_name": "Year of degradation",
            "description": "Year when forest degradation started.",
            "units": "year",
        },
        "TransitionMap_MainClasses": {
            "dtype": "uint8",
            "long_name": "TMF transition map – main classes",
            "description": "Main land-cover transition classes for Tropical Moist Forests.",
        },
        "TransitionMap_Subtypes": {
            "dtype": "uint8",
            "long_name": "TMF transition map – subtypes",
            "description": "Detailed land-cover transition subtypes for Tropical Moist Forests.",
        },
        "UndisturbedDegradedForest": {
            "dtype": "uint8",
            "long_name": "Undisturbed or degraded forest mask",
            "description": "Binary mask distinguishing undisturbed and degraded TMF.",
        },
    }

    # ------------------------------------------------------------------
    # Annual change variable
    # ------------------------------------------------------------------
    ANNUAL_CHANGE = {
        "name": "AnnualChange",
        "dtype": "uint8",
        "years": list(range(1990, 2025)),
        "long_name": "Annual Tropical Moist Forest change",
        "description": (
            "Annual land-cover state for Tropical Moist Forests, "
            "derived from Landsat time series."
        ),
    }

    # ------------------------------------------------------------------
    # Load helpers
    # ------------------------------------------------------------------
    def _load_vrt(self, vrt_path: Path, name: str) -> xr.DataArray:
        da = (
            rioxarray.open_rasterio(
                vrt_path,
                masked=True,
                chunks="auto",
            )
            .squeeze(drop=True)
            .rename(name)
        )
        return da

    # ------------------------------------------------------------------
    # Load dataset
    # ------------------------------------------------------------------
    def load_dataset(
        self,
        vrt_dir: str,
        annual_dir: Optional[str] = None,
    ) -> xr.Dataset:
        """
        Load static TMF layers and optional annual change layers.
        """
        data_vars = {}
        vrt_dir = Path(vrt_dir)

        # --- static layers ---
        for name in self.STATIC_VARIABLES:
            path = vrt_dir / f"{name}.vrt"
            if not path.exists():
                raise FileNotFoundError(f"Missing TMF VRT: {path}")
            data_vars[name] = self._load_vrt(path, name)

        ds = xr.Dataset(data_vars)

        # --- annual change ---
        if annual_dir is not None:
            annual_dir = Path(annual_dir)
            annual_layers = []

            for year in self.ANNUAL_CHANGE["years"]:
                path = annual_dir / f"AnnualChange_{year}.vrt"
                if not path.exists():
                    raise FileNotFoundError(f"Missing AnnualChange VRT: {path}")

                da = self._load_vrt(path, "AnnualChange")
                da = da.expand_dims(
                    time=[np.datetime64(f"{year}-01-01")]
                )
                annual_layers.append(da)

            ds["AnnualChange"] = xr.concat(
                annual_layers,
                dim="time"
            )

        return ds

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        crs: str = "EPSG:4326",
        fill_value: int = 0,
        version: str = "2024",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)

        # --- Rename dims ---
        rename_dims = {}
        if "x" in ds.dims:
            rename_dims["x"] = "longitude"
        if "y" in ds.dims:
            rename_dims["y"] = "latitude"

        if rename_dims:
            ds = ds.rename(rename_dims)
            for o, n in rename_dims.items():
                if o in ds.coords:
                    ds = ds.rename({o: n})

        # --- Chunking ---
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --- static variables ---
        for name, meta in self.STATIC_VARIABLES.items():
            ds[name] = ds[name].astype(meta["dtype"])
            ds[name].attrs.update({
                "long_name": meta["long_name"],
                "description": meta["description"],
                "grid_mapping": "crs",
                "_FillValue": fill_value,
            })
            if "units" in meta:
                ds[name].attrs["units"] = meta["units"]

        # --- annual change ---
        if "AnnualChange" in ds:
            ds["AnnualChange"] = ds["AnnualChange"].astype(
                self.ANNUAL_CHANGE["dtype"]
            )
            ds["AnnualChange"].attrs.update({
                "long_name": self.ANNUAL_CHANGE["long_name"],
                "description": self.ANNUAL_CHANGE["description"],
                "grid_mapping": "crs",
                "_FillValue": fill_value,
            })
            ds["AnnualChange"].attrs["legend"] = {
                1: "Undisturbed Tropical Moist Forest",
                2: "Degraded TMF",
                3: "Deforested land",
                4: "Forest regrowth",
                5: "Permanent or seasonal water",
                6: "Other land cover",
            }

        # --- legends for static maps ---
        self._add_legends(ds)

        # --- global metadata ---
        self.set_global_metadata(ds, {
            "title": "Tropical Moist Forest (TMF) products v1-2024",
            "description": (
                "Global Tropical Moist Forest datasets describing "
                "deforestation, degradation, regrowth and annual land-cover "
                "dynamics from 1990 to 2024."
            ),
            "institution": "Joint Research Centre (JRC)",
            "product_version": version,
            "spatial_resolution": "30 m",
            "crs": crs,
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "references": "https://forobs.jrc.ec.europa.eu/TMF",
        })

        return ds

    # ------------------------------------------------------------------
    # Legends (static)
    # ------------------------------------------------------------------
    def _add_legends(self, ds: xr.Dataset):
        ds["TransitionMap_MainClasses"].attrs["legend"] = {
            10: "Undisturbed Tropical Moist Forest",
            20: "Degraded TMF",
            30: "TMF regrowth",
            41: "Deforested → plantation",
            42: "Deforested → water",
            43: "Deforested → other land cover",
            50: "Ongoing deforestation or degradation (2022–2024)",
            60: "Permanent or seasonal water",
            70: "Other land cover (including afforestation)",
        }

        ds["TransitionMap_Subtypes"].attrs["legend"] = {
            10: "Undisturbed TMF",
            11: "Bamboo-dominated forest",
            12: "Undisturbed mangroves",
            21: "Degraded forest (<2015)",
            22: "Degraded forest (2015–2023)",
            23: "Long degradation (<2015)",
            24: "Long degradation (2015–2023)",
            31: "Old forest regrowth",
            32: "Young forest regrowth",
            33: "Very young forest regrowth",
            41: "Deforestation (<2014)",
            42: "Deforestation (2014–2021)",
            51: "Deforestation (2022)",
            52: "Deforestation (2023)",
            53: "Deforestation (2024)",
        }

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        vrt_dir: str,
        output_zarr: str,
        annual_dir: Optional[str] = None,
        fill_value: int = 0,
        version: str = "2024",
        chunks: Optional[Dict[str, int]] = None,
        crs: str = "EPSG:4326",
    ) -> str:

        if chunks is None:
            chunks = {'time':-1, "latitude": 2048, "longitude": 2048}

        print("Loading TMF VRTs…")
        ds = self.load_dataset(vrt_dir, annual_dir=annual_dir)

        print("Processing TMF dataset…")
        ds = self.process_dataset(
            ds,
            crs=crs,
            chunks=chunks,
            version=version,
            fill_value=fill_value,
        )

        encoding = {
            v: {
                "chunks": (
                    (chunks["time"], chunks["latitude"], chunks["longitude"])
                    if "time" in ds[v].dims
                    else (chunks["latitude"], chunks["longitude"])
                ),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for v in ds.data_vars
        }
        
        print("Writing TMF Zarr…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
