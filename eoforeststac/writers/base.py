import xarray as xr
import numpy as np
import rioxarray  # noqa: F401 — required for .rio accessor on all datasets
import s3fs
from typing import Dict, Optional, Set


class BaseZarrWriter:
    """
    Generic writer for converting EO data into Zarr and storing it in Ceph/S3.

    This class does NOT know anything about product semantics – subclasses
    implement how to load and process their native data.
    """

    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        key: Optional[str] = None,
        secret: Optional[str] = None,
        profile: Optional[str] = None,
        region: str = "eu-central-1",
        anon: bool = False,
        connect_timeout: Optional[int] = None,
        read_timeout: Optional[int] = None,
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url

        config_kwargs = {
            k: v
            for k, v in {
                "connect_timeout": connect_timeout,
                "read_timeout": read_timeout,
            }.items()
            if v is not None
        }

        fs_kwargs = {
            "client_kwargs": {
                "endpoint_url": endpoint_url,
                "region_name": region,
            },
            "config_kwargs": config_kwargs,
        }

        if anon:
            fs_kwargs["anon"] = True
        elif profile is not None:
            fs_kwargs["profile"] = profile
        else:
            fs_kwargs["key"] = key
            fs_kwargs["secret"] = secret

        self.s3 = s3fs.S3FileSystem(**fs_kwargs)

    # ---------- core helpers ----------

    def make_store(self, zarr_path: str):
        """
        Create an s3fs-backed Zarr store.
        zarr_path is full s3://... path.
        """
        return s3fs.S3Map(root=zarr_path, s3=self.s3, check=False)

    def write_to_zarr(
        self,
        ds: xr.Dataset,
        zarr_path: str,
        encoding: Optional[Dict[str, Dict]] = None,
        consolidated: bool = True,
    ) -> str:
        store = self.make_store(zarr_path)
        ds.to_zarr(store=store, mode="w", encoding=encoding, consolidated=consolidated)
        if consolidated:
            self.report_conventions(zarr_path)
        return zarr_path

    def report_conventions(self, zarr_path: str, accept=()) -> list:
        """Print where a written store departs from the catalog's conventions.

        Writers that stream their output and consolidate it themselves call
        this at the end. Findings are printed, never raised: the store is
        already written. ``eoforeststac-check`` reports the same for the
        whole bucket.
        """
        from eoforeststac.checks.conventions import accepted, check_store

        path = self.s3._strip_protocol(zarr_path).rstrip("/")
        findings = accepted(check_store(self.s3, path), accept)
        for f in findings:
            where = f" [{f.variable}]" if f.variable else ""
            print(f"Convention {f.level}: {f.rule}{where}: {f.message}")
        return findings

    @staticmethod
    def apply_fillvalue(ds: xr.Dataset, fill_value=-9999) -> xr.Dataset:
        return ds.where(np.isfinite(ds), fill_value)

    @staticmethod
    def set_crs(ds: xr.Dataset, crs: str = "EPSG:4326") -> xr.Dataset:
        # Ensure y is descending (north-up) so rasterio's from_bounds / clip_box
        # can map geographic top→bottom to row 0→N without raising
        # "Bounds and transform are inconsistent".  GeoTIFFs from projected CRS
        # sources (LAEA, UTM, Albers…) sometimes arrive with ascending y.
        if "y" in ds.coords and float(ds.coords["y"][0]) < float(ds.coords["y"][-1]):
            ds = ds.isel(y=slice(None, None, -1))
        return ds.rio.write_crs(crs)

    @staticmethod
    def set_global_metadata(ds: xr.Dataset, metadata: Dict) -> xr.Dataset:
        ds.attrs.update(metadata)
        return ds

    _CF_STRIP_KEYS: Set[str] = {
        "_FillValue",
        "missing_value",
        "scale_factor",
        "add_offset",
        "valid_range",
    }

    def _strip_cf_serialization_attrs(
        self, obj: xr.Dataset | xr.DataArray
    ) -> xr.Dataset | xr.DataArray:
        """
        Remove CF/Zarr serialization fields from variable attrs.
        These must live only in the encoding dict to avoid xarray conflicts on append.
        Accepts both Dataset and DataArray.
        """
        if isinstance(obj, xr.DataArray):
            for key in self._CF_STRIP_KEYS:
                obj.attrs.pop(key, None)
            return obj
        for var in obj.data_vars:
            for key in self._CF_STRIP_KEYS:
                obj[var].attrs.pop(key, None)
        return obj
