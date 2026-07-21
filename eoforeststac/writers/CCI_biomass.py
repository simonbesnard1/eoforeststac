import zarr
import numpy as np
import xarray as xr
import rioxarray
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class CCIBiomassWriter(BaseZarrWriter):
    """
    Writer for the ESA CCI Biomass product (v7+).

    Native input, as downloaded from
    https://dap.ceda.ac.uk/neodc/esacci/biomass/data/agb/maps/<version>/geotiff/,
    is one directory per year containing global 10x10 degree tiles, e.g.:

        N00E000_ESACCI-BIOMASS-L4-AGB-MERGED-100m-2020-fv7.0.tif
        N00E000_ESACCI-BIOMASS-L4-AGB_SD-MERGED-100m-2020-fv7.0.tif

    This writer expects the tiles for each year/variable to already be
    mosaicked into a VRT (build once per year/variable with GDAL), laid out as:

        <vrt_dir>/AGB_<year>.vrt
        <vrt_dir>/AGB_SD_<year>.vrt

    e.g.:

        gdalbuildvrt AGB_2020.vrt    /downloads/2020/*_ESACCI-BIOMASS-L4-AGB-MERGED-*.tif
        gdalbuildvrt AGB_SD_2020.vrt /downloads/2020/*_ESACCI-BIOMASS-L4-AGB_SD-MERGED-*.tif

    Years are written and appended to Zarr one at a time (CF-safe streaming)
    to avoid ever materializing the full global, multi-decade stack in memory.
    """

    VARIABLES = {
        "aboveground_biomass": {
            "vrt_prefix": "AGB",
            "long_name": "Forest aboveground biomass",
            "description": (
                "Mass (oven-dry weight) of the woody parts (stem, bark, branches, twigs) "
                "of all living trees per unit area, excluding stumps and roots."
            ),
        },
        "aboveground_biomass_std": {
            "vrt_prefix": "AGB_SD",
            "long_name": "Standard deviation of aboveground biomass",
            "description": "Per-pixel estimate of aboveground biomass uncertainty (1-sigma).",
        },
    }

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def _load_vrt(self, vrt_path: Path, name: str) -> xr.DataArray:
        return (
            rioxarray.open_rasterio(
                vrt_path,
                masked=True,
                chunks="auto",
            )
            .squeeze(drop=True)
            .rename(name)
        )

    def discover_years(self, vrt_dir: Path) -> List[int]:
        years = set()
        for var_meta in self.VARIABLES.values():
            prefix = var_meta["vrt_prefix"]
            for path in vrt_dir.glob(f"{prefix}_*.vrt"):
                suffix = path.stem[len(prefix) + 1 :]
                if suffix.isdigit():
                    years.add(int(suffix))
        return sorted(years)

    def load_year(self, vrt_dir: Path, year: int) -> xr.Dataset:
        """
        Load AGB + AGB_SD VRTs for a single year into a Dataset with a time dim.
        """
        data_vars = {}
        for var_name, meta in self.VARIABLES.items():
            vrt_path = vrt_dir / f"{meta['vrt_prefix']}_{year}.vrt"
            if not vrt_path.exists():
                raise FileNotFoundError(f"Missing CCI Biomass VRT: {vrt_path}")
            data_vars[var_name] = self._load_vrt(vrt_path, var_name)

        ds = xr.Dataset(data_vars)
        ds = ds.expand_dims(time=[np.datetime64(f"{year}-01-01")])
        return ds

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_year(
        self,
        ds: xr.Dataset,
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        version: str = "7.0",
        chunks: Optional[Dict[str, int]] = None,
        set_variable_metadata: bool = True,
    ) -> xr.Dataset:

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)

        # --- Rename raster dimensions ---
        rename_dims = {}
        if "x" in ds.dims:
            rename_dims["x"] = "longitude"
        if "y" in ds.dims:
            rename_dims["y"] = "latitude"
        if rename_dims:
            ds = ds.rename(rename_dims)

        # --- Chunking ---
        if chunks is not None:
            ds = ds.chunk(
                {
                    "time": 1,
                    "latitude": chunks["latitude"],
                    "longitude": chunks["longitude"],
                }
            )

        # --- Zero -> NaN -> fill_value -> dtype (SAFE) ---
        for var in ds.data_vars:
            ds[var] = ds[var].where(ds[var] != 0)
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("int32")

        # --- Variable-level metadata (only needed once, on the first write) ---
        if set_variable_metadata:
            for var_name, meta in self.VARIABLES.items():
                if var_name not in ds:
                    continue
                ds[var_name].attrs.update(
                    {
                        "long_name": meta["long_name"],
                        "units": "Mg/ha",
                        "_FillValue": fill_value,
                        "description": meta["description"],
                        "source": f"ESA Climate Change Initiative – Biomass v{version}, Santoro & Cartus (2026)",
                        "grid_mapping": "spatial_ref",
                    }
                )
        else:
            ds = self._strip_cf_serialization_attrs(ds)

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        vrt_dir: str,
        output_zarr: str,
        years: Optional[List[int]] = None,
        version: str = "7.0",
        fill_value: int = -9999,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
        consolidate_at_end: bool = True,
    ) -> str:
        """
        Complete end-to-end writing of ESA CCI biomass to Ceph in Zarr format,
        streaming one year at a time to keep memory bounded.
        """

        if chunks is None:
            chunks = {"latitude": 2048, "longitude": 2048}

        vrt_dir = Path(vrt_dir)

        if years is None:
            years = self.discover_years(vrt_dir)
        if not years:
            raise FileNotFoundError(f"No CCI Biomass VRTs found in {vrt_dir}")

        store = self.make_store(output_zarr)

        for i, year in enumerate(years):
            print(f"Loading CCI Biomass {year}...")
            ds = self.load_year(vrt_dir, year)

            print(f"Processing {year}...")
            ds = self.process_year(
                ds,
                fill_value=fill_value,
                crs=crs,
                version=version,
                chunks=chunks,
                set_variable_metadata=(i == 0),
            )

            if i == 0:
                self.set_global_metadata(
                    ds,
                    {
                        "title": f"ESA CCI Biomass v{version} – Global Aboveground Biomass (100 m)",
                        "version": version,
                        "institution": (
                            "European Space Agency (ESA) Climate Change Initiative (CCI); "
                            "NERC EDS Centre for Environmental Data Analysis"
                        ),
                        "source_dataset": "doi:10.5285/6429d1aafe1e43b9b414e4a5a7f8b903",
                        "created_by": "Santoro, M.; Cartus, O.",
                        "contact": "Maurizio Santoro (GAMMA RS)",
                        "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "description": (
                            "Global forest aboveground biomass maps for 2005-2012 and 2015-2024 "
                            "derived from L-band radar (ALOS, ALOS-2), Sentinel-1, ICESat-2 "
                            "calibration and multi-year temporal weighting."
                        ),
                        "spatial_resolution": "100 m",
                        "_FillValue": fill_value,
                        "spatial_ref": crs,
                    },
                )

                encoding = {
                    var: {
                        "chunks": (1, chunks["latitude"], chunks["longitude"]),
                        "compressor": DEFAULT_COMPRESSOR,
                    }
                    for var in ds.data_vars
                }

                print("Writing first year to Ceph/S3 (creates variables)...")
                ds.to_zarr(store=store, mode="w", encoding=encoding, consolidated=False)
            else:
                print(f"Appending {year} to Ceph/S3...")
                ds.to_zarr(store=store, mode="a", append_dim="time", consolidated=False)

            del ds

        if consolidate_at_end:
            zarr.consolidate_metadata(store)

        print("CCI Biomass Zarr write complete.")
        return output_zarr
