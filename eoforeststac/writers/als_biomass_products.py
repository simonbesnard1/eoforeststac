import gc
import re

import numpy as np
import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr
import zarr

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR, add_display_range


class ALSBiomassProductsWriter(BaseZarrWriter):
    """
    Writer for ALS Biomass Products (v1.0).

    Native input (one country per directory):
        - One GeoTIFF per year, named ``{Country}_{YYYY}_biomass.tif``
        - Same CRS and resolution, but each year may sit on a grid shifted by
          a fraction of a pixel and cover a different extent (yearly ALS
          campaigns scan different parts of the country).

    Output:
        - Single Zarr store with ``biomass(time, y, x)`` on one common grid:
          the union of all years' extents, with pixel edges on multiples of
          the resolution. Each year is placed by nearest-neighbour, i.e. every
          source pixel goes to the target pixel whose centre is closest, so
          values are unchanged and pixels move by less than half a pixel.
    """

    PRODUCT_ID = "ALS_BIOMASS_PRODUCTS"
    VARIABLES = {
        "biomass": {
            "dtype": "float32",
            "units": "Mg ha-1",
            "long_name": "Forest biomass",
            "description": (
                "Forest biomass derived from National Forest Inventory plots "
                "and airborne laser scanning."
            ),
        }
    }

    # ------------------------------------------------------------------
    # Inputs
    # ------------------------------------------------------------------
    @staticmethod
    def find_yearly_tifs(data_dir: str) -> Dict[int, Path]:
        """Return {year: path} for every ``*_YYYY_biomass.tif`` in data_dir."""
        tifs = {}
        for path in sorted(Path(data_dir).glob("*_biomass.tif")):
            match = re.search(r"_(\d{4})_biomass$", path.stem)
            if match is None:
                raise ValueError(f"Cannot parse a year from {path.name}")
            tifs[int(match.group(1))] = path
        if not tifs:
            raise FileNotFoundError(f"No biomass GeoTIFFs found in {data_dir}")
        return tifs

    @staticmethod
    def load_single_dataset(tif_path: Path, chunks: Dict[str, int]) -> xr.DataArray:
        """
        Load one yearly GeoTIFF lazily, with its nodata (NaN or e.g. -9999,
        depending on the country) turned into NaN and no scale/offset attrs.
        """
        da = (
            rioxarray.open_rasterio(
                tif_path,
                chunks={"y": chunks["y"], "x": chunks["x"]},
                mask_and_scale=False,
            )
            .squeeze(drop=True)
            .rename("biomass")
        )
        nodata = da.rio.nodata
        if nodata is not None and not np.isnan(nodata):
            da = da.where(da != nodata)
        return da

    # ------------------------------------------------------------------
    # Common grid
    # ------------------------------------------------------------------
    @staticmethod
    def build_target_grid(
        tifs: Dict[int, Path], res: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Pixel-centre coordinates of the common grid: the union of all inputs'
        bounds, snapped outward to multiples of ``res``. y is descending.
        """
        import rasterio

        bounds = []
        for path in tifs.values():
            with rasterio.open(path) as src:
                # Some inputs are a hair off (e.g. 9.99991 m); place_on_grid
                # still refuses any pixel that would move by half a pixel
                if not np.allclose(np.abs(src.res), res, rtol=1e-4, atol=0):
                    raise ValueError(f"{path.name} has resolution {src.res}, not {res}")
                bounds.append(src.bounds)

        west = np.floor(min(b.left for b in bounds) / res) * res
        south = np.floor(min(b.bottom for b in bounds) / res) * res
        east = np.ceil(max(b.right for b in bounds) / res) * res
        north = np.ceil(max(b.top for b in bounds) / res) * res

        nx = int(round((east - west) / res))
        ny = int(round((north - south) / res))
        x = west + res / 2 + res * np.arange(nx)
        y = north - res / 2 - res * np.arange(ny)
        return x, y

    @staticmethod
    def place_on_grid(
        da: xr.DataArray, target_x: np.ndarray, target_y: np.ndarray, res: float
    ) -> xr.DataArray:
        """
        Put ``da`` on the target grid by nearest neighbour.

        At the target resolution this means relabelling each pixel centre with
        the nearest target centre (a shift below half a pixel, values
        unchanged), then padding with NaN to the full grid.
        """
        pad = {}
        for dim, target in (("x", target_x), ("y", target_y)):
            src = da[dim].values
            step = target[1] - target[0]  # +res for x, -res for y
            idx = np.rint((src - target[0]) / step).astype(np.int64)
            if not np.array_equal(idx, idx[0] + np.arange(len(idx))):
                raise ValueError(f"{dim} is not a regular grid at {res:g} m")
            if idx[0] < 0 or idx[-1] >= len(target):
                raise ValueError(f"{dim} coordinates fall outside the target grid")
            shift = np.abs(src - target[idx]).max()
            if shift >= res / 2:
                raise ValueError(f"{dim} shift {shift} is not below half a pixel")
            print(f"    {dim}: shifted by {shift:.3f} m")
            pad[dim] = (int(idx[0]), int(len(target) - idx[-1] - 1))
        da = da.pad(pad, constant_values=np.nan)
        return da.assign_coords(x=target_x, y=target_y)

    def build_year_dataset(
        self,
        tif_path: Path,
        year: int,
        target_x: np.ndarray,
        target_y: np.ndarray,
        res: float,
        crs: str,
        chunks: Dict[str, int],
    ) -> xr.Dataset:
        """One year on the common grid, as a length-1 ``time`` dataset."""
        da = self.load_single_dataset(tif_path, chunks)
        da = self.place_on_grid(da, target_x, target_y, res)
        da = da.astype(self.VARIABLES["biomass"]["dtype"])
        da = da.expand_dims(time=[np.datetime64(f"{year}-01-01", "ns")])

        ds = da.to_dataset()
        ds = self.set_crs(ds, crs=crs)
        ds = self._strip_cf_serialization_attrs(ds)
        ds["biomass"].attrs = {
            k: self.VARIABLES["biomass"][k]
            for k in ("units", "long_name", "description")
        }
        ds["biomass"].attrs["grid_mapping"] = "spatial_ref"
        # Without this the scalar spatial_ref is stored as a plain variable and
        # a default xr.open_zarr() loses the CRS
        ds["biomass"].encoding["coordinates"] = "spatial_ref"
        return ds.chunk({"time": 1, "y": chunks["y"], "x": chunks["x"]})

    def add_metadata(
        self,
        ds: xr.Dataset,
        country: str,
        years: List[int],
        crs: str,
        res: float,
        version: str,
    ) -> xr.Dataset:
        return self.set_global_metadata(
            ds,
            {
                "title": f"ALS-derived forest biomass – {country}",
                "description": (
                    f"Forest biomass maps at {res:g} m resolution for {country}, derived "
                    "from National Forest Inventory plots and airborne laser scanning. "
                    "Each year covers the area scanned in that year's ALS campaign; "
                    "elsewhere values are NaN."
                ),
                "years": ", ".join(str(y) for y in years),
                "product_version": version,
                "spatial_resolution": f"{res:g} m",
                "spatial_ref": crs,
                "resampling": (
                    "Years on a grid shifted by a fraction of a pixel were placed on "
                    "the common grid by nearest neighbour (values unchanged)."
                ),
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def output_path(self, country: str, version: str) -> str:
        return (
            f"s3://{self.bucket}/collections/{self.PRODUCT_ID}/"
            f"ALS_BIOMASS_{country.upper()}_v{version}.zarr"
        )

    def write(
        self,
        data_dir: str,
        country: str,
        crs: str,
        version: str = "1.0",
        res: float = 10.0,
        chunks: Optional[Dict[str, int]] = None,
        output_zarr: Optional[str] = None,
    ) -> str:
        """
        Write all yearly GeoTIFFs of one country to a single aligned Zarr store.

        Example
        -------
        writer.write(
            data_dir=".../Biomass_maps_v1/Finland",
            country="Finland",
            crs="EPSG:3067",
        )
        """
        if chunks is None:
            chunks = {"y": 1024, "x": 1024}
        output_zarr = output_zarr or self.output_path(country, version)

        tifs = self.find_yearly_tifs(data_dir)
        years = sorted(tifs)
        target_x, target_y = self.build_target_grid(tifs, res)
        print(
            f"ALS biomass {country}: years {years}, common grid "
            f"{len(target_y)} x {len(target_x)} at {res:g} m -> {output_zarr}"
        )

        encoding = {
            "biomass": {
                "compressor": DEFAULT_COMPRESSOR,
                "chunks": (1, chunks["y"], chunks["x"]),
                "_FillValue": np.float32(np.nan),
            }
        }
        store = self.make_store(output_zarr)

        for i, year in enumerate(years):
            print(f"Processing {year} ({i + 1}/{len(years)})")
            ds_year = self.build_year_dataset(
                tifs[year], year, target_x, target_y, res, crs, chunks
            )
            ds_year = self.add_metadata(ds_year, country, years, crs, res, version)
            ds_year.to_zarr(
                store=store,
                mode="w" if i == 0 else "a",
                append_dim=None if i == 0 else "time",
                encoding=encoding if i == 0 else None,
                consolidated=False,
                # Zarr v2 like the rest of the catalog (TiTiler, pyramids)
                zarr_format=2,
                # Most of the grid is outside any single year's campaign
                write_empty_chunks=False,
            )
            del ds_year
            gc.collect()

        zarr.consolidate_metadata(store)

        # Legend range for the explorer, which cannot measure stores this large
        ranges = add_display_range(output_zarr, fs=self.s3)
        print(f"Display range (p2-p98): {ranges}")
        return output_zarr
