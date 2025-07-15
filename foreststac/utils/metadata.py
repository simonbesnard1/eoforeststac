import rasterio
from datetime import datetime
import os

def infer_bbox_from_tiff(tiff_path: str) -> list:
    """Extract bounding box from a GeoTIFF file using rasterio."""
    with rasterio.open(tiff_path) as src:
        bounds = src.bounds
        return [bounds.left, bounds.bottom, bounds.right, bounds.top]

def infer_datetime_from_filename(filename: str) -> datetime:
    """
    Try to extract a year from the filename and return a datetime object.
    Expects a 4-digit year token in the filename, like '2020' in 'GAMI_v2.1_2020.tif'.
    """
    basename = os.path.basename(filename)
    for part in basename.split("_"):
        if part.isdigit() and len(part) == 4:
            return datetime(int(part), 1, 1)
    raise ValueError(f"No valid year found in filename: {filename}")

