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
     - ESA CCI Aboveground Biomass
     - Global aboveground biomass (Mg/ha) at 100 m, multiple epochs. Versions 4.0–6.0.
   * - ``SAATCHI_BIOMASS``
     - Saatchi Aboveground Biomass
     - Pan-tropical aboveground biomass from Saatchi et al.
   * - ``LIU_BIOMASS``
     - Liu Aboveground Biomass
     - Global aboveground biomass time-series from Liu et al.
   * - ``GAMI``
     - GAMI Aboveground Biomass
     - Global age-based modelled biomass from the GAMI ensemble.

Disturbance & Change (``disturbance-change``)
----------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Collection ID
     - Title
     - Description
   * - ``EFDA``
     - European Forest Disturbance Atlas
     - Annual disturbance events across European forests (fire, wind, bark beetle, …).
   * - ``HANSEN_GFC``
     - Hansen Global Forest Change
     - Annual tree cover loss and gain (Hansen et al., 2013+).
   * - ``RADD_EUROPE``
     - RADD Europe Alerts
     - Near-real-time forest disturbance alerts over Europe from Sentinel-1.
   * - ``JRC_TMF``
     - JRC Tropical Moist Forest
     - Annual deforestation and degradation in tropical moist forests.
   * - ``JRC_GFC``
     - JRC Global Forest Cover
     - Annual global forest cover maps from the Joint Research Centre.
   * - ``ROBINSON_CR``
     - Robinson Carbon Recovery
     - Forest carbon recovery trajectories after disturbance.

Structure & Demography (``structure-demography``)
--------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Collection ID
     - Title
     - Description
   * - ``POTAPOV_HEIGHT``
     - Potapov Canopy Height
     - Global forest canopy height at 30 m from Potapov et al.
   * - ``GAMI_AGECLASS``
     - GAMI Age-Class Fractions
     - Global forest age-class fraction product (12 age classes, 20 members, 5 resolutions: 1°–0.0833°). Reference years 2010 and 2020.

Land Use (``land-use``)
------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 30 45

   * - Collection ID
     - Title
     - Description
   * - ``POTAPOV_LCLUC``
     - Potapov Land Cover / Land Use Change
     - Annual global cropland and land use change maps.
   * - ``RESTOR_LANDUSE``
     - RESTOR Land Use
     - Annual land use / land cover classification for Brazil at ~9 m resolution.
   * - ``FORESTPATHS_GENUS``
     - ForestPaths Genus
     - Forest genus classification map for Europe.

Adding new collections
-----------------------

To register a new product in the catalog, add entries to:

1. ``eoforeststac/products/<product>.py`` — product metadata and S3 path config.
2. ``eoforeststac/catalog/<product>.py`` — STAC collection and item factory.
3. ``eoforeststac/catalog/root.py`` — register in ``DEFAULT_VERSIONS`` and ``_product_specs()``.

See :ref:`devindex` for a full contributor guide.
