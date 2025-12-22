import xarray as xr
import rioxarray
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class JRCTMFWriter(BaseZarrWriter):
    """
    Writer for Tropical Moist Forest (TMF) products (v1-2024).

    Native input:
      - One VRT per TMF layer (categorical / year-encoded rasters)

    Output:
      - Single Zarr store with multiple TMF variables
    """

    # ------------------------------------------------------------------
    # Dataset definition
    # ------------------------------------------------------------------
    VARIABLES = {
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
    # Load
    # ------------------------------------------------------------------
    def load_variable(self, vrt_path: Path, var_name: str) -> xr.DataArray:
        """
        Load a single TMF VRT lazily.
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
        Load all TMF VRT layers into a single Dataset.
        """
        data_vars = {}

        for var_name in self.VARIABLES:
            vrt_path = Path(vrt_dir) / f"{var_name}.vrt"
            if not vrt_path.exists():
                raise FileNotFoundError(f"Missing TMF VRT: {vrt_path}")

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
        version: str = "2024",
        chunks: Optional[Dict[str, int]] = None
    ) -> xr.Dataset:
        """
        Harmonize CRS, dimensions, chunking and metadata.
        """

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)

        # --- Rename raster dims ---
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

        # --- Variable handling ---
        for name, meta in self.VARIABLES.items():
            ds[name] = ds[name].astype(meta["dtype"])
            ds[name].attrs.update({
                "long_name": meta["long_name"],
                "description": meta["description"],
                "grid_mapping": "crs",
                "_FillValue": fill_value,
            })
            if "units" in meta:
                ds[name].attrs["units"] = meta["units"]

        # --- Attach legends (CF-safe) ---
        self._add_legends(ds)

        # --- Global metadata ---
        self.set_global_metadata(ds, {
            "title": "Tropical Moist Forest (TMF) Transition Maps v1-2024",
            "description": (
                "Global Tropical Moist Forest transition datasets describing "
                "deforestation, degradation, regrowth, and land-cover conversion "
                "from the 1990s to 2024."
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
    # Legends
    # ------------------------------------------------------------------
    def _add_legends(self, ds: xr.Dataset):
        """
        Attach categorical legends as JSON-style attributes.
        """

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
            21: "Degraded forest (short disturbance, <2015)",
            22: "Degraded forest (short disturbance, 2015–2023)",
            23: "Degraded forest (long disturbance, <2015)",
            24: "Degraded forest (long disturbance, 2015–2023)",
            25: "Degraded forest (2/3 periods, <2015)",
            26: "Degraded forest (2/3 periods, 2015–2023)",
            31: "Old forest regrowth",
            32: "Young forest regrowth",
            33: "Very young forest regrowth",
            41: "Deforestation (<2014)",
            42: "Deforestation (2014–2021)",
            51: "Deforestation (2022)",
            52: "Deforestation (2023)",
            53: "Deforestation (2024)",
            54: "Degradation (2024)",
            61: "Degraded mangroves (<2015)",
            62: "Recently degraded mangroves",
            63: "Mangrove regrowth (≥10 years)",
            64: "Mangrove regrowth (≥3 years)",
            65: "Mangrove deforested (<2014)",
            66: "Mangrove deforested (2015–2022)",
            67: "Mangrove disturbed (2023–2024)",
            71: "Permanent water",
            72: "Seasonal water",
            73: "Deforestation → permanent water",
            74: "Deforestation → seasonal water",
            81: "Old plantation",
            82: "Plantation regrowth (<2015)",
            83: "Plantation regrowth (2015–2021)",
            84: "Conversion to plantation (<2014)",
            85: "Conversion to plantation (2015–2021)",
            86: "Recent conversion to plantation (2022–2024)",
            91: "Other land cover (no afforestation)",
            92: "Young afforestation",
            93: "Old afforestation",
            94: "Water → forest regrowth",
        }

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        vrt_dir: str,
        output_zarr: str,
        fill_value: int = 0,
        version: str = "2024",
        chunks: Optional[Dict[str, int]] = None,
        crs: str = "EPSG:4326",
    ) -> str:
        """
        End-to-end TMF write:
            VRTs → Dataset → harmonized Zarr
        """

        if chunks is None:
            chunks = {"latitude": 2048, "longitude": 2048}

        print("Loading TMF VRTs…")
        ds = self.load_dataset(vrt_dir)

        print("Processing TMF dataset…")
        ds = self.process_dataset(ds, crs=crs, chunks=chunks, version=version)

        encoding = {
            v: {
                "chunks": (chunks["latitude"], chunks["longitude"]),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for v in ds.data_vars
        }
        
        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
