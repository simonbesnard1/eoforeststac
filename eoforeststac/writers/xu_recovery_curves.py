import xarray as xr
import rioxarray  # noqa: F401
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from eoforeststac.writers.base import BaseZarrWriter
from eoforeststac.core.zarr import DEFAULT_COMPRESSOR

# Band order as documented in the Zenodo README
_BAND_PARAMS = ["agbmax", "b", "c", "d"]

# Ordered list of disturbance types (order is preserved in the dimension coordinate)
_DISTURBANCE_TYPES = ["dryfire", "humfire", "otherdeg", "regrowth"]

# Source GeoTIFF filename per disturbance type
_DISTURBANCE_FILES = {
    "dryfire": "growthcurve_dryfire.tif",
    "humfire": "growthcurve_humfire.tif",
    "otherdeg": "growthcurve_otherdeg.tif",
    "regrowth": "growthcurve_regrowth.tif",
}

_PARAM_META = {
    "agbmax": {
        "units": "Mg ha-1",
        "long_name": "Chapman-Richards asymptote (AGB_max)",
        "description": "Asymptotic maximum aboveground biomass",
        "valid_min": 0.0,
    },
    "b": {
        "units": "1",
        "long_name": "Chapman-Richards growth-rate parameter (b)",
    },
    "c": {
        "units": "1",
        "long_name": "Chapman-Richards shape parameter (c)",
    },
    "d": {
        "units": "Mg ha-1",
        "long_name": "Chapman-Richards offset parameter (d)",
        "description": (
            "Starting biomass; non-zero for degradation types because fire and "
            "non-fire degradation do not always remove all biomass. "
            "Zero for regrowth (deforestation) curves."
        ),
    },
}


class XuRecoveryCurvesWriter(BaseZarrWriter):
    """
    Writer for Xu et al. tropical forest biomass recovery curves.

    Source: four GeoTIFFs at 1-degree resolution (EPSG:4326), each with 4 bands
    (band 1 = AGB_max, band 2 = b, band 3 = c, band 4 = d) for a given
    disturbance type (dryfire, humfire, otherdeg, regrowth).

    Output Zarr structure:
        Dimensions:  disturbance_type (4), latitude (180), longitude (360)
        Variables:   agbmax, b, c, d  — each shape (4, 180, 360)
        Usage:       ds["agbmax"].sel(disturbance_type="humfire")

    Reference:
        Xu et al. – Small persistent humid forest clearings drive tropical
        forest biomass losses. Zenodo doi:10.5281/zenodo.18168285
    """

    def load_dataset(self, input_dir: str) -> xr.Dataset:
        """
        Read all four source GeoTIFFs and combine into a single Dataset with a
        disturbance_type dimension.

        Each TIFF has 4 bands (agbmax, b, c, d). We read all four TIFFs, stack
        them along a new 'disturbance_type' dimension, then split bands into
        separate variables.
        """
        input_dir = Path(input_dir)

        # Accumulate one DataArray per disturbance type (shape: band, lat, lon)
        per_disturbance: Dict[str, xr.DataArray] = {}
        for dt in _DISTURBANCE_TYPES:
            tif_path = input_dir / _DISTURBANCE_FILES[dt]
            if not tif_path.exists():
                raise FileNotFoundError(f"Missing required file: {tif_path}")
            per_disturbance[dt] = rioxarray.open_rasterio(
                tif_path, masked=True, chunks="auto"
            )

        # Build one variable per CR parameter, stacking disturbance types
        data_vars: Dict[str, xr.DataArray] = {}
        for band_idx, param in enumerate(_BAND_PARAMS, start=1):
            slices = []
            for dt in _DISTURBANCE_TYPES:
                slices.append(
                    per_disturbance[dt]
                    .sel(band=band_idx)
                    .drop_vars("band")
                    .expand_dims({"disturbance_type": [dt]})
                )
            data_vars[param] = xr.concat(slices, dim="disturbance_type")

        return xr.Dataset(data_vars)

    def process_dataset(
        self,
        ds: xr.Dataset,
        fill_value: float = -9999.0,
        crs: str = "EPSG:4326",
        version: str = "1.0",
        chunks: Optional[Dict[str, int]] = None,
    ) -> xr.Dataset:
        """Harmonise CRS, dimension names, chunking, fill values, and metadata."""

        ds = self.set_crs(ds, crs=crs)

        # Rename rioxarray spatial dims to latitude / longitude
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

        if chunks is not None:
            ds = ds.chunk(chunks)

        ds = self.apply_fillvalue(ds, fill_value=fill_value).astype("float32")

        # Per-variable attributes
        for param, meta in _PARAM_META.items():
            if param in ds:
                ds[param].attrs.update(
                    {
                        **meta,
                        "grid_mapping": "spatial_ref",
                        "_FillValue": fill_value,
                        "source": (
                            "Xu et al. – Small persistent humid forest clearings "
                            "drive tropical forest biomass losses. "
                            "doi:10.5281/zenodo.18168285"
                        ),
                    }
                )

        # disturbance_type coordinate attributes
        if "disturbance_type" in ds.coords:
            ds["disturbance_type"].attrs.update(
                {
                    "long_name": "Disturbance type",
                    "description": (
                        "dryfire: dry-forest fire; "
                        "humfire: humid-forest fire; "
                        "otherdeg: other (non-fire) degradation; "
                        "regrowth: deforestation/regrowth (d=0)"
                    ),
                }
            )

        # Global metadata
        self.set_global_metadata(
            ds,
            {
                "title": (
                    "Tropical Forest Biomass Recovery Curves "
                    "(Chapman-Richards Parameters)"
                ),
                "description": (
                    "Global 1-degree Chapman-Richards parameters describing AGB recovery "
                    "following fire, non-fire degradation, and deforestation in tropical "
                    "forests. AGB(age) = AGB_max x (1 - exp(-b x age))^c + d  [Mg ha-1]. "
                    "Fitted on CCI-Biomass v4 2020, TMF v2023, GABAM fire. "
                    "Select a disturbance type with ds.sel(disturbance_type='humfire')."
                ),
                "version": version,
                "institution": "LSCE / CEA-CNRS-UVSQ",
                "references": "https://doi.org/10.5281/zenodo.18168285",
                "license": "CC-BY-4.0",
                "spatial_ref": crs,
                "spatial_resolution": "1 degree (~111 km at equator)",
                "creation_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "_FillValue": fill_value,
                "citation": (
                    "Xu et al. (2026). Small persistent humid forest clearings drive "
                    "tropical forest biomass losses. Zenodo. "
                    "https://doi.org/10.5281/zenodo.18168285"
                ),
            },
        )

        return ds

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
        End-to-end: directory of source GeoTIFFs -> harmonised Dataset -> Zarr on S3.
        """
        if chunks is None:
            # 1-degree grid is small (4 x 180 x 360); keep it in a single spatial chunk
            chunks = {"disturbance_type": 4, "latitude": 180, "longitude": 360}

        print("Loading Xu et al. recovery curve GeoTIFFs...")
        ds = self.load_dataset(input_dir)

        print("Processing dataset...")
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
                    chunks["disturbance_type"],
                    chunks["latitude"],
                    chunks["longitude"],
                ),
                "compressor": DEFAULT_COMPRESSOR,
            }
            for var in ds.data_vars
        }

        print("Writing Zarr to S3...")
        return self.write_to_zarr(ds, output_zarr, encoding=encoding)
