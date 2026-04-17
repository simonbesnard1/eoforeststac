.. _fundamentals-filters:

####################################
Subsetting and Spatial Filtering
####################################

This page describes how to subset datasets spatially and temporally using :py:func:`eoforeststac.providers.subset.subset`.

Spatial subsetting
-------------------

``subset()`` clips a dataset to a polygon geometry. Geometries must be in **EPSG:4326** (geographic coordinates); they are reprojected to match the dataset CRS automatically.

.. code-block:: python

    import geopandas as gpd
    from eoforeststac.providers.subset import subset

    roi = gpd.read_file("DE-Hai.geojson")
    geometry = roi.to_crs("EPSG:4326").geometry.union_all()

    ds_subset = subset(ds, geometry=geometry)

The returned dataset has its spatial extent clipped to the bounding box of the geometry. Values outside the geometry are masked as ``NaN``.

Temporal subsetting
--------------------

Pass a ``time=`` tuple of ISO date strings to restrict the time dimension:

.. code-block:: python

    ds_subset = subset(
        ds,
        geometry=geometry,
        time=("2010-01-01", "2020-12-31"),
    )

Combined spatial and temporal subsetting
-----------------------------------------

.. code-block:: python

    ds_subset = subset(
        ds,
        geometry=geometry,
        time=("2015-01-01", "2020-12-31"),
    )

Triggering computation
-----------------------

All operations are lazy (Dask-backed). Call ``.compute()`` to load data into memory:

.. code-block:: python

    ds_loaded = ds_subset.compute()

For large datasets, load only the variables and time steps you need before calling ``.compute()``:

.. code-block:: python

    ds_loaded = ds_subset[["agb"]].sel(time="2020-01-01").compute()

Notes
-----

- The geometry must be in EPSG:4326. If your data is in a different CRS, use ``geopandas`` to reproject it first.
- ``subset()`` clips to the bounding box of the geometry plus polygon masking. Pixels outside the polygon are set to ``NaN``.
- If the dataset has no ``time`` dimension, the ``time=`` argument is silently ignored.
