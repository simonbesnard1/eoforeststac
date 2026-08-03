import xarray as xr
import rioxarray
import zarr
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class JRCTMFWriter(BaseZarrWriter):
    """
    Writer for Tropical Moist Forest (TMF) products (v1-2024).

    Native input:
      - Static TMF layers as VRTs
      - AnnualChange as per-year VRTs (1990–2024)

    Output Zarr:
      - Static layers: (latitude, longitude)
      - AnnualChange: (time, latitude, longitude)
    """

    STATIC_VARIABLES = {
        "DeforestationYear": {
            "dtype": "int16",
            "long_name": "Year of deforestation",
            "description": "Year when deforestation started.",
            "units": "year",
        },
        "DegradationYear": {
            "dtype": "int16",
            "long_name": "Year of degradation",
            "description": "Year when forest degradation started.",
            "units": "year",
        },
        "TransitionMap_MainClasses": {
            "dtype": "uint8",
            "long_name": "TMF transition map – main classes",
            "description": "Main land-cover transition classes for Tropical Moist Forests.",
        },
        "TransitionMap_Subtypes": {
            "dtype": "uint8",
            "long_name": "TMF transition map – subtypes",
            "description": "Detailed land-cover transition subtypes for Tropical Moist Forests.",
        },
        "UndisturbedDegradedForest": {
            "dtype": "uint8",
            "long_name": "Undisturbed or degraded forest mask",
            "description": "Binary mask distinguishing undisturbed and degraded TMF.",
        },
    }

    ANNUAL_CHANGE = {
        "name": "AnnualChange",
        "dtype": "uint8",
        "years": list(range(1990, 2025)),
        "long_name": "Annual Tropical Moist Forest change",
        "description": (
            "Annual land-cover state for Tropical Moist Forests "
            "derived from Landsat time series."
        ),
        "legend": {
            1: "Undisturbed Tropical Moist Forest",
            2: "Degraded TMF",
            3: "Deforested land",
            4: "Forest regrowth",
            5: "Permanent or seasonal water",
            6: "Other land cover",
        },
    }

    def load_static_dataset(self, vrt_dir: str) -> xr.Dataset:
        vrt_dir = Path(vrt_dir)
        data_vars = {}

        for name in self.STATIC_VARIABLES:
            path = vrt_dir / f"{name}.vrt"
            if not path.exists():
                raise FileNotFoundError(f"Missing TMF VRT: {path}")
            data_vars[name] = self._load_vrt(path, name)

        return xr.Dataset(data_vars)

    def _load_vrt(self, vrt_path: Path, name: str) -> xr.DataArray:
        return (
            rioxarray.open_rasterio(
                vrt_path,
                masked=True,
                mask_and_scale=False,
                chunks="auto",
            )
            .squeeze(drop=True)
            .rename(name)
        )

    def load_annual_change_year(
        self,
        annual_dir: Path,
        year: int,
    ) -> xr.DataArray:
        path = annual_dir / f"AnnualChange_{year}.vrt"
        if not path.exists():
            raise FileNotFoundError(f"Missing AnnualChange VRT: {path}")

        da = self._load_vrt(path, "AnnualChange")

        da = da.expand_dims(time=[np.datetime64(f"{year}-01-01")])

        return da

    def process_static_dataset(
        self,
        ds: xr.Dataset,
        *,
        crs: str,
        fill_value: int,
        chunks: Dict[str, int],
        version: str,
    ) -> xr.Dataset:

        ds = self.set_crs(ds, crs=crs)

        rename = {}
        if "x" in ds.dims:
            rename["x"] = "longitude"
        if "y" in ds.dims:
            rename["y"] = "latitude"
        if rename:
            ds = ds.rename(rename)

        ds = ds.chunk(chunks)

        for name, meta in self.STATIC_VARIABLES.items():
            ds[name] = ds[name].astype(meta["dtype"])
            ds[name].attrs.update(
                {
                    "long_name": meta["long_name"],
                    "description": meta["description"],
                    "grid_mapping": "spatial_ref",
                    "_FillValue": fill_value,
                }
            )
            if "units" in meta:
                ds[name].attrs["units"] = meta["units"]

        self._add_legends(ds)

        self.set_global_metadata(ds, self._global_metadata(version=version, crs=crs))

        return ds

    def _global_metadata(self, *, version: str, crs: str) -> Dict:
        return {
            "title": "Tropical Moist Forest (TMF) products v1-2024",
            "description": (
                "Global Tropical Moist Forest datasets describing deforestation, "
                "degradation, regrowth, and annual land-cover dynamics from 1990 to 2024."
            ),
            "institution": "Joint Research Centre (JRC)",
            "product_version": version,
            "spatial_resolution": "30 m",
            "spatial_ref": crs,
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "references": "https://forobs.jrc.ec.europa.eu/TMF",
        }

    def _add_legends(self, ds: xr.Dataset):
        ds["TransitionMap_MainClasses"].attrs["legend"] = {
            10: "Undisturbed Tropical Moist Forest",
            20: "Degraded TMF",
            30: "TMF regrowth",
            41: "Deforested → plantation",
            42: "Deforested → water",
            43: "Deforested → other land cover",
            50: "Ongoing deforestation or degradation (2022–2024)",
            60: "Permanent or seasonal water",
            70: "Other land cover (including afforestation)",
        }

        ds["TransitionMap_Subtypes"].attrs["legend"] = {
            10: "Undisturbed TMF",
            11: "Bamboo-dominated forest",
            12: "Undisturbed mangroves",
            21: "Degraded forest (<2015)",
            22: "Degraded forest (2015–2023)",
            23: "Long degradation (<2015)",
            24: "Long degradation (2015–2023)",
            31: "Old forest regrowth",
            32: "Young forest regrowth",
            33: "Very young forest regrowth",
            41: "Deforestation (<2014)",
            42: "Deforestation (2014–2021)",
            51: "Deforestation (2022)",
            52: "Deforestation (2023)",
            53: "Deforestation (2024)",
        }

    def write(
        self,
        vrt_dir: str,
        output_zarr: str,
        *,
        annual_dir: Optional[str] = None,
        fill_value: int = 0,
        version: str = "2024",
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
        consolidate_at_end: bool = True,
    ) -> str:

        if chunks is None:
            chunks = {"latitude": 2048, "longitude": 2048}

        store = self.make_store(output_zarr)

        # --------------------------------------------------
        # 1. Write static layers
        # --------------------------------------------------
        print("Loading static TMF layers…")
        ds_static = self.load_static_dataset(vrt_dir)

        print("Processing static TMF dataset…")
        ds_static = self.process_static_dataset(
            ds_static,
            crs=crs,
            fill_value=fill_value,
            chunks=chunks,
            version=version,
        )

        encoding_static = {
            v: {
                "chunks": (chunks["latitude"], chunks["longitude"]),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for v in ds_static.data_vars
        }

        print("Writing static TMF layers…")
        ds_static.to_zarr(
            store=store,
            mode="w",
            encoding=encoding_static,
            consolidated=False,
        )

        # --------------------------------------------------
        # 2. Stream AnnualChange year by year (CF-safe)
        # --------------------------------------------------
        if annual_dir is not None:
            annual_dir = Path(annual_dir)

            # Reused on every AnnualChange write: zarr append ("mode=a")
            # overrides the group's/array's existing attrs with whatever is
            # passed in, so both the dataset-level metadata and the
            # AnnualChange variable's own attrs must be reapplied on every
            # write, not just the first one, or later appends silently wipe
            # them (this previously wiped global attrs starting from the very
            # first AnnualChange year, since a bare DataArray.to_zarr() call
            # never carries dataset-level attrs at all).
            global_meta = self._global_metadata(version=version, crs=crs)
            annual_change_meta = {
                "long_name": self.ANNUAL_CHANGE["long_name"],
                "description": self.ANNUAL_CHANGE["description"],
                "grid_mapping": "spatial_ref",
                "legend": self.ANNUAL_CHANGE["legend"],
            }

            for i, year in enumerate(self.ANNUAL_CHANGE["years"]):
                print(f"Writing AnnualChange {year}")

                da = self.load_annual_change_year(annual_dir, year)

                # CRS + dim names
                da = da.rio.write_crs(crs, inplace=False)
                da = da.rename({"x": "longitude", "y": "latitude"})

                # Fill + dtype (avoid NaN→uint warning)
                da = da.where(da.notnull(), fill_value).astype(
                    self.ANNUAL_CHANGE["dtype"]
                )

                # Chunk explicitly (time=1)
                da = da.chunk(
                    {
                        "time": 1,
                        "latitude": chunks["latitude"],
                        "longitude": chunks["longitude"],
                    }
                )

                # Wrap in a Dataset (not a bare DataArray) so dataset-level
                # (global) attrs actually get written to the group.
                ds_annual = da.to_dataset(name="AnnualChange")
                ds_annual["AnnualChange"].attrs.update(annual_change_meta)
                self.set_global_metadata(ds_annual, global_meta)

                # _FillValue must live only in encoding (set once, at
                # creation below), never in attrs, or appending conflicts.
                ds_annual = self._strip_cf_serialization_attrs(ds_annual)

                # --------------------------------------------------
                # First year → create variable
                # --------------------------------------------------
                if i == 0:
                    ds_annual.to_zarr(
                        store=store,
                        mode="a",
                        encoding={
                            "AnnualChange": {
                                "chunks": (1, chunks["latitude"], chunks["longitude"]),
                                "compressor": DEFAULT_COMPRESSOR,
                                "fill_value": fill_value,
                            }
                        },
                        consolidated=False,
                    )

                # --------------------------------------------------
                # Subsequent years → append
                # --------------------------------------------------
                else:
                    ds_annual.to_zarr(
                        store=store,
                        mode="a",
                        append_dim="time",
                        consolidated=False,
                    )

                del da, ds_annual

        if consolidate_at_end:
            zarr.consolidate_metadata(store)

        print("TMF Zarr write complete.")
        return output_zarr
