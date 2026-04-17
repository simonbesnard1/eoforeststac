.. currentmodule:: eoforeststac

.. _fundamentals-provider:

#################
Loading Datasets
#################

:py:class:`eoforeststac.providers.zarr.ZarrProvider` is the main interface for opening datasets stored in the STAC catalog. It locates the correct Zarr asset from the catalog and returns it as a lazy ``xarray.Dataset``.

Key capabilities
----------------

- **Catalog-driven access**: the asset URL is resolved automatically from the STAC item — no manual URL management.
- **Version selection**: pass ``version=`` to load a specific product version.
- **Resolution selection**: pass ``resolution=`` for multi-resolution products (e.g. GAMI_AGECLASS).
- **Variable filtering**: pass ``variables=`` to load only a subset of data variables.
- **HTTPS and S3**: HTTPS public URLs are handled via ``fsspec``; authenticated S3 access is handled via ``s3fs``.

Initialising the provider
--------------------------

.. code-block:: python

    from eoforeststac.providers.zarr import ZarrProvider

    provider = ZarrProvider(
        catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
        endpoint_url="https://s3.gfz-potsdam.de",
        anon=True,   # public, no credentials needed
    )

Opening a single-resolution dataset
-------------------------------------

.. code-block:: python

    ds = provider.open_dataset(collection_id="CCI_BIOMASS", version="6.0")

    print(ds)
    # <xarray.Dataset>
    # Dimensions:  (latitude: ..., longitude: ..., time: ...)
    # Coordinates:
    #   * latitude   (latitude) float32
    #   * longitude  (longitude) float32
    #   * time       (time) datetime64[ns]
    # Data variables:
    #     agb        (time, latitude, longitude) float32 dask.array
    #     ...

Opening a multi-resolution dataset
------------------------------------

For products with multiple spatial resolutions (such as GAMI_AGECLASS), use the ``resolution=`` parameter:

.. code-block:: python

    ds = provider.open_dataset(
        collection_id="GAMI_AGECLASS",
        version="3.0",
        resolution="0.25deg",
    )
    # Also available: "1deg", "0.5deg", "0.1deg", "0.0833deg"

If the resolution key does not exist, a ``ValueError`` is raised listing the available options.

Loading a variable subset
--------------------------

.. code-block:: python

    ds = provider.open_dataset(
        collection_id="CCI_BIOMASS",
        version="6.0",
        variables=["agb"],
    )

Error handling
--------------

The provider raises informative errors for common mistakes:

.. code-block:: python

    # Collection not found
    provider.open_dataset("UNKNOWN", "1.0")
    # ValueError: Collection 'UNKNOWN' not found.
    # Available collections: CCI_BIOMASS, EFDA, ...

    # Version not found
    provider.open_dataset("CCI_BIOMASS", "99.0")
    # ValueError: Version '99.0' not found for collection 'CCI_BIOMASS'.
    # Available version(s): 4.0, 5.0, 6.0

    # Resolution not found
    provider.open_dataset("GAMI_AGECLASS", "3.0", resolution="2deg")
    # ValueError: Asset 'zarr_2deg' not found for item 'GAMI_AGECLASS_v3.0'.
    # Use resolution='1deg' or one of: 1deg, 0.5deg, 0.25deg, 0.1deg, 0.0833deg
