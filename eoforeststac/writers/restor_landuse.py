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

NATIVE_CRS = "+proj=aea +lat_0=-12 +lon_0=-54 +lat_1=-2 +lat_2=-22 +x_0=5000000 +y_0=10000000 +ellps=GRS80 +units=m +no_defs"


class RestorLanduseWriter(BaseZarrWriter):
    """
    Writer for Annual Land Use and Land Cover maps for the Brazilian Amazon (2000–2022).

    Native input:
      - Yearly GeoTIFFs organised as {input_dir}/{year}/LANDSAT_OLI_MOSAIC_{year}-01-01_{year}-12-31_class_v1.tif
      - Custom Albers Equal Area (GRS80), no standard EPSG

    Output:
      - Single Zarr store with variable lulc(time, y, x)

    Classes (uint8):
      1  Annual agriculture
      2  Semi-perennial agriculture
      3  Water
      4  Forest
      5  Silviculture
      6  Secondary vegetation
      7  Mining
      8  Urbanized area
      9  Non-forest natural vegetation
      10 Pasture
      11 Seasonally flooded
      12 Deforestation of the year
      13 Perennial agriculture
      14 Not observed
    """

    TIF_PATTERN = "LANDSAT_OLI_MOSAIC_{year}-01-01_{year}-12-31_class_v1.tif"

    # ------------------------------------------------------------------
    # Low-level IO (single year)
    # ------------------------------------------------------------------
    def _open_year_da(
        self,
        input_dir: str,
        year: int,
        chunks: Dict[str, int],
    ) -> xr.DataArray:
        tif_path = Path(input_dir) / str(year) / self.TIF_PATTERN.format(year=year)
        if not tif_path.exists():
            raise FileNotFoundError(f"RESTOR Land Use GeoTIFF not found: {tif_path}")

        da = (
            rioxarray.open_rasterio(
                tif_path,
                chunks={"y": chunks["y"], "x": chunks["x"]},
                mask_and_scale=False,
            )
            .squeeze(drop=True)
            .rename("lulc")
        )

        da = da.assign_coords(time=np.datetime64(f"{year}-01-01")).expand_dims("time")
        return da.astype("uint8")

    # ------------------------------------------------------------------
    # Build per-year dataset
    # ------------------------------------------------------------------
    def build_year_dataset(
        self,
        input_dir: str,
        year: int,
        crs: str,
        chunks: Dict[str, int],
    ) -> xr.Dataset:
        da = self._open_year_da(input_dir, year, chunks)

        ds = xr.Dataset({"lulc": da})
        ds = self.set_crs(ds, crs=crs)

        ds = ds.chunk({"time": 1, "y": chunks["y"], "x": chunks["x"]})

        if "x" in ds.coords:
            ds["x"].attrs.update(
                {
                    "long_name": "Projected x coordinate (Albers Equal Area, Brazil)",
                    "standard_name": "projection_x_coordinate",
                    "units": "m",
                    "axis": "X",
                }
            )
        if "y" in ds.coords:
            ds["y"].attrs.update(
                {
                    "long_name": "Projected y coordinate (Albers Equal Area, Brazil)",
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
        self, ds: xr.Dataset, crs: str, version: str = "1.0"
    ) -> xr.Dataset:
        if "lulc" in ds:
            ds["lulc"].attrs.update(
                {
                    "long_name": "Land Use and Land Cover classification",
                    "description": (
                        "Annual LULC map for the Brazilian Amazon biome derived from "
                        "Landsat imagery. Categorical map with 14 classes."
                    ),
                    "units": "categorical",
                    "grid_mapping": "spatial_ref",
                    "valid_min": 1,
                    "valid_max": 14,
                    "flag_values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
                    "flag_meanings": (
                        "annual_agriculture semi_perennial_agriculture water forest "
                        "silviculture secondary_vegetation mining urbanized_area "
                        "non_forest_natural_vegetation pasture seasonally_flooded "
                        "deforestation_of_the_year perennial_agriculture not_observed"
                    ),
                }
            )

        self.set_global_metadata(
            ds,
            {
                "title": "Annual Land Use and Land Cover maps for the Brazilian Amazon (2000–2022)",
                "description": (
                    "Annual Land Use and Land Cover maps for the Brazilian Amazon biome, "
                    "derived from Landsat imagery at 30 m spatial resolution. "
                    "Covers the period 2000–2022 with 14 LULC classes."
                ),
                "version": version,
                "institution": "National Institute for Space Research (INPE)",
                "spatial_resolution": "30 m",
                "spatial_ref": crs,
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )

        return ds

    # ------------------------------------------------------------------
    # Zarr encoding
    # ------------------------------------------------------------------
    def make_encoding(
        self, chunks: Dict[str, int], _FillValue: int = 255
    ) -> Dict[str, Dict]:
        return {
            "lulc": {
                "dtype": "uint8",
                "chunks": (1, chunks["y"], chunks["x"]),
                "compressor": DEFAULT_COMPRESSOR,
                "_FillValue": np.uint8(_FillValue),
            },
        }

    # ------------------------------------------------------------------
    # Main write
    # ------------------------------------------------------------------
    def write(
        self,
        input_dir: str,
        years: Sequence[int],
        output_zarr: str,
        version: str = "1.0",
        crs: str = NATIVE_CRS,
        _FillValue: int = 255,
        chunks: Optional[Dict[str, int]] = None,
        consolidate_at_end: bool = True,
    ) -> str:
        """
        Stream yearly RESTOR Land Use GeoTIFFs into a single Zarr store along time.
        """
        years = [int(y) for y in years]

        if chunks is None:
            chunks = {"y": 1000, "x": 1000}

        encoding = self.make_encoding(chunks=chunks, _FillValue=_FillValue)
        store = self.make_store(output_zarr)

        for i, year in enumerate(years):
            print(f"RESTOR Land Use: processing {year} ({i + 1}/{len(years)})")

            ds_year = self.build_year_dataset(
                input_dir=input_dir,
                year=year,
                crs=crs,
                chunks=chunks,
            )

            ds_year = self.add_metadata(ds_year, crs=crs, version=version)

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

        print(f"RESTOR Land Use: done → {output_zarr}")
        return output_zarr
