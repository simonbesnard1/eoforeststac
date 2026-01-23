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
        fill_value: int = -9999,
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Convert alert dates to a monthly disturbance cube.
    
        Semantics
        ---------
        - forest_mask: {0,1} are valid classes; outside-domain pixels are fill_value (-9999)
        - disturbance: within-domain pixels are {0,1}; outside-domain pixels are fill_value (-9999)
          Additionally, non-forest pixels (forest_mask==0) are forced to 0 (not disturbed).
        """
    
        # CRS
        ds = self.set_crs(ds, crs=crs)
    
        # Rename dims (NOTE: for EPSG:3035, you may prefer 'easting'/'northing',
        # but keeping your names as requested)
        rename = {}
        if "x" in ds.dims:
            rename["x"] = "longitude"
        if "y" in ds.dims:
            rename["y"] = "latitude"
        if rename:
            ds = ds.rename(rename)
    
        # ------
        # Phase 1 chunking: only spatial dims exist at this point
        # ------
        if chunks:
            spatial_chunks = {k: v for k, v in chunks.items() if k in ("latitude", "longitude")}
            if spatial_chunks:
                ds = ds.chunk(spatial_chunks)
    
        # ----------------------------
        # Forest mask: domain validity
        # ----------------------------
        fm_raw = ds["forest_mask"]
    
        # rioxarray often turns nodata into NaN (masked=True). Use "isfinite" as domain flag.
        # If your mask uses an explicit nodata instead, this still works after masked read.
        domain_valid = xr.ufuncs.isfinite(fm_raw)
    
        # Normalize forest_mask to int16 with fill_value outside domain
        fm = xr.where(domain_valid, fm_raw, fill_value).astype("int16").rename("forest_mask")
    
        # Optional: enforce only 0/1 inside domain (helps catch weird values early)
        # Anything not 0/1 inside domain becomes fill_value (or raise if you prefer).
        fm = xr.where(domain_valid & ((fm == 0) | (fm == 1)), fm, fill_value).astype("int16")
    
        # ----------------------------
        # Decode alert date YYddd -> datetime
        # ----------------------------
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
    
        # Broadcast comparison → {0,1} inside domain (temporarily uint8/boolean is fine)
        disturbance01 = (alert_month == time_da)
    
        # ----------------------------
        # Apply domain + forest logic
        # ----------------------------
        # Start with int16 so we can store fill_value
        disturbance = disturbance01.astype("int16")
    
        # Outside-domain pixels -> fill_value
        disturbance = disturbance.where(domain_valid, other=fill_value)
    
        # Inside-domain but non-forest (fm==0) -> force to 0
        disturbance = disturbance.where(fm != 0, other=0)

        disturbance = disturbance.rename("disturbance_occurence")
        
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
                "title": "RADD Europe - Monthly forest disturbance occurrence",
                "description": (
                        "RADD Europe forest disturbance alerts derived from Sentinel-1 radar time series, "
                        "providing event-based detection of forest disturbance across Europe. "
                        "Native alert dates encoded as YYddd are converted into a monthly time series "
                        "indicating the occurrence of a disturbance event in the corresponding month. "
                        "Disturbance is flagged only for forested pixels, as defined by an accompanying "
                        "binary forest mask."
                    ),
                "temporal_resolution": "monthly",
                "product_version": version,
                "institution": (
                    "Laboratory of Geo-information Science and Remote Sensing, Wageningen University"
                ),
                "created_by": "van der Woude et al.",
                "spatial_resolution": "10 m",
                "crs": crs,
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )
        
        # ------
        # Phase 2 chunking: time exists now
        # ------
        if chunks:
            out_chunks = {k: v for k, v in chunks.items() if k in out.dims}
            if out_chunks:
                out = out.chunk(out_chunks)
        
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
        version: str = "1.0",
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
            version= version
        )
                
        encoding = {
            "disturbance_occurence": {
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
