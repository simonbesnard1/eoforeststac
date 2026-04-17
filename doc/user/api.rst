.. currentmodule:: eoforeststac

.. _api:

API Reference
=============

This page provides an auto-generated summary of EOForestSTAC's public API. For usage examples and conceptual background, refer to the :ref:`user` guide.

Providers
=========

Discovery
---------

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.providers.discovery.DiscoveryProvider

Data loading
------------

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.providers.zarr.ZarrProvider

Subsetting
----------

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.providers.subset.subset

Alignment
---------

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.providers.align.DatasetAligner

Base provider
-------------

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.providers.base.BaseProvider

Catalog
=======

Factory functions
-----------------

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.catalog.factory.create_collection
   eoforeststac.catalog.factory.create_item
   eoforeststac.catalog.root.build_catalog
   eoforeststac.catalog.root.build_browser_catalog

Writers
=======

Base writer
-----------

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.writers.base.BaseZarrWriter

Product writers
---------------

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.writers.CCI_biomass.CCIBiomassWriter
   eoforeststac.writers.efda.EFDAWriter
   eoforeststac.writers.gami.GAMIWriter
   eoforeststac.writers.gami_ageclass.GAMIAgeClassWriter
   eoforeststac.writers.hansen_gfc.HansenGFCWriter
   eoforeststac.writers.jrc_gfc.JRCGFCWriter
   eoforeststac.writers.jrc_tmf.JRCTMFWriter
   eoforeststac.writers.liu_biomass.LiuBiomassWriter
   eoforeststac.writers.potapov_height.PotapovHeightWriter
   eoforeststac.writers.potapov_lcluc.PotapovLCLUCWriter
   eoforeststac.writers.radd_europe.RADDEuropeWriter
   eoforeststac.writers.restor_landuse.RestorLanduseWriter
   eoforeststac.writers.robinson_cr.RobinsonCRWriter
   eoforeststac.writers.saatchi_biomass.SaatchiBiomassWriter
   eoforeststac.writers.forestpaths_genus.ForestPathsGenusWriter

Core utilities
==============

.. autosummary::
   :toctree: generated/
   :recursive:

   eoforeststac.core.assets.create_zarr_asset
   eoforeststac.core.config
   eoforeststac.core.zarr
