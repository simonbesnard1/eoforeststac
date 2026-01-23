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
    following the same routine as the EFDA writer: append along time with to_zarr.

    Inputs
    ------
    alert_vrt : str
        Single VRT with alert date codes encoded as YYddd (0 = no alert).
    mask_vrt : str
        Single VRT with forest mask. Valid classes within domain are 0/1.
        Pixels outside the valid domain should become _FillValue (-9999).

    Output (Zarr)
    -------------
    disturbance_occurrence(time, latitude, longitude) int16
        1 only in the month of the alert for forest pixels; 0 otherwise;
        _FillValue outside valid domain.
    forest_mask(latitude, longitude) int16
        0/1 within valid domain; _FillValue outside valid domain.

    CRS
    ---
    Native projection is ETRS89 / LAEA Europe (EPSG:3035).
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
        Load a single VRT lazily. If chunks is provided, apply spatial chunking
        at read time to avoid later rechunk explosions.
        """
        rio_chunks = None
        if chunks:
            rio_chunks = {}
            # rioxarray uses x/y; we will rename to longitude/latitude later
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
    # Decode YYddd → month index (int32, months since 1970-01)
    # ------------------------------------------------------------------
    @staticmethod
    def _yydoy_to_month_index(block: np.ndarray) -> np.ndarray:
        """
        Convert YYddd codes into a month index (datetime64[M] integer).

        Input:
            block: integer array with YYddd. 0 means 'no alert'.

        Output:
            int32 month index for valid pixels, -1 for 0/invalid.
        """
        arr = block.astype(np.int64, copy=False)
        out = np.full(arr.shape, -1, dtype=np.int32)

        valid = arr > 0
        if not np.any(valid):
            return out

        yy = (arr[valid] // 1000).astype(np.int64)
        doy = (arr[valid] % 1000).astype(np.int64)

        year = 2000 + yy

        # Build date using numpy datetime arithmetic
        year_start = year.astype("datetime64[Y]").astype("datetime64[D]")
        date = year_start + (doy - 1).astype("timedelta64[D]")

        # Convert to month resolution, then to int32 month index
        out[valid] = date.astype("datetime64[M]").astype(np.int32)
        return out

    # ------------------------------------------------------------------
    # Process helpers
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

    def build_static_layers(
        self,
        ds: xr.Dataset,
        *,
        _FillValue: int,
    ) -> Dict[str, xr.DataArray]:
        """
        Build static 2D layers:
          - domain_valid (bool)
          - forest_mask (int16 with _FillValue outside-domain)
          - alert_month_index (int32; -1 for no alert)
        """
        fm_raw = ds["forest_mask_raw"]

        # domain validity: masked areas -> NaN when masked=True
        domain_valid = xr.ufuncs.isfinite(fm_raw).rename("domain_valid")

        forest_mask = xr.where(domain_valid, fm_raw, _FillValue).astype("int16").rename("forest_mask")
        forest_mask = xr.where(
            domain_valid & ((forest_mask == 0) | (forest_mask == 1)),
            forest_mask,
            _FillValue,
        ).astype("int16")

        alert_month_index = xr.apply_ufunc(
            self._yydoy_to_month_index,
            ds["alert_code"].astype("int32"),
            dask="parallelized",
            output_dtypes=[np.int32],
        ).rename("alert_month_index")

        return {
            "domain_valid": domain_valid,
            "forest_mask": forest_mask,
            "alert_month_index": alert_month_index,
        }

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    def add_metadata(
        self,
        ds: xr.Dataset,
        *,
        _FillValue: int,
        crs: str,
        version: str,
    ) -> xr.Dataset:
        # variable attrs
        if "disturbance_occurrence" in ds:
            ds["disturbance_occurrence"].attrs.update(
                {
                    "long_name": "Monthly forest disturbance occurrence",
                    "description": (
                        "Binary monthly disturbance flag derived from RADD alert dates (YYddd). "
                        "A pixel is flagged only in the month of the alert. Pixels outside the "
                        "valid mask domain are set to -9999. Non-forest pixels are forced to 0."
                    ),
                    "grid_mapping": "crs",
                    "_FillValue": _FillValue,
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
                        "Pixels outside the valid domain are -9999."
                    ),
                    "grid_mapping": "crs",
                    "_FillValue": _FillValue,
                    "valid_min": 0,
                    "valid_max": 1,
                }
            )

        # global attrs
        self.set_global_metadata(
            ds,
            {
                "title": "RADD Europe - Monthly forest disturbance occurrence",
                "description": (
                    "RADD Europe forest disturbance alerts derived from Sentinel-1 radar time series, "
                    "providing event-based detection of forest disturbance across Europe. Native alert "
                    "dates encoded as YYddd are converted into a monthly time series indicating the "
                    "month in which an alert was triggered for each pixel. Disturbance is masked to "
                    "forest pixels using an accompanying categorical forest mask."
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
        """
        Stream monthly slices into a single Zarr store along time.

        This mirrors the EFDA writer pattern:
          - initialize store with first timestep (mode='w', encoding=...)
          - append along time for subsequent timesteps (mode='a', append_dim='time')
          - consolidate metadata once at the end (optional)
        """
        if chunks is None:
            chunks = {"time": 1, "latitude": 2048, "longitude": 2048}

        # Spatial chunking at read time (avoid Dask rechunk explosions)
        spatial_chunks = {k: v for k, v in chunks.items() if k in ("latitude", "longitude")}

        print("RADD: loading VRTs…")
        ds_in = self.load_dataset(alert_vrt, mask_vrt, spatial_chunks=spatial_chunks)

        # CRS + rename dims
        ds_in = self.set_crs(ds_in, crs=crs)
        ds_in = self._rename_xy_to_latlon(ds_in)

        # Ensure spatial chunking is present (time does not exist yet)
        if spatial_chunks:
            ds_in = ds_in.chunk(spatial_chunks)

        # Precompute static layers (2D) once
        static = self.build_static_layers(ds_in, _FillValue=_FillValue)
        domain_valid = static["domain_valid"]
        forest_mask = static["forest_mask"]
        alert_month_index = static["alert_month_index"]

        # Monthly timesteps
        times = pd.date_range(start=start, end=end, freq="MS")
        month_index = times.to_numpy(dtype="datetime64[M]").astype(np.int32)

        # Prepare store using BaseZarrWriter (credentials handled there)
        store = self.make_store(output_zarr)

        # Encoding for initialization (dims are time, latitude, longitude)
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
        }

        for i, (t, m_idx) in enumerate(zip(times, month_index)):
            print(f"RADD: processing {t.strftime('%Y-%m')} ({i + 1}/{len(times)})")

            # 2D slice for this month
            dist2d = (alert_month_index == np.int32(m_idx)).astype("int16")

            # outside-domain -> fill value
            dist2d = dist2d.where(domain_valid, other=_FillValue)

            # non-forest inside domain -> 0
            dist2d = dist2d.where(forest_mask != 0, other=0)

            # Expand to time=1 dataset so append_dim='time' works
            ds_step = xr.Dataset(
                {
                    "disturbance_occurrence": dist2d.expand_dims(time=[t]),
                    # write forest_mask only once (first step)
                    **({"forest_mask": forest_mask} if i == 0 else {}),
                }
            )

            # Chunk step dataset to match target layout
            ds_step = ds_step.chunk(
                {
                    "time": chunks["time"],
                    "latitude": chunks["latitude"],
                    "longitude": chunks["longitude"],
                }
            )

            # metadata once (first step is enough)
            if i == 0:
                ds_step = self.add_metadata(ds_step, _FillValue=_FillValue, crs=crs, version=version)
            else:
                ds_step = self._strip_cf_serialization_attrs(ds_step)

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
