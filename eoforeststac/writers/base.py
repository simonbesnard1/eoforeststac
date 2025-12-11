import xarray as xr
import numpy as np
import s3fs
from typing import Dict, Optional


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
        region: str = "eu-central-1",
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url

        self.s3 = s3fs.S3FileSystem(
            key=key,
            secret=secret,
            client_kwargs={"endpoint_url": endpoint_url, "region_name": region},
        )

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
        return zarr_path

    @staticmethod
    def apply_fillvalue(ds: xr.Dataset, fill_value=-9999) -> xr.Dataset:
        return ds.where(np.isfinite(ds), fill_value)

    @staticmethod
    def set_crs(ds: xr.Dataset, crs: str = "EPSG:4326") -> xr.Dataset:
        # requires rioxarray to be imported by caller or installed
        return ds.rio.write_crs(crs)

    @staticmethod
    def set_global_metadata(ds: xr.Dataset, metadata: Dict) -> xr.Dataset:
        ds.attrs.update(metadata)
        return ds
