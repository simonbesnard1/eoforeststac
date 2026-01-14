# eoforeststac/writers/radd.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Union, Sequence

import numpy as np
import xarray as xr
import rioxarray  # needed for .rio accessor

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class RADDWriter(BaseZarrWriter):
    """
    Writer for RADD alert GeoTIFF where pixel values encode YYYYMMDD (e.g., 20220101).

    Produces:
      - radd_disturbance(time, latitude, longitude): monthly binary alert (0/1)
      - radd_day(time, latitude, longitude): day-of-month (1..31) of alert (optional)

    Forest mask is applied so only forest pixels can be disturbed; non-forest becomes fill_value.
    """

    def load_raster(self, path: str) -> xr.DataArray:
        """Load a raster lazily and standardize dims to (latitude, longitude)."""
        da = rioxarray.open_rasterio(
            path,
            masked=True,
            chunks="auto",
            cache=False,
        )
        # (band, y, x) -> (y, x) for single-band products
        if "band" in da.dims and da.sizes.get("band", 1) == 1:
            da = da.isel(band=0, drop=True)
        # standardize dim names
        da = da.rename({"y": "latitude", "x": "longitude"})
        return da

    @staticmethod
    def _yyyymmdd_to_year_month_day(date_int: xr.DataArray) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
        """
        Vectorized split of YYYYMMDD integer into (year, month, day), preserving laziness.
        """
        # Ensure integer-ish
        di = date_int.astype("int64")
        year = di // 10000
        month = (di // 100) % 100
        day = di % 100
        return year, month, day

    def process_dataset(
        self,
        radd_dates: xr.DataArray,
        forest_mask: xr.DataArray,
        *,
        forest_values: Union[int, Sequence[int]] = 1,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
        keep_day_layer: bool = True,
        time_start: Optional[str] = None,   # e.g. "2019-01-01"
        time_end: Optional[str] = None,     # e.g. "2025-12-01"
    ) -> xr.Dataset:
        """
        Build monthly time cube from YYYYMMDD-encoded alert raster.
        """

        # --- CRS on both rasters (metadata) ---
        radd_dates = radd_dates.rio.write_crs(crs, inplace=False)
        forest_mask = forest_mask.rio.write_crs(crs, inplace=False)

        # --- Align grids if needed ---
        # If you know they match exactly, you can remove this.
        forest_mask = forest_mask.rio.reproject_match(radd_dates)

        # --- Chunking override (optional) ---
        if chunks is not None:
            radd_dates = radd_dates.chunk({k: v for k, v in chunks.items() if k in radd_dates.dims})
            forest_mask = forest_mask.chunk({k: v for k, v in chunks.items() if k in forest_mask.dims})

        # --- Build forest boolean mask ---
        if isinstance(forest_values, (list, tuple, set)):
            is_forest = xr.zeros_like(forest_mask, dtype=bool)
            for v in forest_values:
                is_forest = is_forest | (forest_mask == v)
        else:
            is_forest = (forest_mask == forest_values)

        # --- Valid alert pixels: positive YYYYMMDD integers (exclude 0 / nodata) ---
        # masked=True already turns nodata to NaN; also guard against 0.
        valid_date = radd_dates.notnull() & (radd_dates > 0)

        # --- Decode year/month/day (lazily) ---
        year, month, day = self._yyyymmdd_to_year_month_day(radd_dates.where(valid_date))

        # --- Determine monthly range to emit ---
        # If user doesn't provide, infer from raster min/max year-month.
        # (We avoid computing full min/max if possible; but we do need a finite list of months.)
        if time_start is None or time_end is None:
            # compute minimal scalars; this will touch metadata & small reductions, not the whole array
            y_min = int(year.min().compute())
            y_max = int(year.max().compute())
            m_min = int(month.where(year == y_min).min().compute())
            m_max = int(month.where(year == y_max).max().compute())
            time_start = time_start or f"{y_min:04d}-{m_min:02d}-01"
            time_end = time_end or f"{y_max:04d}-{m_max:02d}-01"

        months = xr.cftime_range(start=time_start, end=time_end, freq="MS")
        # represent as numpy datetime64[ns] for consistency with your other products
        time_index = np.array([np.datetime64(f"{t.year:04d}-{t.month:02d}-01") for t in months])

        # --- Build monthly layers lazily ---
        monthly_binary = []
        monthly_day = [] if keep_day_layer else None

        for t in months:
            y = t.year
            m = t.month

            in_month = (year == y) & (month == m) & valid_date & is_forest

            # Binary disturbance for this month
            b = xr.where(in_month, 1, 0).astype("uint8")
            b = b.expand_dims(time=[np.datetime64(f"{y:04d}-{m:02d}-01")])
            monthly_binary.append(b)

            if keep_day_layer:
                # day-of-month for alerted pixels, fill elsewhere
                d = xr.where(in_month, day.astype("int16"), fill_value).astype("int16")
                d = d.expand_dims(time=[np.datetime64(f"{y:04d}-{m:02d}-01")])
                monthly_day.append(d)

        radd_disturb = xr.concat(monthly_binary, dim="time")
        ds = xr.Dataset({"radd_disturbance": radd_disturb})

        if keep_day_layer and monthly_day is not None:
            ds["radd_day"] = xr.concat(monthly_day, dim="time")

        # --- Apply fill_value to non-forest pixels (so “outside domain” isn’t 0) ---
        # For disturbance: set non-forest to fill_value (int16) to distinguish from “forest no-alert”
        ds["radd_disturbance"] = ds["radd_disturbance"].where(is_forest, other=fill_value).astype("int16")

        if keep_day_layer:
            ds["radd_day"] = ds["radd_day"].where(is_forest, other=fill_value).astype("int16")

        # --- Add CRS variable + global attrs using your helpers ---
        ds = self.set_crs(ds, crs=crs)

        # --- Variable metadata (CF-ish + legends) ---
        ds["radd_disturbance"].attrs.update({
            "long_name": "RADD forest disturbance alert (monthly)",
            "description": (
                "Monthly binary disturbance derived from RADD alerts. "
                "Pixel values are 1 if an alert occurred in that month (within the forest mask), else 0."
            ),
            "units": "binary",
            "flag_values": [0, 1],
            "flag_meanings": "no_disturbance disturbance",
            "grid_mapping": "crs",
            "_FillValue": fill_value,
        })

        if keep_day_layer:
            ds["radd_day"].attrs.update({
                "long_name": "RADD alert day-of-month",
                "description": (
                    "Day-of-month (1–31) of the alert date for pixels flagged as disturbed in the corresponding month. "
                    "Fill value elsewhere."
                ),
                "units": "day",
                "valid_min": 1,
                "valid_max": 31,
                "grid_mapping": "crs",
                "_FillValue": fill_value,
            })

        # --- Global metadata ---
        meta = {
            "title": "RADD Forest Disturbance Alerts (monthly binary)",
            "product_name": "RADD (Radar for Detecting Deforestation) Alerts",
            "version": version,
            "created_by": "EOForestSTAC processing",
            "creation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "crs": crs,
            "spatial_resolution": "native (see source)",
            "_FillValue": fill_value,
            "processing_notes": (
                "Input raster encodes alert date as integer YYYYMMDD. "
                "Output aggregates to monthly time steps; optional per-pixel day-of-month stored as radd_day."
            ),
        }
        self.set_global_metadata(ds, meta)

        return ds

    def write(
        self,
        radd_date_tif: str,
        forest_mask_tif: str,
        output_zarr: str,
        *,
        version: str = "1.0",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
        forest_values: Union[int, Sequence[int]] = 1,
        keep_day_layer: bool = True,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
    ) -> str:

        print("Loading RADD date raster…")
        radd_dates = self.load_raster(radd_date_tif)

        print("Loading forest mask…")
        forest_mask = self.load_raster(forest_mask_tif)

        print("Processing to monthly cube…")
        ds = self.process_dataset(
            radd_dates=radd_dates,
            forest_mask=forest_mask,
            forest_values=forest_values,
            fill_value=fill_value,
            crs=crs,
            version=version,
            chunks=chunks,
            keep_day_layer=keep_day_layer,
            time_start=time_start,
            time_end=time_end,
        )

        # Encoding: derive from actual dask chunks
        encoding = {}
        for var in ds.data_vars:
            chunk_tuple = tuple(ds[var].chunksizes[dim][0] for dim in ds[var].dims)
            encoding[var] = {
                "chunks": chunk_tuple,
                "compressor": DEFAULT_COMPRESSOR,
            }

        print("Writing Zarr…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
