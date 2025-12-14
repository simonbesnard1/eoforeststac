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

    Output:
      - a single Zarr store with variables:
          efda_disturbance(time, latitude, longitude)
          efda_agent(time, latitude, longitude)

    Strategy:
      - stream year-by-year and APPEND along time (no concat, no big lists)
    """

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------
    def _open_year_da(
        self,
        input_dir: str,
        year: int,
        pattern: str,
        var_name: str,
        chunks_xy: Dict[str, int],
    ) -> xr.DataArray:
        """
        Open one yearly GeoTIFF lazily (dask-chunked) and return DataArray (y, x).
        """
        tif_path = Path(input_dir) / pattern.format(year=year)

        da = (
            rioxarray.open_rasterio(
                tif_path,
                chunks={"y": chunks_xy["latitude"], "x": chunks_xy["longitude"]},
            )
            .squeeze(drop=True)               # drop band
            .rename(var_name)                 # name variable
        )

        # attach time coordinate but keep it as a length-1 time dimension
        da = da.assign_coords(time=np.datetime64(f"{year}-01-01")).expand_dims("time")
        return da

    def _standardize_xy_names(self, obj: xr.Dataset | xr.DataArray) -> xr.Dataset | xr.DataArray:
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
            # also rename coordinate variables if present
            for old, new in rename_dims.items():
                if old in obj.coords:
                    obj = obj.rename({old: new})
        return obj

    # ------------------------------------------------------------------
    # Per-year build + process
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
        # open both layers lazily + chunked
        da_mosaic = self._open_year_da(
            mosaic_dir, year, mosaic_pattern, "efda_disturbance", chunks_xy=chunks
        )
        da_agent = self._open_year_da(
            agent_dir, year, agent_pattern, "efda_agent", chunks_xy=chunks
        )

        # standardize dim names
        da_mosaic = self._standardize_xy_names(da_mosaic)
        da_agent  = self._standardize_xy_names(da_agent)

        ds = xr.Dataset(
            {
                "efda_disturbance": da_mosaic,
                "efda_agent": da_agent,
            }
        )

        # CRS (write to dataset once)
        ds = self.set_crs(ds, crs=crs)

        # dtype (EFDA is categorical; keep small)
        ds = ds.astype(dtype)

        # chunk once more at dataset level (ensures alignment)
        ds = ds.chunk({"time": 1, "latitude": chunks["latitude"], "longitude": chunks["longitude"]})

        # coordinate attrs (projected LAEA meters)
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

    def add_metadata(
        self,
        ds: xr.Dataset,
        _FillValue: int,
        crs: str,
    ) -> xr.Dataset:
        """
        Add variable + global metadata. (Does not force loading.)
        """
        ds["efda_disturbance"].attrs.update({
            "long_name": "EFDA disturbance mosaic",
            "description": "Annual forest disturbance mosaic from EFDA.",
            "grid_mapping": "crs",
            "_FillValue": _FillValue,
        })

        ds["efda_agent"].attrs.update({
            "long_name": "EFDA disturbance agent",
            "description": "Disturbance agent classification (e.g., wind, bark beetle, harvest).",
            "grid_mapping": "crs",
            "_FillValue": _FillValue,
        })

        meta = {
            "title": "European Forest Disturbance Atlas (EFDA)",
            "product_name": "European Forest Disturbance Atlas",
            "institution": "Joint Research Centre (JRC)",
            "created_by": "EFDA consortium",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "spatial_resolution": "100 m",
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
        Encoding must be tuples of ints in DIM ORDER.
        We write variables as (time, latitude, longitude).
        """
        zchunks = (1, chunks["latitude"], chunks["longitude"])
        return {
            "efda_disturbance": {
                "chunks": zchunks,
                "compressor": DEFAULT_COMPRESSOR,
                "dtype": np.dtype(dtype),
            },
            "efda_agent": {
                "chunks": zchunks,
                "compressor": DEFAULT_COMPRESSOR,
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
        _FillValue: int = 0,
        chunks: Optional[Dict[str, int]] = None,
        dtype: str = "uint8",
        consolidate_at_end: bool = True,
    ) -> str:
        """
        Stream yearly EFDA GeoTIFFs into a single Zarr store along time.
    
        Design guarantees:
          - constant memory usage
          - safe append semantics
          - explicit metadata consolidation (no silent failures)
    
        Notes:
          - Default _FillValue=0 is correct for EFDA categorical layers.
          - For signed nodata, use dtype=int16 and _FillValue=-9999.
        """
    
        years = [int(y) for y in years]
    
        if chunks is None:
            chunks = {"latitude": 1000, "longitude": 1000}
    
        # --------------------------------------------------------------
        # Encoding (fixed, chunk-aligned, compressor-aware)
        # --------------------------------------------------------------
        encoding = self.make_encoding(
            chunks=chunks,
            _FillValue=_FillValue,
            dtype=dtype,
        )
    
        # --------------------------------------------------------------
        # Zarr store (S3 / Ceph / FS)
        # --------------------------------------------------------------
        store = self.make_store(output_zarr)
    
        # --------------------------------------------------------------
        # STREAM: write year-by-year
        # --------------------------------------------------------------
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
    
            # metadata only (no data touch)
            ds_year = self.add_metadata(
                ds_year,
                _FillValue=_FillValue,
                crs=crs,
            )
    
            if i == 0:
                print("EFDA: initializing Zarr (mode='w')")
                ds_year.to_zarr(
                    store=store,
                    mode="w",
                    encoding=encoding,
                    consolidated=False,
                )
            else:
                print("EFDA: appending along time (mode='a')")
                ds_year.to_zarr(
                    store=store,
                    mode="a",
                    append_dim="time",
                    encoding=encoding,
                    consolidated=False,  
                )
    
            # help GC on very large loops
            del ds_year
    
        # --------------------------------------------------------------
        # FINAL METADATA CONSOLIDATION (ONE TIME ONLY)
        # --------------------------------------------------------------
        if consolidate_at_end:
            print("EFDA: consolidating Zarr metadata (.zmetadata)")
            import zarr
            zarr.consolidate_metadata(store)
    
        print(f"EFDA: done → {output_zarr}")
        return output_zarr

