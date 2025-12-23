import xarray as xr
import numpy as np
import rioxarray
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class LiuBiomassWriter(BaseZarrWriter):
    """
    Writer for European canopy cover, canopy height and aboveground biomass
    derived from PlanetScope imagery (Liu et al., v0.1).

    Native input:
      - 3 GeoTIFFs at 30 m resolution (EPSG:3035)

    Variables:
      - aboveground_biomass (kg)
      - canopy_cover (%)
      - canopy_height (m)

    Notes:
      - Research-only use (Planet Labs Education & Research license)
      - No time dimension (reference year: 2019)
    """

    # ------------------------------------------------------------------
    # Dataset definition
    # ------------------------------------------------------------------
    VARIABLES = {
        "aboveground_biomass": {
            "filename": "planet_agb_30m_v0.1.tif",
            "dtype": "float32",
            "long_name": "Aboveground biomass",
            "description": (
                "Aboveground woody biomass estimated from canopy cover and "
                "canopy height using allometric equations."
            ),
            "units": "kg",
        },
        "canopy_cover": {
            "filename": "planet_canopy_cover_30m_v0.1.tif",
            "dtype": "uint8",
            "long_name": "Canopy cover",
            "description": (
                "Fractional canopy cover derived from PlanetScope imagery."
            ),
            "units": "percent",
            "valid_min": 0,
            "valid_max": 100,
        },
        "canopy_height": {
            "filename": "planet_canopy_height_30m_v0.1.tif",
            "dtype": "float32",
            "long_name": "Canopy height",
            "description": (
                "Mean canopy height derived from fusion of PlanetScope imagery "
                "and airborne LiDAR canopy height models."
            ),
            "units": "m",
        },
    }

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_variable(self, tif_path: Path, var_name: str) -> xr.DataArray:
        """
        Load a single GeoTIFF lazily.
        """
        return (
            rioxarray.open_rasterio(
                tif_path,
                masked=True,
                chunks="auto",
            )
            .squeeze(drop=True)
            .rename(var_name)
        )

    def load_dataset(self, data_dir: str) -> xr.Dataset:
        """
        Load all Liu biomass layers into a single Dataset.
        """
        data_vars = {}

        for var, meta in self.VARIABLES.items():
            tif_path = Path(data_dir) / meta["filename"]
            if not tif_path.exists():
                raise FileNotFoundError(f"Missing input file: {tif_path}")

            data_vars[var] = self.load_variable(tif_path, var)

        return xr.Dataset(data_vars)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        crs: str = "EPSG:3035",
        fill_value: int = 0,
        version: str = "0.1",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Harmonize CRS, dimensions, chunking and metadata.
        """

        # --------------------------------------------------
        # CRS
        # --------------------------------------------------
        ds = self.set_crs(ds, crs=crs)

        # --------------------------------------------------
        # Rename raster dims to spatial coordinates
        # --------------------------------------------------
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

        # --------------------------------------------------
        # Add reference time coordinate (single epoch)
        # --------------------------------------------------
        if "time" not in ds.coords:
            ds = ds.assign_coords(
                time=np.datetime64("2020-01-01")
            )
            
        # --------------------------------------------------
        # Chunking
        # --------------------------------------------------
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --------------------------------------------------
        # Variable handling
        # --------------------------------------------------
        for var, meta in self.VARIABLES.items():
            ds[var] = ds[var].astype(meta["dtype"])

            attrs = {
                "long_name": meta["long_name"],
                "description": meta["description"],
                "grid_mapping": "crs",
                "_FillValue": fill_value,
            }

            if "units" in meta:
                attrs["units"] = meta["units"]
            if "valid_min" in meta:
                attrs["valid_min"] = meta["valid_min"]
            if "valid_max" in meta:
                attrs["valid_max"] = meta["valid_max"]

            ds[var].attrs.update(attrs)

        # --------------------------------------------------
        # Global metadata
        # --------------------------------------------------
        self.set_global_metadata(ds, {
            "title": (
                "European canopy height, canopy cover and aboveground biomass "
                "(PlanetScope-derived)"
            ),
            "description": (
                "European canopy cover, canopy height and aboveground biomass maps "
                "derived from 3 m PlanetScope imagery and airborne LiDAR using deep "
                "learning. Biomass is estimated at 30 m resolution from canopy "
                "structure. Dataset accompanies the study "
                "'The overlooked contribution of trees outside forests to tree cover "
                "and woody biomass across Europe'.\n\n"
                "IMPORTANT: Restricted to research and scientific use only. "
                "Commercial use is prohibited under the Planet Labs Education & "
                "Research license."
            ),
            "version": version,
            "reference_year": 2019,
            "institution": "University of Copenhagen",
            "created_by": "Shan Liu et al.",
            "spatial_resolution": "30 m",
            "crs": crs,
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "references": "https://zenodo.org/records/8154445",
            "license": (
                "Restricted to research use only; Planet Labs Education & "
                "Research license applies."
            ),
            "contact": "sliu@ign.ku.dk; martin.brandt@mailbox.org",
        })

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        data_dir: str,
        output_zarr: str,
        fill_value: int = 0,
        version: str = "0.1",
        chunks: Optional[Dict[str, int]] = None,
        crs: str = "EPSG:3035",
    ) -> str:
        """
        End-to-end write:
            GeoTIFFs → Dataset → harmonized Zarr
        """

        if chunks is None:
            chunks = {"latitude": 2048, "longitude": 2048}

        print("Loading Liu biomass layers…")
        ds = self.load_dataset(data_dir)

        print("Processing dataset…")
        ds = self.process_dataset(
            ds,
            crs=crs,
            fill_value=fill_value,
            version=version,
            chunks=chunks,
        )

        encoding = {
            var: {
                "chunks": (chunks["latitude"], chunks["longitude"]),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
