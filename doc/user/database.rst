.. _database:

################################
Advanced Usage
################################

Region statistics
=================

:py:func:`eoforeststac.analytics.region_statistics` computes area-weighted
statistics of a gridded variable inside a polygon, one row per time step. It is
the same code the explorer's **Analysis** tab runs, so notebook numbers match
the explorer's.

.. code-block:: python

    import rioxarray  # noqa: F401  (gives the DataArray its CRS)
    from eoforeststac.providers.zarr import ZarrProvider
    from eoforeststac.analytics import region_statistics

    provider = ZarrProvider(
        catalog_url="https://s3.gfz.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
        endpoint_url="https://s3.gfz.de",
        anon=True,
    )
    agb = provider.open_dataset("CCI_BIOMASS", "7.0")["aboveground_biomass"]

    harz = {"type": "Polygon", "coordinates": [[[10.5, 51.5], [11.5, 51.5],
                                                 [11.5, 52.5], [10.5, 52.5], [10.5, 51.5]]]}
    for row in region_statistics(agb, harz, crs="EPSG:4326"):
        print(row["time"], round(row["mean"], 1), "Mg/ha", round(row["total"] / 1e6, 2), "Tg")

Each row holds ``mean`` (area-weighted, over valid pixels), ``total`` (value x
area, e.g. Mg for a density in Mg/ha), ``valid_area_ha``, ``region_area_ha`` and
``coverage`` (the valid share of the region). Check ``coverage`` before
comparing products or years: a total over 40 % of the area is not comparable
with one over 95 %.

- Pixel areas are exact on the WGS84 ellipsoid for latitude/longitude grids,
  where they shrink towards the poles, and come from the resolution on
  projected grids.
- A pixel counts as inside when its centre lies in the polygon.
- The polygon is in EPSG:4326 by default (``geometry_crs=...`` to change); it
  is projected into the dataset's CRS for national grids such as the ALS
  biomass countries.

Which variables can be analysed, and how, is declared per product in the
catalog (``eoforeststac:analytics`` on the collection); currently the biomass
products, as densities in Mg/ha.

Dataset alignment
==================

:py:class:`eoforeststac.providers.align.DatasetAligner` reprojects and resamples multiple datasets onto a common reference grid, enabling pixel-level comparison of products with different native CRS or resolution.

Basic alignment
----------------

.. code-block:: python

    from eoforeststac.providers.zarr import ZarrProvider
    from eoforeststac.providers.subset import subset
    from eoforeststac.providers.align import DatasetAligner
    import geopandas as gpd

    provider = ZarrProvider(
        catalog_url="https://s3.gfz.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
        endpoint_url="https://s3.gfz.de",
        anon=True,
    )

    roi = gpd.read_file("DE-Hai.geojson")
    geometry = roi.to_crs("EPSG:4326").geometry.union_all()

    ds_cci = provider.open_dataset("CCI_BIOMASS", "6.0")
    ds_cci = subset(ds_cci, geometry=geometry, time=("2020-01-01", "2020-12-31"))

    ds_saatchi = provider.open_dataset("SAATCHI_BIOMASS", "2.0")
    ds_saatchi = subset(ds_saatchi, geometry=geometry, time=("2020-01-01", "2020-12-31"))

    aligner = DatasetAligner(
        target="CCI_BIOMASS",
        resampling={
            "CCI_BIOMASS": {"default": "average"},
            "SAATCHI_BIOMASS": {"default": "average"},
        },
    )

    aligned = aligner.align({
        "CCI_BIOMASS": ds_cci.sel(time="2020-01-01"),
        "SAATCHI_BIOMASS": ds_saatchi.sel(time="2020-01-01"),
    })

The ``target=`` argument names the reference dataset. All other datasets are reprojected and resampled to match its CRS, resolution, and grid origin.

The aligned result has:
- Identical CRS, resolution, and spatial extent for all variables.
- Consistent dimension names (``latitude``, ``longitude``).
- Variable-specific resampling applied (e.g. ``"average"`` for continuous variables, ``"nearest"`` for categorical).

Aligning more than two products
---------------------------------

.. code-block:: python

    ds_liu = provider.open_dataset("LIU_BIOMASS", "1.0")
    ds_liu = subset(ds_liu, geometry=geometry, time=("2020-01-01", "2020-12-31"))

    aligned = aligner.align({
        "CCI_BIOMASS": ds_cci.sel(time="2020-01-01"),
        "SAATCHI_BIOMASS": ds_saatchi.sel(time="2020-01-01"),
        "LIU_BIOMASS": ds_liu.sel(time="2020-01-01"),
    })

Writing data writers
=====================

For data producers, the ``writers`` subpackage provides product-specific classes for ingesting raw data and writing analysis-ready Zarr stores. Each writer extends :py:class:`eoforeststac.writers.base.BaseZarrWriter` and implements three methods: ``load_dataset()``, ``process_dataset()``, and ``write()``.

Example: GAMI Age-Class Fractions
-----------------------------------

.. code-block:: python

    from eoforeststac.writers.gami_ageclass import GAMIAgeClassWriter

    writer = GAMIAgeClassWriter(
        endpoint_url="https://s3.gfz.de",
        aws_access_key_id="...",
        aws_secret_access_key="...",
    )

    for resolution in ["1deg", "0.5deg", "0.25deg", "0.1deg", "0.0833deg"]:
        writer.write(
            input_zarr=f"/data/GAMI/AgeClass_{resolution}",
            output_zarr=f"s3://dog.atlaseo-glm.eo-gridded-data/collections/GAMI_AGECLASS/GAMI_AGECLASS_{resolution}_v3.0.zarr",
            resolution=resolution,
            version="3.0",
        )

Example: CCI Biomass
---------------------

.. code-block:: python

    from eoforeststac.writers.CCI_biomass import CCIBiomassWriter

    writer = CCIBiomassWriter(
        endpoint_url="https://s3.gfz.de",
        aws_access_key_id="...",
        aws_secret_access_key="...",
    )

    writer.write(
        input_dir="/data/CCI_Biomass/v6.0",
        output_zarr="s3://dog.atlaseo-glm.eo-gridded-data/collections/CCI_BIOMASS/CCI_BIOMASS_v6.0.zarr",
        version="6.0",
    )

Rebuilding the catalog
========================

After adding new products or versions, rebuild the STAC catalog JSON files and upload them:

.. code-block:: python

    from eoforeststac.catalog.root import build_catalog

    catalog = build_catalog(versions={
        "CCI_BIOMASS": ["4.0", "5.0", "6.0"],
        "GAMI_AGECLASS": ["3.0"],
        # ...
    })

    catalog.normalize_and_save(root_href="s3://dog.atlaseo-glm.eo-gridded-data/collections/public/")
