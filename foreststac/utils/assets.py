import pystac

def create_zarr_asset(href: str, title: str) -> pystac.Asset:
    return pystac.Asset(
        href=href,
        media_type="application/vnd+zarr",
        roles=["data"],
        title=title
    )

def create_cog_asset(href: str, title: str) -> pystac.Asset:
    return pystac.Asset(
        href=href,
        media_type="image/tiff; application=geotiff; profile=cloud-optimized",
        roles=["data"],
        title=title
    )

def create_netcdf_asset(href: str, title: str) -> pystac.Asset:
    return pystac.Asset(
        href=href,
        media_type="application/x-netcdf",
        roles=["data"],
        title=title
    )

