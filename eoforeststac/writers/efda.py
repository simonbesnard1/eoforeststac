# eoforeststac/writers/efda.py

from __future__ import annotations

import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np
import rioxarray
import xarray as xr

from eoforeststac.core.zarr import DEFAULT_COMPRESSOR
from eoforeststac.writers.base import BaseZarrWriter


# These frequently come from GeoTIFF/rasterio and collide with xarray's CF encoding on append.
_CF_SERIALIZATION_ATTRS = {
    "add_offset",
    "scale_factor",
    "valid_range",
    "missing_value",
}


class EFDAWriter(BaseZarrWriter):
    """
    Writer for the European Forest Disturbance Atlas (EFDA).

    Native input:
      - yearly disturbance mosaic GeoTIFFs
      - yearly disturbance agent GeoTIFFs
    Projection:
      - EPSG:3035 (LAEA Europe)

    Output:
      - single Zarr store with variables:
          efda_disturbance(time, latitude, longitude)
          efda_agent(time, latitude, longitude)

    Strategy:
      - stream year-by-year and append along time (no concat, no huge lists)
      - consolidate metadata at end to produce .zmetadata
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _strip_cf_serialization_attrs(ds: xr.Dataset) -> xr.Dataset:
        """Remove CF serialization attrs that break append encoding."""
        ds = ds.copy()
        for v in ds.data_vars:
            for k in _CF_SERIALIZATION_ATTRS:
                ds[v].attrs.pop(k, None)
        return ds

    @staticmethod
    def _standardize_xy_names(obj: xr.Dataset | xr.DataArray) -> xr.Dataset | xr.DataArray:
        """
        Rename projected x/y dimensions to longitude/latitude (projected coords).
        """
        rename_dims = {}
        if "x" in obj.dims:
            rename_dims["x"] = "longitude"
        if "y" in obj.dims:
            rename_dims["y"] = "latitude"

        if rename_dims:
            obj = obj.rename(rename_dims)
            for old, new in rename_dims.items():
                if old in obj.coords:
                    obj = obj.rename({old: new})
        return obj

    # ------------------------------------------------------------------
    # Low-level IO (single year)
    # ------------------------------------------------------------------
    def _open_year_da(
        self,
        input_dir: str,
        year: int,
        pattern: str,
        var_name: str,
        chunks: Dict[str, int],
    ) -> xr.DataArray:
        """
        Open one yearly GeoTIFF lazily (dask-chunked) and return DataArray with dims (time, y, x).
        """
        tif_path = Path(input_dir) / pattern.format(year=year)

        # mask_and_scale=False avoids carrying add_offset/scale_factor semantics into attrs
        da = (
            rioxarray.open_rasterio(
                tif_path,
                chunks={"y": chunks["latitude"], "x": chunks["longitude"]},
                mask_and_scale=False,
            )
            .squeeze(drop=True)
            .rename(var_name)
        )

        # Attach time coordinate and keep it as length-1 dimension
        da = da.assign_coords(time=np.datetime64(f"{year}-01-01")).expand_dims("time")
        return da

    # ------------------------------------------------------------------
    # Build per-year dataset
    # ------------------------------------------------------------------
    def build_year_dataset(
        self,
        mosaic_dir: str,
        agent_dir: str,
        year: int,
        mosaic_pattern: str,
        agent_pattern: str,
        crs: str,
        chunks: Dict[str, int],
        dtype: str = "uint8",
    ) -> xr.Dataset:
        """
        Build a 1-year Dataset(time=1, latitude, longitude) containing both vars.
        """
        da_mosaic = self._open_year_da(
            mosaic_dir, year, mosaic_pattern, "efda_disturbance", chunks=chunks
        )
        da_agent = self._open_year_da(
            agent_dir, year, agent_pattern, "efda_agent", chunks=chunks
        )

        da_mosaic = self._standardize_xy_names(da_mosaic)
        da_agent = self._standardize_xy_names(da_agent)

        ds = xr.Dataset(
            {
                "efda_disturbance": da_mosaic,
                "efda_agent": da_agent,
            }
        )

        # CRS once
        ds = self.set_crs(ds, crs=crs)

        # dtype (categorical: keep small)
        ds = ds.astype(np.dtype(dtype))

        # enforce chunk alignment (time=1 always)
        ds = ds.chunk({"time": 1, "latitude": chunks["latitude"], "longitude": chunks["longitude"]})

        # Coordinate attrs (projected LAEA meters)
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

        return ds

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def add_metadata(self, ds: xr.Dataset, _FillValue: int, crs: str) -> xr.Dataset:
        """
        Add variable + global metadata. (Does not compute/load data.)
        """
        if "efda_disturbance" in ds:
            ds["efda_disturbance"].attrs.update({
                "long_name": "EFDA disturbance mosaic",
                "description": "Annual forest disturbance mosaic from EFDA.",
                "grid_mapping": "crs",
                "_FillValue": _FillValue,
            })

        if "efda_agent" in ds:
            ds["efda_agent"].attrs.update({
                "long_name": "EFDA disturbance agent",
                "description": "Disturbance agent classification (e.g., wind, bark beetle, harvest).",
                "grid_mapping": "crs",
                "_FillValue": _FillValue,
            })

        meta = {
                "title": "European Forest Disturbance Atlas (EFDA) v2.1.1",
                "description": (
                    "The European Forest Disturbance Atlas (EFDA) provides annual estimates "
                    "of forest disturbance occurrence, severity, and agent across continental "
                    "Europe from 1985 onward. Derived from a consistent Landsat data cube and "
                    "classification workflow developed by Viana-Soto and Senf, EFDA covers 38 "
                    "European countries in EPSG:3035 (ETRS89 / LAEA Europe), capturing disturbance "
                    "patterns such as natural disturbances and harvest events."
                ),
                "version": "2.1.1",
                "doi": "10.5281/zenodo.13333034",
                "references": "Viana-Soto & Senf (2024) European Forest Disturbance Atlas; dataset available at https://doi.org/10.5281/zenodo.13333034",
                "institution": "Technical University of Munich (Earth Observation for Ecosystem Management)",
                "contact": "Alba Viana-Soto & Cornelius Senf",
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "spatial_resolution": "30 m",
                "crs": crs,
                "_FillValue": _FillValue,
            }

        self.set_global_metadata(ds, meta)
        return ds

    # ------------------------------------------------------------------
    # Zarr encoding
    # ------------------------------------------------------------------
    def make_encoding(
        self,
        chunks: Dict[str, int],
        _FillValue: int,
        dtype: str,
    ) -> Dict[str, Dict]:
        """
        Zarr encoding expects tuples of ints, in *dimension order*.
        Here: (time, latitude, longitude) = (1, lat_chunk, lon_chunk)
        """
        zchunks = (1, chunks["latitude"], chunks["longitude"])
        dt = np.dtype(dtype)

        # Note: set dtype for both variables for consistency
        return {
            "efda_disturbance": {
                "chunks": zchunks,
                "compressor": DEFAULT_COMPRESSOR,
                "dtype": dt,
                "_FillValue": _FillValue,
            },
            "efda_agent": {
                "chunks": zchunks,
                "compressor": DEFAULT_COMPRESSOR,
                "dtype": dt,
                "_FillValue": _FillValue,
            },
        }

    # ------------------------------------------------------------------
    # Main write (STREAM + APPEND + FINAL CONSOLIDATION)
    # ------------------------------------------------------------------
    def write(
        self,
        mosaic_dir: str,
        agent_dir: str,
        years: Sequence[int],
        output_zarr: str,
        mosaic_pattern: str = "{year}_disturb_mosaic_v211_22_epsg3035.tif",
        agent_pattern: str = "{year}_disturb_agent_v211_reclass_compv211_epsg3035.tif",
        crs: str = "EPSG:3035",
        _FillValue: int = -9999,
        chunks: Optional[Dict[str, int]] = None,
        dtype: str = "uint32",
        consolidate_at_end: bool = True,
    ) -> str:
        """
        Stream yearly EFDA GeoTIFFs into a single Zarr store along time.

        Practical defaults:
          - _FillValue=0 (EFDA categories; GeoTIFF nodata is typically 0)
          - dtype=uint8   (small + categorical)
        """
        years = [int(y) for y in years]

        if chunks is None:
            chunks = {"latitude": 1000, "longitude": 1000}

        # fixed encoding for initialization
        encoding = self.make_encoding(chunks=chunks, _FillValue=_FillValue, dtype=dtype)

        # store
        store = self.make_store(output_zarr)

        for i, year in enumerate(years):
            print(f"EFDA: processing {year} ({i + 1}/{len(years)})")

            ds_year = self.build_year_dataset(
                mosaic_dir=mosaic_dir,
                agent_dir=agent_dir,
                year=year,
                mosaic_pattern=mosaic_pattern,
                agent_pattern=agent_pattern,
                crs=crs,
                chunks=chunks,
                dtype=dtype,
            )

            ds_year = self.add_metadata(ds_year, _FillValue=_FillValue, crs=crs)

            # Critical: prevent add_offset/scale_factor collisions on append
            ds_year = self._strip_cf_serialization_attrs(ds_year)

            if i == 0:
                # Only the first write gets encoding; later appends must NOT provide it
                print("EFDA: initializing Zarr (mode='w')")
                ds_year.to_zarr(
                    store=store,
                    mode="w",
                    encoding=encoding,
                    consolidated=False,
                )
            else:
                print("EFDA: appending along time (mode='a', append_dim='time')")
                ds_year.to_zarr(
                    store=store,
                    mode="a",
                    append_dim="time",
                    consolidated=False,
                )

            del ds_year
            gc.collect()

        if consolidate_at_end:
            print("EFDA: consolidating Zarr metadata (.zmetadata)")
            import zarr
            zarr.consolidate_metadata(store)

        print(f"EFDA: done → {output_zarr}")
        return output_zarr
