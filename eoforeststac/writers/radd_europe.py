from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd
import xarray as xr
import rioxarray

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class RADDEuropeWriter(BaseZarrWriter):
    """
    Writer for RADD Europe alert dates (YYddd) and forest mask (0/1).

    Inputs
    ------
    - alert_vrt : single VRT with YYddd alert dates (0 = no alert)
    - mask_vrt  : single VRT with forest mask (1 = forest)

    Output
    ------
    - disturbance(time, latitude, longitude) uint8
      Monthly binary disturbance occurrence
    - forest_mask(latitude, longitude) uint8
    """

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_variable(self, vrt: Path, name: str) -> xr.DataArray:
        da = (
            rioxarray.open_rasterio(
                vrt,
                masked=True,
                chunks="auto",
            )
            .squeeze(drop=True)
            .rename(name)
        )
        return da

    def load_dataset(self, alert_vrt: str, mask_vrt: str) -> xr.Dataset:
        return xr.Dataset(
            {
                "alert_code": self.load_variable(Path(alert_vrt), "alert_code"),
                "forest_mask": self.load_variable(Path(mask_vrt), "forest_mask"),
            }
        )

    # ------------------------------------------------------------------
    # Decode YYddd → datetime64
    # ------------------------------------------------------------------
    @staticmethod
    def _decode_yydoy(block: np.ndarray) -> np.ndarray:
        """
        Decode YYddd → datetime64[ns]; 0 → NaT
        """
        out = np.empty(block.shape, dtype="datetime64[ns]")
        out[:] = np.datetime64("NaT")

        valid = block > 0
        if not np.any(valid):
            return out

        yy = block[valid] // 1000
        doy = block[valid] % 1000
        year = 2000 + yy

        yyyyddd = year * 1000 + doy
        s = np.char.zfill(yyyyddd.astype(str), 7)

        out[valid] = pd.to_datetime(
            s, format="%Y%j", errors="coerce"
        ).to_numpy()

        return out

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        *,
        start: str = "2020-01-01",
        end: str = "2023-12-01",
        crs: str = "EPSG:3035",
        fill_value: int = 0,
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Convert alert dates to a monthly disturbance cube.
        """

        # CRS
        ds = self.set_crs(ds, crs=crs)

        # Rename dims
        rename = {}
        if "x" in ds.dims:
            rename["x"] = "longitude"
        if "y" in ds.dims:
            rename["y"] = "latitude"
        if rename:
            ds = ds.rename(rename)

        # Decode alert date
        alert_dt = xr.apply_ufunc(
            self._decode_yydoy,
            ds["alert_code"].astype("int32"),
            dask="parallelized",
            output_dtypes=[np.dtype("datetime64[ns]")],
        )

        alert_month = alert_dt.astype("datetime64[M]")

        # Monthly time axis
        time = pd.date_range(start=start, end=end, freq="MS")
        time_da = xr.DataArray(
            time.to_numpy(dtype="datetime64[M]"),
            dims="time",
            coords={"time": time},
        )

        # Broadcast comparison
        disturbance = (alert_month == time_da).astype("uint8")

        # Apply forest mask
        fm = ds["forest_mask"].fillna(0).astype("uint8")
        disturbance = disturbance.where(fm == 1, other=fill_value)

        disturbance = disturbance.rename("disturbance")
        
        disturbance.attrs.update(
            {
                "long_name": "Monthly forest disturbance occurrence",
                "description": (
                    "Binary monthly disturbance flag derived from RADD alert "
                    "dates (YYddd). A pixel is flagged only in the month of "
                    "the alert and only where forest_mask = 1."
                ),
                "grid_mapping": "crs",
                "_FillValue": fill_value,
                "valid_min": 0,
                "valid_max": 1,
            }
        )

        fm.attrs.update(
            {
                "long_name": "Forest mask",
                "description": "Binary forest mask (1=forest, 0=non-forest).",
                "grid_mapping": "crs",
                "_FillValue": fill_value,
            }
        )

        out = xr.Dataset(
            {
                "disturbance_occurence": disturbance,
                "forest_mask": fm,
            }
        )

        self.set_global_metadata(
            out,
            {
                "title": "RADD Europe – Monthly forest disturbance occurrence",
                "temporal_resolution": "monthly",
                "crs": crs,
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )
        
        if chunks:
            out = out.chunk(chunks)

        return out

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        alert_vrt: str,
        mask_vrt: str,
        output_zarr: str,
        *,
        start: str = "2020-01-01",
        end: str = "2023-12-01",
        crs: str = "EPSG:3035",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        alert_vrt + mask_vrt → monthly disturbance Zarr
        """

        if chunks is None:
            chunks = {"time": 1, "latitude": 2048, "longitude": 2048}

        print("Loading RADD Europe VRTs…")
        ds = self.load_dataset(alert_vrt, mask_vrt)

        print("Processing monthly disturbance cube…")
        ds = self.process_dataset(
            ds,
            start=start,
            end=end,
            crs=crs,
            chunks=chunks,
        )
        
        print(ds)

        encoding = {
            "disturbance": {
                "chunks": (
                    chunks["latitude"],
                    chunks["longitude"],
                    chunks["time"],
                ),
                "compressor": DEFAULT_COMPRESSOR,
            },
            "forest_mask": {
                "chunks": (
                    chunks["latitude"],
                    chunks["longitude"],
                ),
                "compressor": DEFAULT_COMPRESSOR,
            },
        }

        print("Writing Zarr…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
