import xarray as xr
import rioxarray
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR


class RobinsonCRWriter(BaseZarrWriter):
    """
    Writer for Robinson et al. global Chapman–Richards (CR) curve parameters
    and derived carbon accumulation metrics.

    Native input:
      - Multiple single-band GeoTIFFs on identical global grids (~1 km)

    Output:
      - One chunked, compressed Zarr store with multiple variables
    """

    # ------------------------------------------------------------------
    # Variable registry (single source of truth)
    # ------------------------------------------------------------------
    VARIABLES = {
        "cr_a": {
            "units": "Mg C ha-1",
            "long_name": "Chapman–Richards asymptote (a)",
            "description": "Asymptotic maximum aboveground carbon stock",
            "valid_min": 0.0,
        },
        "cr_b": {
            "units": "1",
            "long_name": "Chapman–Richards intercept (b)",
            "description": "Intercept parameter controlling curve offset",
        },
        "cr_k": {
            "units": "1",
            "long_name": "Chapman–Richards rate parameter (k)",
            "description": "Rate/shape parameter controlling saturation speed",
        },
        "cr_a_error": {
            "units": "1",
            "long_name": "Standard error of CR asymptote (a)",
        },
        "cr_b_error": {
            "units": "1",
            "long_name": "Standard error of CR intercept (b)",
        },
        "cr_k_error": {
            "units": "1",
            "long_name": "Standard error of CR rate parameter (k)",
        },
        "max_rate": {
            "units": "Mg C ha-1 yr-1",
            "long_name": "Maximum annual carbon accumulation rate",
        },
        "age_at_max_rate": {
            "units": "years",
            "long_name": "Age at maximum carbon accumulation rate",
        },
        "max_removal_potential_benefit_25": {
            "units": "%",
            "long_name": (
                "Relative carbon removal benefit of protecting young forests"
            ),
            "description": (
                "Difference between accumulation in first 25 years and "
                "25-year window of maximum accumulation"
            ),
        },
    }

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_dataset(self, input_dir: str) -> xr.Dataset:
        """
        Load all CR parameter GeoTIFFs from a directory into a single Dataset.
        """

        input_dir = Path(input_dir)
        data_vars = {}

        for var in self.VARIABLES:
            tif = input_dir / f"{var}.tif"
            if not tif.exists():
                raise FileNotFoundError(f"Missing required file: {tif}")

            da = (
                rioxarray.open_rasterio(
                    tif,
                    masked=True,
                    chunks="auto",
                )
                .squeeze(drop=True)
                .rename(var)
            )

            data_vars[var] = da

        return xr.Dataset(data_vars)

    # ------------------------------------------------------------------
    # Process
    # ------------------------------------------------------------------
    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: float = -9999.0,
        crs: str = "EPSG:4326",
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """
        Harmonise CRS, dimensions, chunking and metadata.
        """

        # --- CRS ---
        ds = self.set_crs(ds, crs=crs)

        # --- Rename dimensions ---
        rename_dims = {}
        if "x" in ds.dims:
            rename_dims["x"] = "longitude"
        if "y" in ds.dims:
            rename_dims["y"] = "latitude"

        if rename_dims:
            ds = ds.rename(rename_dims)
            for old, new in rename_dims.items():
                if old in ds.coords:
                    ds = ds.rename({old: new})

        # --- Chunking ---
        if chunks is not None:
            ds = ds.chunk(chunks)

        # --- Fill values + dtype ---
        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("float32")

        # --- Variable metadata ---
        for var, meta in self.VARIABLES.items():
            if var in ds:
                ds[var].attrs.update({
                    **meta,
                    "grid_mapping": "crs",
                    "_FillValue": fill_value,
                    "source": (
                        "Robinson et al., Protect young secondary forests "
                        "for optimum carbon removal"
                    ),
                })

        # --- Global metadata ---
        global_meta = {
            "title": (
                "Global Chapman–Richards Curve Parameters for "
                "Secondary Forest Carbon Dynamics"
            ),
            "description": (
                "Global pixel-level Chapman–Richards (CR) curve parameters "
                "and derived metrics describing aboveground carbon accumulation "
                "in secondary forests."
            ),
            "version": version,
            "institution": "CIFOR-ICRAF & The Nature Conservancy",
            "references": "ttps://doi.org/10.1038/s41558-025-02355-5",
            "crs": crs,
            "spatial_resolution": "~1 km",
            "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "_FillValue": fill_value,
        }

        self.set_global_metadata(ds, global_meta)

        return ds

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(
        self,
        input_dir: str,
        output_zarr: str,
        version: str = "1.0",
        fill_value: float = -9999.0,
        crs: str = "EPSG:4326",
        chunks: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        End-to-end:
            directory of GeoTIFFs → harmonised Dataset → Zarr-on-Ceph/S3
        """

        if chunks is None:
            chunks = {
                "latitude": 2048,
                "longitude": 2048,
            }

        print("Loading CR parameter rasters…")
        ds = self.load_dataset(input_dir)

        print("Processing dataset…")
        ds = self.process_dataset(
            ds,
            fill_value=fill_value,
            crs=crs,
            version=version,
            chunks=chunks,
        )

        encoding = {
            var: {
                "chunks": (
                    chunks["latitude"],
                    chunks["longitude"],
                ),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }
        
        print("Writing Zarr to Ceph/S3…")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
