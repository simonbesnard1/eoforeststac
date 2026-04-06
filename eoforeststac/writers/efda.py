# eoforeststac/writers/efda.py

from __future__ import annotations

import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Sequence

import numpy as np
import rioxarray
import xarray as xr
import zarr

from eoforeststac.core.zarr import DEFAULT_COMPRESSOR
from eoforeststac.writers.base import BaseZarrWriter


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
          disturbance_occurrence(time, y, x)
          disturbance_agent(time, y, x)

    Strategy:
      - stream year-by-year and append along time (no concat, no huge lists)
      - consolidate metadata at end to produce .zmetadata
    """

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
        if not tif_path.exists():
            raise FileNotFoundError(f"EFDA GeoTIFF not found: {tif_path}")

        # mask_and_scale=False avoids carrying add_offset/scale_factor semantics into attrs
        da = (
            rioxarray.open_rasterio(
                tif_path,
                chunks={"y": chunks["y"], "x": chunks["x"]},
                mask_and_scale=False,
            )
            .squeeze(drop=True)
            .rename(var_name)
        )

        # Attach time coordinate and keep it as length-1 dimension
        da = da.assign_coords(time=np.datetime64(f"{year}-01-01")).expand_dims("time")
        return da.astype("int16")

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
        dtype: str = "int16",
        forest_mask_path: Optional[str] = None,
        _FillValue: int = -9999,
    ) -> xr.Dataset:
        """
        Build a 1-year Dataset(time=1, y, x) containing both vars.

        If forest_mask_path is provided, disturbance_occurrence will be:
          - 1  where disturbed forest (forest_mask == 1 and disturbance == 1)
          - 0  where undisturbed forest (forest_mask == 1 and disturbance == 0)
          - _FillValue (NaN sentinel) where not forest (forest_mask != 1)
        """
        da_mosaic = self._open_year_da(
            mosaic_dir, year, mosaic_pattern, "disturbance_occurrence", chunks=chunks
        )
        da_agent = self._open_year_da(
            agent_dir, year, agent_pattern, "disturbance_agent", chunks=chunks
        )

        forest_mask_raw = (
            rioxarray.open_rasterio(
                Path(forest_mask_path),
                chunks={"y": chunks["y"], "x": chunks["x"]},
                masked=True,  # ← nodata → NaN, enabling domain detection
            )
            .squeeze(drop=True)
            .astype("int16")
        )

        # 1 = disturbed forest, 0 = undisturbed forest, _FillValue = non-forest OR outside domain
        da_mosaic = da_mosaic.where(forest_mask_raw == 1, other=_FillValue).astype(
            dtype
        )
        da_agent = da_agent.where(forest_mask_raw == 1, other=_FillValue).astype(dtype)

        ds = xr.Dataset(
            {
                "disturbance_occurrence": da_mosaic,
                "disturbance_agent": da_agent,
            }
        )

        # CRS once
        ds = self.set_crs(ds, crs=crs)

        # enforce chunk alignment (time=1 always)
        ds = ds.chunk(
            {
                "time": 1,
                "y": chunks["y"],
                "x": chunks["x"],
            }
        )

        # Coordinate attrs (projected LAEA meters)
        if "x" in ds.coords:
            ds["x"].attrs.update(
                {
                    "long_name": "Projected x coordinate (LAEA Europe)",
                    "standard_name": "projection_x_coordinate",
                    "units": "m",
                    "axis": "X",
                }
            )
        if "y" in ds.coords:
            ds["y"].attrs.update(
                {
                    "long_name": "Projected y coordinate (LAEA Europe)",
                    "standard_name": "projection_y_coordinate",
                    "units": "m",
                    "axis": "Y",
                }
            )

        return ds

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def add_metadata(
        self, ds: xr.Dataset, _FillValue: int, crs: str, version: str = "1.0"
    ) -> xr.Dataset:
        """
        Add variable + global metadata.

        Note: _FillValue is intentionally NOT written into variable attrs here.
        It is owned exclusively by the encoding dict and will be serialized
        correctly by xarray via make_encoding(). Writing it into attrs as well
        causes xarray's CF encoder to raise a ValueError.
        """

        if "disturbance_occurrence" in ds:
            ds["disturbance_occurrence"].attrs.update(
                {
                    "long_name": "EFDA forest disturbance occurrence",
                    "description": "Annual forest disturbance occurrence mosaic from the European Forest Disturbance Atlas (EFDA).",
                    "units": "binary",
                    "flag_values": [0, 1],
                    "flag_meanings": "no_disturbance disturbance",
                    "grid_mapping": "spatial_ref",
                }
            )

        if "disturbance_agent" in ds:
            ds["disturbance_agent"].attrs.update(
                {
                    "long_name": "EFDA disturbance agent",
                    "description": (
                        "Causal agent of forest disturbance following the EFDA classification."
                    ),
                    "units": "categorical",
                    "flag_values": [0, 1, 2, 3, 4],
                    "flag_meanings": "no_disturbance wind_bark_beetle fire harvest mixed",
                    "flag_descriptions": "No Disturbance, Wind and bark beetle disturbance complex; Wildfire-related disturbance; Planned or salvage logging; Mixed agents (more than one disturbance agent occurred)",
                    "grid_mapping": "spatial_ref",
                }
            )

        # Global attributes (optional but recommended)
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
            "version": version,
            "doi": "10.5281/zenodo.13333034",
            "references": "Viana-Soto & Senf (2024) European Forest Disturbance Atlas; dataset available at https://doi.org/10.5281/zenodo.13333034",
            "institution": "Technical University of Munich (Earth Observation for Ecosystem Management)",
            "contact": "Alba Viana-Soto & Cornelius Senf",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "spatial_resolution": "30 m",
            "spatial_ref": crs,
        }

        self.set_global_metadata(ds, meta)

        return ds

    # ------------------------------------------------------------------
    # Zarr encoding
    # ------------------------------------------------------------------
    def make_encoding(
        self, chunks: Dict[str, int], _FillValue: int = -9999
    ) -> Dict[str, Dict]:
        zchunks = (1, chunks["y"], chunks["x"])

        return {
            "disturbance_occurrence": {
                "dtype": "int16",
                "chunks": zchunks,
                "compressor": DEFAULT_COMPRESSOR,
                "_FillValue": np.int16(_FillValue),
            },
            "disturbance_agent": {
                "dtype": "int16",
                "chunks": zchunks,
                "compressor": DEFAULT_COMPRESSOR,
                "_FillValue": np.int16(_FillValue),
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
        version: str = "2.1.1",
        mosaic_pattern: str = "{year}_disturb_mosaic_v211_22_epsg3035.tif",
        agent_pattern: str = "{year}_disturb_agent_v211_reclass_compv211_epsg3035.tif",
        crs: str = "EPSG:3035",
        _FillValue: int = -9999,
        forest_mask_path: str = None,
        chunks: Dict[str, int] = None,
        dtype: str = "int16",
        consolidate_at_end: bool = True,
    ) -> str:
        """
        Stream yearly EFDA GeoTIFFs into a single Zarr store along time.

        Parameters
        ----------
        forest_mask_path : str, optional
            Path to a forest mask GeoTIFF (1=forest, other=non-forest).
            When provided, disturbance_occurrence is:
              1  = disturbed forest
              0  = undisturbed forest
              _FillValue = non-forest (treated as NaN by xarray on read)
        """
        years = [int(y) for y in years]

        if chunks is None:
            chunks = {"y": 1000, "x": 1000}

        # fixed encoding for initialization
        encoding = self.make_encoding(chunks=chunks, _FillValue=_FillValue)

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
                forest_mask_path=forest_mask_path,
                _FillValue=_FillValue,
            )

            # Add human-readable metadata
            ds_year = self.add_metadata(
                ds_year, _FillValue=_FillValue, crs=crs, version=version
            )

            # Strip CF serialization attrs (_FillValue, scale_factor, add_offset,
            # missing_value) from variable attrs on every year.
            ds_year = self._strip_cf_serialization_attrs(ds_year)

            ds_year.to_zarr(
                store=store,
                mode="w" if i == 0 else "a",
                append_dim=None if i == 0 else "time",
                encoding=encoding if i == 0 else None,
                consolidated=False,
            )

            del ds_year
            gc.collect()

        if consolidate_at_end:
            zarr.consolidate_metadata(store)
        else:
            print(
                "EFDA: skipping metadata consolidation — call zarr.consolidate_metadata() manually before reading the store."
            )

        print(f"EFDA: done → {output_zarr}")
        return output_zarr
