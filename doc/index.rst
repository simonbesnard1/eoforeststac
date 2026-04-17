.. _eoforeststac_docs_mainpage:

############################
EOForestSTAC Documentation
############################

.. toctree::
   :maxdepth: 1
   :hidden:

   Installation <user/installing>
   User Guide <user/index>
   Catalog Overview <user/catalog_overview>
   API Reference <user/api>
   Examples <auto_examples/index>
   Discussions <https://github.com/simonbesnard1/eoforeststac/discussions>
   Development <user/contributing>

**EOForestSTAC** is an open-source Python package for cloud-native access to global forest Earth Observation datasets. It connects to a curated `STAC <https://stacspec.org>`_ catalog hosted on GFZ Ceph object storage and exposes all products as `Zarr <https://zarr.dev>`_ archives, readable on-demand via `xarray <https://docs.xarray.dev>`_. Spatial subsetting, temporal filtering, and multi-product alignment are available out of the box.

Explore the full catalog interactively at **https://simonbesnard1.github.io/eoforeststac/**.

.. grid:: 1 1 2 2
    :gutter: 2 3 4 4

    .. grid-item-card::
        :text-align: center

        **Getting Started**
        ^^^

        New to EOForestSTAC? Start here for a quick introduction to discovering the catalog and loading your first dataset.

        +++

        .. button-ref:: user/quick-overview
            :expand:
            :color: primary
            :click-parent:

            Explore Quick Overview

    .. grid-item-card::
        :text-align: center

        **User Guide**
        ^^^

        Dive into the User Guide for detailed explanations of the STAC catalog structure, providers, subsetting, and multi-product alignment.

        +++

        .. button-ref:: user
            :expand:
            :color: primary
            :click-parent:

            Access User Guide

    .. grid-item-card::
        :text-align: center

        **API Reference**
        ^^^

        Auto-generated reference for all public classes and functions: ``DiscoveryProvider``, ``ZarrProvider``, ``DatasetAligner``, and ``subset``.

        +++

        .. button-ref:: user/api
            :expand:
            :color: primary
            :click-parent:

            Explore API Reference

    .. grid-item-card::
        :text-align: center

        **Contributor's Guide**
        ^^^

        Want to contribute to EOForestSTAC? This guide covers how to set up a development environment, run tests, and submit pull requests.

        +++

        .. button-ref:: user/contributing
            :expand:
            :color: primary
            :click-parent:

            View Contributor's Guide
