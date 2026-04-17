.. _overview:

##############
Quick Overview
##############

This section provides a brief end-to-end example of the EOForestSTAC workflow: discovering the catalog, loading a dataset, subsetting spatially and temporally, and aligning multiple products. For detailed explanations refer to :ref:`fundamentals`.

Setup
-----

.. code-block:: python

    from eoforeststac.providers.discovery import DiscoveryProvider
    from eoforeststac.providers.zarr import ZarrProvider
    from eoforeststac.providers.subset import subset
    from eoforeststac.providers.align import DatasetAligner
    import geopandas as gpd

    CATALOG_URL = "https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json"
    ENDPOINT_URL = "https://s3.gfz-potsdam.de"

Discover the catalog
---------------------

:py:class:`eoforeststac.providers.discovery.DiscoveryProvider` navigates the STAC hierarchy to list themes, collections, and available versions.

.. code-block:: python

    disc = DiscoveryProvider(
        catalog_url=CATALOG_URL,
        endpoint_url=ENDPOINT_URL,
        anon=True,
    )

    # List all themes
    disc.list_themes()
    # {'biomass-carbon': 'Biomass & Carbon',
    #  'disturbance-change': 'Disturbance & Change',
    #  'structure-demography': 'Structure & Demography',
    #  'land-use': 'Land Use'}

    # List collections within a theme
    disc.list_collections(theme="biomass-carbon")
    # {'CCI_BIOMASS': 'ESA CCI Aboveground Biomass', 'SAATCHI_BIOMASS': ..., ...}

    # Overview table for a theme
    df = disc.collections_table(theme="biomass-carbon")
    print(df[["collection_id", "title", "versions"]])

    # List available versions for one collection
    disc.list_versions("CCI_BIOMASS")
    # ['4.0', '5.0', '6.0']

Open a dataset
--------------

:py:class:`eoforeststac.providers.zarr.ZarrProvider` opens any dataset version as an ``xarray.Dataset`` streamed from Ceph S3 — no local download required.

.. code-block:: python

    provider = ZarrProvider(
        catalog_url=CATALOG_URL,
        endpoint_url=ENDPOINT_URL,
        anon=True,
    )

    # Open a dataset (lazy — no data transferred yet)
    ds = provider.open_dataset(collection_id="CCI_BIOMASS", version="6.0")
    print(ds)

For multi-resolution products, specify a resolution:

.. code-block:: python

    # GAMI Age-Class Fractions at 0.25° resolution
    ds_age = provider.open_dataset(
        collection_id="GAMI_AGECLASS",
        version="3.0",
        resolution="0.25deg",
    )
    # Available resolutions: 1deg, 0.5deg, 0.25deg, 0.1deg, 0.0833deg

Subset spatially and temporally
---------------------------------

:py:func:`eoforeststac.providers.subset.subset` clips the dataset to a geometry and time range. Geometries must be in EPSG:4326 and are automatically reprojected to the dataset CRS.

.. code-block:: python

    # Load a region of interest
    roi = gpd.read_file("DE-Hai.geojson")
    geometry = roi.to_crs("EPSG:4326").geometry.union_all()

    # Subset spatially and temporally
    ds_subset = subset(
        ds,
        geometry=geometry,
        time=("2007-01-01", "2020-12-31"),
    )

    # Trigger computation
    ds_subset = ds_subset.compute()

Align multiple datasets
------------------------

:py:class:`eoforeststac.providers.align.DatasetAligner` reprojects and resamples multiple datasets onto a common reference grid.

.. code-block:: python

    ds_biomass = provider.open_dataset("CCI_BIOMASS", "6.0")
    ds_biomass = subset(ds_biomass, geometry=geometry, time=("2020-01-01", "2020-12-31"))

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
        "CCI_BIOMASS": ds_biomass.sel(time="2020-01-01"),
        "SAATCHI_BIOMASS": ds_saatchi.sel(time="2020-01-01"),
    })

The aligned dataset is guaranteed to share identical CRS, resolution, and grid origin across all products.

---

For a complete explanation of the STAC catalog structure, provider options, and advanced usage, continue to :ref:`fundamentals`.
