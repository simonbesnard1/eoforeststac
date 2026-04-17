.. _fundamentals-setup:

*****************************
STAC and Zarr Architecture
*****************************

EOForestSTAC combines a **STAC metadata catalog** with **Zarr cloud-native storage**. Understanding how these two layers interact is the key to understanding the rest of the package.

Overview
--------

.. code-block:: text

   catalog.json  (root — pystac.Catalog)
   ├── biomass-carbon/          ← theme (pystac.Catalog)
   │   ├── CCI_BIOMASS/         ← collection (pystac.Collection)
   │   │   ├── CCI_BIOMASS_v6.0 ← item (pystac.Item)
   │   │   │   └── zarr         ← asset href → s3://.../CCI_BIOMASS_v6.0.zarr
   │   │   └── CCI_BIOMASS_v7.0
   │   ├── SAATCHI_BIOMASS/
   │   └── LIU_BIOMASS/
   ├── disturbance-change/
   │   ├── EFDA/
   │   └── HANSEN_GFC/
   ├── structure-demography/
   │   ├── POTAPOV_HEIGHT/
   │   └── GAMI_AGECLASS/       ← multi-resolution: one item, 5 resolution assets
   │       └── GAMI_AGECLASS_v3.0
   │           ├── zarr_1deg
   │           ├── zarr_0.5deg
   │           ├── zarr_0.25deg
   │           ├── zarr_0.1deg
   │           └── zarr_0.0833deg
   └── land-use/
       ├── POTAPOV_LCLUC/
       └── RESTOR_LANDUSE/

Layer 1: STAC Catalog (metadata)
----------------------------------

The STAC catalog is a hierarchy of JSON files hosted on Ceph S3 at:

.. code-block:: text

   https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json

It follows the `SpatioTemporal Asset Catalog <https://stacspec.org>`_ specification with four levels:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Level
     - Role
   * - **Root catalog**
     - Entry point; links to all theme sub-catalogs.
   * - **Theme catalog**
     - Groups related products (e.g. *biomass-carbon*). Has no spatial extent of its own.
   * - **Collection**
     - One product family (e.g. *CCI_BIOMASS*). Holds spatial/temporal extent, license, keywords, and links to all items.
   * - **Item**
     - One version of a product (e.g. *CCI_BIOMASS_v6.0*). Holds asset links to the actual Zarr stores.

For multi-resolution products (e.g. GAMI_AGECLASS), a single item holds multiple Zarr assets named ``zarr_1deg``, ``zarr_0.25deg``, etc.

Layer 2: Zarr Stores (data)
------------------------------

All products are stored as `Zarr <https://zarr.dev>`_ archives on Ceph S3. Each Zarr store is a directory of chunks. Key design decisions:

- **HTTPS access**: assets are exposed via HTTPS public URLs, readable by anyone without credentials.
- **Lazy streaming**: ``xr.open_zarr()`` reads only the metadata (coordinates, attributes) on open. Actual data chunks are fetched when ``.compute()`` is called.
- **Consolidated metadata**: each store has a ``.zmetadata`` file so that metadata can be read in a single request.
- **CF-compliant attributes**: all products follow CF conventions for dimension names (``latitude``, ``longitude``, ``time``), units, and ``_FillValue``.

How the providers use these layers
-------------------------------------

:py:class:`eoforeststac.providers.discovery.DiscoveryProvider` reads the STAC JSON hierarchy to build discovery tables — it never touches the Zarr data.

:py:class:`eoforeststac.providers.zarr.ZarrProvider` reads the STAC item to find the asset href, then opens the Zarr store via ``fsspec``. For ``https://`` hrefs it uses ``fsspec.get_mapper()``; for ``s3://`` hrefs it uses the configured ``s3fs`` filesystem.

Asset key resolution
----------------------

For standard products, ``ZarrProvider.open_dataset()`` defaults to the ``"zarr"`` asset key. For multi-resolution products, pass ``resolution=`` to select the resolution-specific key:

.. code-block:: python

    # Single-resolution product (uses 'zarr' asset)
    ds = provider.open_dataset("CCI_BIOMASS", "6.0")

    # Multi-resolution product — 'zarr_0.25deg' asset
    ds = provider.open_dataset("GAMI_AGECLASS", "3.0", resolution="0.25deg")

If the ``resolution=`` key does not exist, a ``ValueError`` is raised listing the available resolution keys.
