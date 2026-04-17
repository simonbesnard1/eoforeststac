.. _fundamentals-processor:

################
Discovery
################

:py:class:`eoforeststac.providers.discovery.DiscoveryProvider` navigates the STAC catalog hierarchy to discover available themes, collections, versions, and asset keys. It never touches the Zarr data — it only reads the STAC JSON metadata.

Overview
---------

.. code-block:: python

    from eoforeststac.providers.discovery import DiscoveryProvider

    disc = DiscoveryProvider(
        catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
        endpoint_url="https://s3.gfz-potsdam.de",
        anon=True,
    )

Listing themes
---------------

.. code-block:: python

    disc.list_themes()
    # {'biomass-carbon': 'Biomass & Carbon',
    #  'disturbance-change': 'Disturbance & Change',
    #  'structure-demography': 'Structure & Demography',
    #  'land-use': 'Land Use'}

Listing collections
--------------------

Pass a ``theme=`` identifier to list all collections within that theme:

.. code-block:: python

    disc.list_collections(theme="biomass-carbon")
    # {'CCI_BIOMASS': 'ESA CCI Aboveground Biomass',
    #  'SAATCHI_BIOMASS': 'Saatchi Aboveground Biomass',
    #  'LIU_BIOMASS': 'Liu Aboveground Biomass',
    #  'GAMI': 'GAMI Aboveground Biomass'}

    # All collection IDs across all themes
    disc.list_collection_ids()

Discovery table
----------------

``collections_table()`` returns a ``pandas.DataFrame`` with one row per collection including title, description, and available versions:

.. code-block:: python

    df = disc.collections_table(theme="biomass-carbon")
    print(df[["collection_id", "title", "versions", "n_versions"]])

Listing versions
-----------------

.. code-block:: python

    disc.list_versions("CCI_BIOMASS")
    # ['4.0', '5.0', '6.0']

    disc.list_versions("GAMI_AGECLASS")
    # ['3.0']

Inspecting a collection
-------------------------

Use ``pystac`` directly for fine-grained inspection:

.. code-block:: python

    col = disc.get_collection("CCI_BIOMASS")
    print(col.title)
    print(col.description)
    print(col.extent.spatial.bboxes)

    item = col.get_item("CCI_BIOMASS_v6.0")
    print(list(item.assets.keys()))   # e.g. ['zarr']
    print(item.assets["zarr"].href)   # the HTTPS URL to the Zarr store
