from __future__ import annotations

import gc
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import xarray as xr
import rioxarray
import zarr

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class RADDEuropeWriter(BaseZarrWriter):
    """
    Streaming writer for RADD Europe alert dates (YYddd) + forest mask (0/1),
    following the EFDA pattern: append along time with to_zarr.

    Output (Zarr)
    -------------
    disturbance_occurrence(time, latitude, longitude) int16
      - 1 only in the month of the alert for forest pixels
      - 0 otherwise within valid domain
      - _FillValue outside valid domain

    forest_mask(latitude, longitude) int16
      - 0/1 within valid domain
      - _FillValue outside valid domain

    CRS: EPSG:3035
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_variable(
        self,
        vrt: Path,
        name: str,
        *,
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.DataArray:
        """
        Load VRT lazily. Apply spatial chunking at read time to avoid rechunking later.
        """
        rio_chunks = None
        if chunks:
            rio_chunks = {}
            if "longitude" in chunks:
                rio_chunks["x"] = chunks["longitude"]
            if "latitude" in chunks:
                rio_chunks["y"] = chunks["latitude"]

        da = (
            rioxarray.open_rasterio(
                vrt,
                masked=True,
                chunks=rio_chunks if rio_chunks else "auto",
            )
            .squeeze(drop=True)
            .rename(name)
        )
        return da

    def load_dataset(
        self,
        alert_vrt: str,
        mask_vrt: str,
        *,
        spatial_chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        return xr.Dataset(
            {
                "alert_code": self.load_variable(Path(alert_vrt), "alert_code", chunks=spatial_chunks),
                "forest_mask_raw": self.load_variable(Path(mask_vrt), "forest_mask_raw", chunks=spatial_chunks),
            }
        )

    # ------------------------------------------------------------------
    # Decode YYddd → month index (int32 months since 1970-01)
    # ------------------------------------------------------------------
    @staticmethod
    def _yydoy_to_month_index(block: np.ndarray) -> np.ndarray:
        """
        Convert YYddd codes into a month index (datetime64[M] integer).
        YY=20, ddd=004 -> 2020-01 -> month index
    
        Output:
          int32 month index for valid pixels, -1 for 0/invalid.
        """
        arr = block.astype(np.int64, copy=False)
        out = np.full(arr.shape, -1, dtype=np.int32)
    
        valid = np.isfinite(arr) & (arr > 0)
        if not np.any(valid):
            return out
    
        yy = (arr[valid] // 1000).astype(np.int64)
        doy = (arr[valid] % 1000).astype(np.int64)
        year = 2000 + yy
    
        yyyyddd = year * 1000 + doy  # e.g., 2020004
        s = np.char.zfill(yyyyddd.astype(str), 7)
    
        dt = pd.to_datetime(s, format="%Y%j", errors="coerce")
        out[valid] = dt.to_numpy(dtype="datetime64[M]").astype(np.int32)
    
        return out


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _rename_xy_to_latlon(ds: xr.Dataset) -> xr.Dataset:
        rename = {}
        if "x" in ds.dims:
            rename["x"] = "longitude"
        if "y" in ds.dims:
            rename["y"] = "latitude"
        if rename:
            ds = ds.rename(rename)
            for old, new in rename.items():
                if old in ds.coords:
                    ds = ds.rename({old: new})
        return ds

    @staticmethod
    def _drop_fillvalue_attr(ds: xr.Dataset) -> xr.Dataset:
        """
        xarray treats _FillValue as a serialization/encoding field.
        Keep it in encoding, NOT in attrs, to avoid ValueError.
        """
        for v in ds.data_vars:
            ds[v].attrs.pop("_FillValue", None)
        return ds
    
    def _strip_cf_serialization_attrs(self, ds: xr.Dataset) -> xr.Dataset:
        """
        Remove CF/Zarr serialization-related attributes that must NOT
        be present when appending to an existing Zarr store.
        """
        STRIP_KEYS = {
            "_FillValue",
            "missing_value",
            "scale_factor",
            "add_offset",
        }
    
        for var in ds.data_vars:
            for key in STRIP_KEYS:
                ds[var].attrs.pop(key, None)
    
        return ds

    def build_static_layers(self, ds: xr.Dataset, fill_value: int = -9999):
        fm_raw = ds["forest_mask_raw"]
    
        # masked=True often yields NaN outside-domain
        domain_valid = xr.ufuncs.isfinite(fm_raw)
    
        # Forest mask: keep 0/1 in-domain, fill_value outside-domain (and for weird values)
        forest_mask = (
            fm_raw
            .where(domain_valid, other=fill_value)
            .astype("int16")
        )
        forest_mask = (
            forest_mask
            .where((forest_mask == 0) | (forest_mask == 1), other=fill_value)
            .astype("int16")
        )
    
        # Month index from alert_code (note: cast to int32 here is OK because 0 is valid, NaNs should be handled)
        # But if alert_code contains NaNs, handle them before astype:
        alert_code_int = (
            ds["alert_code"]
            .where(xr.ufuncs.isfinite(ds["alert_code"]), other=0)  # 0 means "no alert"
            .astype("int32")
        )
    
        alert_month_index = xr.apply_ufunc(
            self._yydoy_to_month_index,
            alert_code_int,
            dask="parallelized",
            output_dtypes=[np.int32],
        )
    
        # Keep native YYddd as a 2D layer:
        # Replace NaNs FIRST, then cast. Use int16 (fits both YYddd and -9999).
        alert_yydoy = (
            ds["alert_code"]
            .where(xr.ufuncs.isfinite(ds["alert_code"]), other=fill_value)
            .astype("int16")
        )
        
        # Outside domain -> fill_value
        alert_yydoy = alert_yydoy.where(domain_valid, other=fill_value).astype("int16")
    
        return domain_valid, forest_mask, alert_month_index, alert_yydoy
    

    # ------------------------------------------------------------------
    # Metadata (NO _FillValue in attrs!)
    # ------------------------------------------------------------------
    def add_metadata(self, ds: xr.Dataset, *, crs: str, version: str) -> xr.Dataset:
        if "disturbance_occurrence" in ds:
            ds["disturbance_occurrence"].attrs.update(
                {
                    "long_name": "Monthly forest disturbance occurrence",
                    "description": (
                        "Binary monthly disturbance flag derived from RADD alert dates (YYddd). "
                        "A pixel is flagged only in the month of the alert. Pixels outside the "
                        "valid mask domain use the dataset fill value. Non-forest pixels are forced to 0."
                    ),
                "grid_mapping": "spatial_ref",
                    "valid_min": 0,
                    "valid_max": 1,
                }
            )

        if "forest_mask" in ds:
            ds["forest_mask"].attrs.update(
                {
                    "long_name": "Forest mask",
                    "description": (
                        "Categorical forest mask. Within the valid domain: 1=forest, 0=non-forest. "
                        "Outside-domain pixels use the dataset fill value."
                    ),
                    "grid_mapping": "spatial_ref",
                    "valid_min": 0,
                    "valid_max": 1,
                }
            )
            
        if "alert_yydoy" in ds:
            ds["alert_yydoy"].attrs.update(
                {
                    "long_name": "RADD alert date code (YYddd)",
                    "description": (
                        "Native RADD alert date encoding as YYddd (year since 2000 and day-of-year). "
                        "0 indicates no alert within the record. Outside the valid domain uses the dataset fill value."
                    ),
                    "grid_mapping": "spatial_ref",
                    "valid_min": 0,
                }
            )

        self.set_global_metadata(
            ds,
            {
                "title": "RADD Europe - Monthly forest disturbance occurrence",
                "description": (
                    "RADD Europe forest disturbance alerts derived from Sentinel-1 radar time series. "
                    "Native alert dates encoded as YYddd are converted into a monthly time series indicating "
                    "the month in which an alert was triggered for each pixel. Disturbance is masked to forest "
                    "pixels using an accompanying categorical forest mask."
                ),
                "temporal_resolution": "monthly",
                "product_version": version,
                "institution": "Laboratory of Geo-information Science and Remote Sensing, Wageningen University",
                "created_by": "van der Woude et al.",
                "spatial_resolution": "10 m",
                "crs": crs,
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )
        return ds

    # ------------------------------------------------------------------
    # Write (EFDA-style streaming)
    # ------------------------------------------------------------------
    def write(
        self,
        alert_vrt: str,
        mask_vrt: str,
        output_zarr: str,
        *,
        start: str = "2020-01-01",
        end: str = "2023-12-01",
        version: str = "1.0",
        crs: str = "EPSG:3035",
        _FillValue: int = -9999,
        chunks: Optional[Dict[str, int]] = None,
        consolidate_at_end: bool = True,
    ) -> str:
        if chunks is None:
            # Consider 4096 if scheduler overhead is high
            chunks = {"time": 1, "latitude": 2048, "longitude": 2048}

        spatial_chunks = {k: v for k, v in chunks.items() if k in ("latitude", "longitude")}

        print("RADD: loading VRTs…")
        ds_in = self.load_dataset(alert_vrt, mask_vrt, spatial_chunks=spatial_chunks)
        
        ds_in = self.set_crs(ds_in, crs=crs)
        ds_in = self._rename_xy_to_latlon(ds_in)
        target_chunks = {"latitude": chunks["latitude"], "longitude": chunks["longitude"]}
        ds_in["alert_code"] = ds_in["alert_code"].chunk(target_chunks)
        ds_in["forest_mask_raw"] = ds_in["forest_mask_raw"].chunk(target_chunks)

        domain_valid, forest_mask, alert_month_index, alert_yydoy = self.build_static_layers(ds_in, fill_value=_FillValue)

        times = pd.date_range(start=start, end=end, freq="MS")
        month_index = times.to_numpy(dtype="datetime64[M]").astype(np.int32)

        store = self.make_store(output_zarr)

        encoding = {
                "disturbance_occurrence": {
                    "dtype": "int16",
                    "chunks": (chunks["time"], chunks["latitude"], chunks["longitude"]),
                    "compressor": DEFAULT_COMPRESSOR,
                    "_FillValue": np.int16(_FillValue),
                },
                "forest_mask": {
                    "dtype": "int16",
                    "chunks": (chunks["latitude"], chunks["longitude"]),
                    "compressor": DEFAULT_COMPRESSOR,
                    "_FillValue": np.int16(_FillValue),
                },
                "alert_yydoy": {
                    "dtype": "int32",
                    "chunks": (chunks["latitude"], chunks["longitude"]),
                    "compressor": DEFAULT_COMPRESSOR,
                    "_FillValue": np.int32(_FillValue),
                },
            }

        for i, (t, m_idx) in enumerate(zip(times, month_index)):
            print(f"RADD: processing {t.strftime('%Y-%m')} ({i + 1}/{len(times)})")

            dist2d = (alert_month_index == np.int32(m_idx)).astype("int16")
            dist2d = dist2d.where(domain_valid, other=_FillValue)
            dist2d = dist2d.where(forest_mask != 0, other=0)

            ds_step = xr.Dataset(
                        {
                            "disturbance_occurrence": dist2d.expand_dims(time=[t]),
                            **(
                                {
                                    "forest_mask": forest_mask,
                                    "alert_yydoy": alert_yydoy,
                                }
                                if i == 0
                                else {}
                            ),
                        }
                    )

            # Chunk only if needed; but make sure it matches encoding layout
            ds_step = ds_step.chunk(
                {
                    "time": chunks["time"],
                    "latitude": chunks["latitude"],
                    "longitude": chunks["longitude"],
                }
            )

            if i == 0:
                ds_step = self.add_metadata(ds_step, crs=crs, version=version)

            # Always prevent CF serialization conflicts on append steps
            if i > 0:
                ds_step = self._strip_cf_serialization_attrs(ds_step)

            # Critical: remove _FillValue from attrs (keep only in encoding)
            ds_step = self._drop_fillvalue_attr(ds_step)
            
            ds_step.to_zarr(
                store=store,
                mode="w" if i == 0 else "a",
                append_dim=None if i == 0 else "time",
                encoding=encoding if i == 0 else None,
                consolidated=False,
            )

            del ds_step
            gc.collect()

        if consolidate_at_end:
            zarr.consolidate_metadata(store)

        print(f"RADD: done → {output_zarr}")
        return output_zarr
