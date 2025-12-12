import xarray as xr
import rioxarray
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Sequence, Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class EFDAWriter(BaseZarrWriter):
    """
    Writer for the European Forest Disturbance Atlas (EFDA).

    Native input:
      - yearly disturbance mosaic GeoTIFFs
      - yearly disturbance agent GeoTIFFs
    Projection:
      - EPSG:3035 (LAEA Europe)
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def _open_year(
        self,
        input_dir: str,
        year: int,
        pattern: str,
        var_name: str,
        chunks: Dict[str, int],
    ) -> xr.DataArray:
        """
        Load one yearly GeoTIFF lazily and attach time coordinate.
        """
        tif_path = Path(input_dir) / pattern.format(year=year)

        da = (
            rioxarray.open_rasterio(tif_path, chunks=chunks)
            .squeeze(drop=True)
            .rename(var_name)
        )

        da = da.assign_coords(time=np.datetime64(f"{year}-01-01"))
        da = da.expand_dims("time")

        return da

    def load_dataset(
        self,
        mosaic_dir: str,
        agent_dir: str,
        years: Sequence[int],
        mosaic_pattern: str,
        agent_pattern: str,
        chunks: Dict[str, int],
    ) -> xr.Dataset:
        """
        Load all EFDA yearly layers and concatenate along time.
        """

        mosaics = [
            self._open_year(
                mosaic_dir,
                int(year),
                mosaic_pattern,
                "efda_disturbance",
                chunks,
            )
            for year in years
        ]

        agents = [
            self._open_year(
                agent_dir,
                int(year),
                agent_pattern,
                "efda_agent",
                chunks,
            )
            for year in years
        ]

        return xr.Dataset(
            {
                "efda_disturbance": xr.concat(mosaics, dim="time"),
                "efda_agent": xr.concat(agents, dim="time"),
            }
        )

    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:3035",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Apply fill values, CRS, coordinate harmonization,
        chunking, and metadata.
        """
    
        # --- Fill values + dtype ---
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int16")
    
        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)
    
        # ------------------------------------------------------------------
        # Rename projected x/y to longitude/latitude (explicitly projected)
        # ------------------------------------------------------------------
        rename_dims = {}
        if "x" in ds.dims:
            rename_dims["x"] = "longitude"
        if "y" in ds.dims:
            rename_dims["y"] = "latitude"
    
        if rename_dims:
            ds = ds.rename(rename_dims)
    
            # rename coordinates explicitly
            for old, new in rename_dims.items():
                if old in ds.coords:
                    ds = ds.rename({old: new})
    
        # --- Coordinate metadata (VERY IMPORTANT) ---
        if "longitude" in ds.coords:
            ds["longitude"].attrs.update({
                "long_name": "Projected x coordinate (LAEA Europe)",
                "standard_name": "projection_x_coordinate",
                "units": "m",
                "axis": "X",
            })
    
        if "latitude" in ds.coords:
            ds["latitude"].attrs.update({
                "long_name": "Projected y coordinate (LAEA Europe)",
                "standard_name": "projection_y_coordinate",
                "units": "m",
                "axis": "Y",
            })
    
        # --- Chunking (after renaming!) ---
        if chunks is not None:
            ds = ds.chunk(chunks)
    
        # --- Variable metadata ---
        ds["efda_disturbance"].attrs.update({
            "long_name": "EFDA disturbance mosaic",
            "description": "Annual forest disturbance mosaic from EFDA.",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })
    
        ds["efda_agent"].attrs.update({
            "long_name": "EFDA disturbance agent",
            "description": (
                "Disturbance agent classification "
                "(e.g., wind, bark beetle, harvest)."
            ),
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })
    
        # --- Global metadata ---
        meta = {
            "title": "European Forest Disturbance Atlas (EFDA)",
            "product_name": "European Forest Disturbance Atlas",
            "institution": "Joint Research Centre (JRC)",
            "created_by": "EFDA consortium",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "spatial_resolution": "100 m",
            "crs": crs,
            "_FillValue": fill_value,
        }
    
        self.set_global_metadata(ds, meta)
    
        return ds


    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        mosaic_dir: str,
        agent_dir: str,
        years: Sequence[int],
        output_zarr: str,
        mosaic_pattern: str = "{year}_disturb_mosaic_v211_22_epsg3035.tif",
        agent_pattern: str = "{year}_disturb_agent_v211_reclass_compv211_epsg3035.tif",
        fill_value: int = -9999,
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        End-to-end transform:
            yearly GeoTIFFs → Dataset → harmonization → Zarr-on-Ceph
        """

        if chunks is None:
            chunks = {"time": len(years), "y": 1000, "x": 1000}

        print("Loading EFDA dataset…")
        ds = self.load_dataset(
            mosaic_dir=mosaic_dir,
            agent_dir=agent_dir,
            years=years,
            mosaic_pattern=mosaic_pattern,
            agent_pattern=agent_pattern,
            chunks={"y": chunks["y"], "x": chunks["x"]},
        )

        print("Processing dataset…")
        ds = self.process_dataset(
            ds,
            fill_value=fill_value,
            chunks=chunks,
        )

        # 🔑 Zarr encoding derived from actual Dask chunks
        encoding = {
                var: {
                    "chunks": (
                        chunks["latitude"],
                        chunks["longitude"],
                        chunks["time"],
                    ),
                    "compressor": DEFAULT_COMPRESSOR,
                }
                for var in ds.data_vars
            }

        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
