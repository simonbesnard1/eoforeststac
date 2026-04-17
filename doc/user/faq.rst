.. _faq:

################################
Frequently Asked Questions (FAQ)
################################

How should I cite EOForestSTAC?
---------------------------------

Please use the following citation when referencing EOForestSTAC in your work:

  Besnard, S. (2025). EOForestSTAC: A toolbox for accessing the EO forest data catalog.
  GitHub repository: https://github.com/simonbesnard1/eoforeststac

How do I find out which collections and versions are available?
----------------------------------------------------------------

Use ``DiscoveryProvider``:

.. code-block:: python

    from eoforeststac.providers.discovery import DiscoveryProvider

    disc = DiscoveryProvider(
        catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
        endpoint_url="https://s3.gfz-potsdam.de",
        anon=True,
    )

    disc.list_themes()
    disc.list_collections(theme="biomass-carbon")
    disc.list_versions("CCI_BIOMASS")

Or browse the interactive STAC Browser at https://simonbesnard1.github.io/eoforeststac/.

I get a ``ValueError: Asset 'zarr' not found``. What is wrong?
---------------------------------------------------------------

Some products (e.g. GAMI_AGECLASS) are stored at multiple spatial resolutions. Their assets are named ``zarr_1deg``, ``zarr_0.25deg``, etc. rather than just ``zarr``. Pass the ``resolution=`` argument:

.. code-block:: python

    ds = provider.open_dataset("GAMI_AGECLASS", "3.0", resolution="0.25deg")

The error message also lists the available resolution keys.

Why is loading data slow?
--------------------------

Data is streamed from GFZ Ceph S3 over HTTPS. The first call to ``.compute()`` fetches only the chunks that fall within your requested spatial and temporal subset. To minimise data transfer:

1. Subset spatially and temporally before calling ``.compute()``.
2. Load only the variables you need: ``ds[["agb"]].compute()``.
3. For repeated access to the same region, consider caching locally with ``xr.Dataset.to_zarr()``.

What coordinate names do datasets use?
----------------------------------------

All products follow CF conventions: spatial dimensions are named ``latitude`` and ``longitude``; the time dimension is ``time``. Coordinates carry ``units``, ``long_name``, and ``standard_name`` attributes.

Can I load data without an internet connection?
------------------------------------------------

No. All data is hosted on GFZ Ceph S3. The package does not support local file caching natively. Use ``xr.Dataset.to_zarr()`` or ``xr.Dataset.to_netcdf()`` to save a subset locally after loading.

Can I use EOForestSTAC from a Jupyter notebook?
-------------------------------------------------

Yes. The package works in any Python environment. For interactive notebooks, install ``jupyter`` and Dask's dashboard:

.. code-block:: bash

    pip install jupyter dask[distributed]

Then enable the progress bar in a notebook:

.. code-block:: python

    from dask.distributed import Client
    client = Client()   # starts a local cluster with a dashboard

How do I contribute to EOForestSTAC?
--------------------------------------

Contributions are welcome! See :ref:`devindex` for guidelines on submitting bug reports, feature requests, and pull requests.

How do I add a new product to the catalog?
-------------------------------------------

Adding a new product requires three steps:

1. **Product config** (``eoforeststac/products/<product>.py``): define spatial extent, temporal extent, keywords, license, and asset template.
2. **Catalog module** (``eoforeststac/catalog/<product>.py``): create the STAC collection and items using the factory functions.
3. **Writer** (``eoforeststac/writers/<product>.py``): implement ``BaseZarrWriter`` to read raw input data and write an analysis-ready Zarr store.

See the ``CCI_BIOMASS`` or ``GAMI_AGECLASS`` implementations for a complete example.
