.. _catalog-overview:

Catalog Overview
================

This page gives a complete overview of all collections currently registered in the EOForestSTAC catalog, organised by theme.

Themes
------

The catalog is divided into four thematic groups. Use ``DiscoveryProvider.list_themes()`` to retrieve this list programmatically.

Biomass & Carbon (``biomass-carbon``)
--------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Collection ID
     - Title
     - Description
   * - ``CCI_BIOMASS``
     - ESA CCI Biomass – Global annual aboveground biomass
     - Global aboveground biomass (Mg/ha) at 100 m, multiple epochs.
   * - ``SAATCHI_BIOMASS``
     - Saatchi & Yu – Global aboveground biomass
     - Global aboveground biomass at 100 m (Saatchi & Yu 2020).
   * - ``LIU_BIOMASS``
     - Liu et al. – Europe aboveground biomass, canopy cover, and canopy height
     - European aboveground biomass, canopy cover, and canopy height at 30 m.
   * - ``ROBINSON_CR``
     - Robinson et al. – Chapman-Richards growth-curve parameters
     - Secondary-forest aboveground carbon dynamics at 1 km.

Disturbance & Change (``disturbance-change``)
----------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Collection ID
     - Title
     - Description
   * - ``EFDA``
     - European Forest Disturbance Atlas (EFDA)
     - Annual disturbance maps for European forests (fire, wind, bark beetle, …) at 30 m.
   * - ``JRC_TMF``
     - JRC Tropical Moist Forests (TMF)
     - Forest change (degradation, deforestation, regrowth) at 30 m.
   * - ``HANSEN_GFC``
     - Hansen Global Forest Change (GFC)
     - Tree cover and annual loss/gain at 30 m.
   * - ``JRC_GFC2020``
     - JRC Global Forest Cover 2020 (GFC2020)
     - Forest presence/absence at 10 m.
   * - ``RADD_EUROPE``
     - RADD Europe
     - Monthly forest disturbance occurrence from Sentinel-1 at 10 m.

Structure & Demography (``structure-demography``)
--------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Collection ID
     - Title
     - Description
   * - ``GAMI``
     - Global Age Mapping Integration (GAMI)
     - Global forest age ensemble at 100 m.
   * - ``GAMI_AGECLASS``
     - GAMI – Global Forest Age-Class Fractions
     - Forest age-class fractions (12 classes, 20 ensemble members) at 5 resolutions: 1°–0.0833°. Reference years 2010 and 2020.
   * - ``POTAPOV_HEIGHT``
     - Global Canopy Height (Potapov et al.)
     - Global forest canopy height at 30 m.
   * - ``FORESTPATHS_GENUS``
     - ForestPaths – European Tree Genus Map 2020
     - European tree genus classification at 10 m.

Land Use & Land Cover (``land-use-land-cover``)
------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Collection ID
     - Title
     - Description
   * - ``RESTOR_LANDUSE``
     - Annual Land Use and Land Cover maps for the Brazilian Amazon
     - Annual LULC classification for the Brazilian Amazon (2000–2022) at 30 m.
   * - ``Potapov_LCLUC``
     - Potapov Land Cover and Land Use Change 2000–2020
     - Global cropland and land use change maps at 30 m.

Adding new collections
-----------------------

To register a new product in the catalog, add entries to:

1. ``eoforeststac/products/<product>.py`` — product metadata and S3 path config.
2. ``eoforeststac/catalog/<product>.py`` — STAC collection and item factory.
3. ``eoforeststac/catalog/root.py`` — register in ``DEFAULT_VERSIONS`` and ``_product_specs()``.

See :ref:`devindex` for a full contributor guide.
