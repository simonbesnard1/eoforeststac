import pystac

def create_collection(cfg: dict) -> pystac.Collection:
    """Create a STAC Collection based on a product config dict."""

    providers = [
        pystac.Provider(
            name=p["name"],
            roles=p.get("roles", []),
            url=p.get("url")
        )
        for p in cfg.get("providers", [])
    ]

    collection = pystac.Collection(
        id=cfg["id"],
        title=cfg["title"],
        description=cfg["description"],
        license=cfg.get("license", "CC-BY-4.0"),
        providers=providers,
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent([cfg["bbox"]]),
            temporal=pystac.TemporalExtent([[cfg["start_datetime"], cfg["end_datetime"]]])
        ),
        keywords=cfg.get("keywords", []),
        href=cfg["collection_href"],
    )
    
    return collection


def create_item(cfg: dict, version: str) -> pystac.Item:
    """Create a STAC Item for a dataset version."""

    item_href = f"{cfg['base_path']}/{cfg['id']}_v{version}/item.json"

    item = pystac.Item(
        id=f"{cfg['id']}_v{version}",
        geometry=cfg["geometry"],
        bbox=cfg["bbox"],
        datetime=cfg["end_datetime"],
        properties={
            "product_name": cfg["title"],
            "version": version,
            "start_datetime": cfg["start_datetime"].isoformat(),
            "end_datetime": cfg["end_datetime"].isoformat(),
        },
        href=item_href
    )

    # Add main Zarr asset
    if "asset_template" in cfg:
        asset_factory = cfg["asset_template"]["factory"]
        asset_key = cfg["asset_template"].get("key", "data")
        item.add_asset(asset_key, asset_factory(cfg, version))

    return item
