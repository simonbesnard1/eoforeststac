import rioxarray as rxr
from eoforeststac.providers.base import BaseProvider

class EFDAProvider(BaseProvider):
    def _s3_to_https(self, s3_href: str) -> str:
        """
        Convert an S3 href to an HTTPS href for public access via rasterio.
        """
        return s3_href.replace(
            "s3://dog.atlaseo-glm.eo-gridded-data/",
            "https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/"
        )

    def load_data(self, year: int, version: str) -> dict:
        """
        Load EFDA GeoTIFFs for a given year and version.
        Returns a dictionary with 'disturbance' and 'agent' xarray objects.
        """
        item_id = f"EFDA_{year}_v{version}"
        item = self.get_item("EFDA", item_id)

        data = {}

        if "disturbance" in item.assets:
            s3_href = item.assets["disturbance"].href
            data["disturbance"] = rxr.open_rasterio(self._s3_to_https(s3_href), masked=True)

        if "agent" in item.assets:
            s3_href = item.assets["agent"].href
            data["agent"] = rxr.open_rasterio(self._s3_to_https(s3_href), masked=True)

        if not data:
            raise ValueError(f"No GeoTIFF assets found for EFDA item {item_id}")

        return data
