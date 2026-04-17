.. currentmodule:: eoforeststac

.. _whyeoforeststac:

Overview: Why EOForestSTAC?
============================

EOForestSTAC is a Python package built to simplify access to **global forest Earth Observation datasets** hosted on cloud-native object storage. It exposes a curated STAC catalog of analysis-ready Zarr archives and provides a clean Python interface for discovery, loading, subsetting, and combining multiple products.

The motivation behind EOForestSTAC
------------------------------------

Working with large-scale forest EO datasets presents several challenges:

- **Fragmented products**: biomass, disturbance, canopy height, forest age, and land-use datasets are published by different groups in different formats, often as multi-gigabyte GeoTIFFs.
- **Version proliferation**: most products have multiple versions and spatial resolutions; tracking what is available and what is current requires manual bookkeeping.
- **Download overhead**: traditional workflows require downloading complete datasets before any analysis, even when only a small region and time range are needed.
- **Grid inconsistency**: combining products from different sources requires reprojection and resampling to a common grid.

EOForestSTAC was designed to address all of these by combining a **STAC metadata catalog** with **Zarr cloud-native storage**, enabling lazy streaming access with no local downloads.

What EOForestSTAC enables
--------------------------

- **Zero-download access**: datasets are streamed from Ceph S3 directly into an ``xarray.Dataset``; only the requested spatial and temporal subset is transferred.
- **Unified catalog**: all products, versions, and spatial resolutions are registered in a single STAC catalog browsable via Python or the interactive STAC Browser.
- **Multi-resolution support**: products like GAMI age-class fractions are available at five spatial resolutions; the ``resolution=`` parameter selects the right asset automatically.
- **Spatial subsetting**: ``subset()`` clips any dataset to a GeoDataFrame geometry with automatic CRS reprojection.
- **Multi-product alignment**: ``DatasetAligner`` reprojects and resamples multiple datasets onto a common grid in one call.
- **Lazy evaluation**: all operations are backed by Dask and xarray; computation is deferred until ``.compute()`` is called.

Catalog structure
------------------

The catalog is organized as a three-level hierarchy:

.. code-block:: text

   catalog.json  (root)
   ├── biomass-carbon/          ← theme catalog
   │   ├── CCI_BIOMASS/         ← collection (one per product)
   │   │   ├── CCI_BIOMASS_v6.0 ← item (one per version)
   │   │   └── CCI_BIOMASS_v7.0
   │   ├── SAATCHI_BIOMASS/
   │   └── LIU_BIOMASS/
   ├── disturbance-change/
   │   ├── EFDA/
   │   ├── HANSEN_GFC/
   │   └── ...
   ├── structure-demography/
   │   ├── POTAPOV_HEIGHT/
   │   └── GAMI_AGECLASS/       ← multi-resolution: one item, 5 resolution assets
   └── ...

Each item holds one or more Zarr assets (one per spatial resolution for multi-resolution products). The ``ZarrProvider`` and ``DiscoveryProvider`` classes navigate this hierarchy transparently.

Core components of EOForestSTAC
---------------------------------

1. :py:class:`eoforeststac.providers.discovery.DiscoveryProvider`: navigates the STAC catalog hierarchy to list themes, collections, versions, and asset keys.

2. :py:class:`eoforeststac.providers.zarr.ZarrProvider`: opens a specific dataset version as an ``xarray.Dataset`` streamed from Ceph S3.

3. :py:func:`eoforeststac.providers.subset.subset`: clips a dataset to a spatial geometry and optional time range.

4. :py:class:`eoforeststac.providers.align.DatasetAligner`: reprojects and resamples multiple datasets onto a shared reference grid.

Available product themes
-------------------------

+------------------------------+---------------------------------------------+
| Theme                        | Products (examples)                         |
+==============================+=============================================+
| ``biomass-carbon``           | CCI Biomass, Saatchi Biomass, Liu Biomass,  |
|                              | GAMI                                        |
+------------------------------+---------------------------------------------+
| ``disturbance-change``       | EFDA (forest disturbances), Hansen GFC,     |
|                              | RADD Europe, JRC TMF, JRC GFC,              |
|                              | Robinson Carbon Recovery                    |
+------------------------------+---------------------------------------------+
| ``structure-demography``     | Potapov Canopy Height, GAMI Age-Class       |
|                              | Fractions (multi-resolution)                |
+------------------------------+---------------------------------------------+
| ``land-use``                 | Potapov LCLUC, RESTOR Land Use,             |
|                              | ForestPaths Genus                           |
+------------------------------+---------------------------------------------+

Goals and aspirations
----------------------

EOForestSTAC's primary objective is to provide a reproducible, interoperable platform for forest EO research, including:

- **Multi-source synthesis**: load biomass, disturbance, canopy height, and forest age data onto a common grid for integrated analyses.
- **Temporal change detection**: access all available versions of a product and compare them with ``.sel(time=...)``.
- **Carbon cycle studies**: combine multiple products to quantify forest carbon stocks, changes, and uncertainty.

---

A project from GFZ Potsdam
===========================

EOForestSTAC was developed by Simon Besnard from the `Global Land Monitoring Group <https://www.gfz.de/en/section/remote-sensing-and-geoinformatics/topics/global-land-monitoring>`_ at the Helmholtz Centre Potsdam GFZ German Research Centre for Geosciences. The project applies cloud-native data principles established in the `gedidb <https://github.com/simonbesnard1/gedidb>`_ and `icesat2db <https://github.com/simonbesnard1/icesat2db>`_ packages to global gridded forest EO products. It is open-source (EUPL-1.2) and welcomes contributions from the research community.

---
