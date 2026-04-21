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
     - Monthly forest disturbance occurrence from Sentinel-1 at 10 m (2020–2025).

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

Direct access without installing eoforeststac
----------------------------------------------

All datasets are publicly accessible via HTTPS (i.e, no Python package or credentials
required).  Browse the `STAC Browser <https://simonbesnard1.github.io/eoforeststac/>`_
to find the Zarr asset URL for any collection/version, then stream it directly with
``xarray`` (Python) or ``Rarr`` / ``rstac`` (R).

.. tab:: Python

   Install dependencies::

      pip install xarray zarr

   Open and subset a Zarr store over HTTPS:

   .. code-block:: python

      import xarray as xr

      s3_path = (
          "https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data"
          "/collections/CCI_BIOMASS/CCI_BIOMASS_v6.0.zarr"
      )

      # Open lazily — no data is downloaded yet
      ds = xr.open_zarr(s3_path)
      print(ds)

      # Spatial + temporal slice
      agb = ds.sel(
          time="2010-01-01",
          latitude=slice(-3, -6),
          longitude=slice(-68, -62),
      ).aboveground_biomass

      agb.compute()   # triggers the actual S3 read

      # Optional: export to GeoTIFF
      import rioxarray
      agb.rio.set_spatial_dims(x_dim="longitude", y_dim="latitude")
      agb.rio.write_crs("EPSG:4326", inplace=True)
      agb.compute().rio.to_raster("agb_2010_subset.tif")

.. tab:: R

   Install dependencies:

   .. code-block:: r

      install.packages("rstac")
      BiocManager::install("Rarr")   # Bioconductor
      install.packages("terra")

   Browse the catalog with ``rstac``:

   .. code-block:: r

      library(rstac)

      s    <- stac("https://simonbesnard1.github.io/eoforeststac")
      cols <- s |> collections() |> get_request()
      print(cols)

      # Extract the Zarr href for a specific item
      items     <- s |> collections("CCI_BIOMASS") |> items() |> get_request()
      zarr_href <- items$features[[1]]$assets$zarr$href

   Read and export with ``Rarr`` over HTTPS (no credentials needed):

   .. code-block:: r

      library(Rarr)
      library(terra)

      zarr_path <- zarr_href   # from rstac above, or paste directly

      # Read coordinate arrays first (small/fast)
      lat  <- read_zarr_array(file.path(zarr_path, "latitude"))
      lon  <- read_zarr_array(file.path(zarr_path, "longitude"))
      time <- read_zarr_array(file.path(zarr_path, "time"))

      time_dates <- as.Date(time, origin = "2007-01-01")
      time_idx   <- which(time_dates == as.Date("2010-01-01"))
      lat_idx    <- which(lat >= -6  & lat <= -3)
      lon_idx    <- which(lon >= -68 & lon <= -62)

      # Read only the slice you need
      agb_subset <- read_zarr_array(
        file.path(zarr_path, "aboveground_biomass"),
        index = list(lat_idx, lon_idx, time_idx)
      )

      # Convert to SpatRaster and export
      agb_2d <- drop(agb_subset)
      r      <- rast(agb_2d)
      ext(r) <- c(min(lon[lon_idx]), max(lon[lon_idx]),
                  min(lat[lat_idx]), max(lat[lat_idx]))
      crs(r) <- "EPSG:4326"
      writeRaster(r, "agb_2010_subset.tif", overwrite = TRUE)

.. note::

   ``Rarr`` supports HTTPS endpoints directly — pass the full URL as ``zarr_path``.
   No Python bridge or S3 credentials are needed for public datasets.

Adding new collections
-----------------------

To register a new product in the catalog, add entries to:

1. ``eoforeststac/products/<product>.py`` — product metadata and S3 path config.
2. ``eoforeststac/catalog/<product>.py`` — STAC collection and item factory.
3. ``eoforeststac/catalog/root.py`` — register in ``DEFAULT_VERSIONS`` and ``_product_specs()``.

See :ref:`devindex` for a full contributor guide.
