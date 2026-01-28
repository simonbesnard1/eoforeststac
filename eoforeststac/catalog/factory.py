import pystac


def create_collection(cfg: dict) -> pystac.Collection:
    """Create a STAC Collection with rich metadata for STAC Browser."""

    # Create providers
    providers = [
        pystac.Provider(name=p["name"], roles=p.get("roles", []), url=p.get("url"))
        for p in cfg.get("providers", [])
    ]

    # Create collection
    collection = pystac.Collection(
        id=cfg["id"],
        title=cfg["title"],
        description=cfg["description"],
        license=cfg.get("license", "CC-BY-4.0"),
        providers=providers,
        extent=pystac.Extent(
            spatial=pystac.SpatialExtent([cfg["bbox"]]),
            temporal=pystac.TemporalExtent(
                [[cfg["start_datetime"], cfg["end_datetime"]]]
            ),
        ),
        keywords=cfg.get("keywords", []),
        href=cfg["collection_href"],
    )

    # Add STAC extensions
    if "stac_extensions" in cfg:
        collection.stac_extensions = cfg["stac_extensions"]

    # Add links (critical for STAC Browser experience)
    if "links" in cfg:
        for link_cfg in cfg["links"]:
            collection.add_link(
                pystac.Link(
                    rel=link_cfg["rel"],
                    target=link_cfg["href"],
                    media_type=link_cfg.get("type"),
                    title=link_cfg.get("title"),
                )
            )

    # Add summaries (appears in STAC Browser sidebar)
    if "summaries" in cfg:
        collection.summaries = pystac.Summaries(cfg["summaries"])

    # Add item_assets (defines asset structure for items)
    if "item_assets" in cfg:
        collection.extra_fields["item_assets"] = cfg["item_assets"]

    # Add collection-level assets (used by STAC Browser for thumbnails/icons)
    if "assets" in cfg:
        for key, a in cfg["assets"].items():
            collection.add_asset(
                key,
                pystac.Asset(
                    href=a["href"],
                    media_type=a.get("type"),
                    title=a.get("title"),
                    roles=a.get("roles", []),
                    description=a.get("description"),
                ),
            )

    return collection


def create_item(cfg: dict, version: str) -> pystac.Item:
    """Create a STAC Item with rich metadata for a dataset version."""

    item_href = f"{cfg['base_path']}/{cfg['id']}_v{version}/item.json"

    # Build comprehensive properties
    properties = {
        "product_name": cfg["title"],
        "version": version,
        "start_datetime": cfg["start_datetime"].isoformat(),
        "end_datetime": cfg["end_datetime"].isoformat(),
    }

    # Add extension-specific properties
    if "eo:gsd" in cfg:
        properties["eo:gsd"] = cfg["eo:gsd"]

    if "proj:epsg" in cfg:
        properties["proj:epsg"] = cfg["proj:epsg"]

    # Add summaries as properties if useful at item level
    if "summaries" in cfg:
        summaries = cfg["summaries"]
        if "temporal_resolution" in summaries:
            properties["temporal_resolution"] = summaries["temporal_resolution"][0]
        if "variables" in summaries:
            properties["variables"] = summaries["variables"]
        if "units" in summaries:
            properties["units"] = summaries["units"]

    # Create item
    item = pystac.Item(
        id=f"{cfg['id']}_v{version}",
        geometry=cfg["geometry"],
        bbox=cfg["bbox"],
        datetime=cfg["end_datetime"],
        properties=properties,
        href=item_href,
    )

    # Add STAC extensions to item
    if "stac_extensions" in cfg:
        item.stac_extensions = cfg["stac_extensions"]

    # Add main Zarr asset with rich metadata
    if "asset_template" in cfg:
        asset_factory = cfg["asset_template"]["factory"]
        asset_key = cfg["asset_template"].get("key", "data")
        item.add_asset(asset_key, asset_factory(cfg, version))

    # Add links to item (e.g., documentation, DOI)
    if "links" in cfg:
        for link_cfg in cfg["links"]:
            # Add important links like cite-as, about, license to items
            if link_cfg["rel"] in ["cite-as", "about", "license"]:
                item.add_link(
                    pystac.Link(
                        rel=link_cfg["rel"],
                        target=link_cfg["href"],
                        media_type=link_cfg.get("type"),
                        title=link_cfg.get("title"),
                    )
                )

    return item


def validate_and_save_collection(collection: pystac.Collection, output_path: str):
    """Validate and save collection with proper normalization."""
    # Normalize hrefs to be absolute
    collection.normalize_hrefs(output_path)

    # Validate the collection
    collection.validate()

    # Save to JSON
    collection.save_object()

    return collection
