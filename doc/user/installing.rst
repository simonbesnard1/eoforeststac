.. _installing:

Installation
============

Dependencies
------------

EOForestSTAC requires Python ≥ 3.10 and the following core dependencies:

+-------------------+-----------------+----------------------------------------------+
| Dependency        | Minimum Version | Purpose                                      |
+===================+=================+==============================================+
| pystac            | 1.9             | STAC catalog reading and navigation          |
+-------------------+-----------------+----------------------------------------------+
| xarray            | 2024.1          | Dataset abstraction, lazy I/O                |
+-------------------+-----------------+----------------------------------------------+
| zarr              | 2.16            | Cloud-native array storage backend           |
+-------------------+-----------------+----------------------------------------------+
| fsspec            | 2024.1          | Filesystem abstraction (S3, HTTPS)           |
+-------------------+-----------------+----------------------------------------------+
| s3fs              | 2024.1          | S3-compatible object storage support         |
+-------------------+-----------------+----------------------------------------------+
| rioxarray         | 0.15            | CRS handling and spatial operations          |
+-------------------+-----------------+----------------------------------------------+
| numpy             | 1.26            | Array operations                             |
+-------------------+-----------------+----------------------------------------------+
| pandas            | 2.0             | Discovery tables                             |
+-------------------+-----------------+----------------------------------------------+
| geopandas         | 0.14            | Geometry input for spatial subsetting        |
+-------------------+-----------------+----------------------------------------------+
| shapely           | 2.0             | Geometry operations                          |
+-------------------+-----------------+----------------------------------------------+

Installation Instructions
--------------------------

Install directly from GitHub (recommended):

.. code-block:: bash

    python -m pip install "git+https://github.com/simonbesnard1/eoforeststac.git"

Or clone and install in editable mode for development:

.. code-block:: bash

    git clone https://github.com/simonbesnard1/eoforeststac.git
    cd eoforeststac
    pip install -e .

Development install
-------------------

The development environment includes pytest for running the test suite:

.. code-block:: bash

    git clone https://github.com/simonbesnard1/eoforeststac.git
    cd eoforeststac
    pip install -e ".[dev]"
    pytest eoforeststac/tests/ -v

Verifying the install
---------------------

.. code-block:: python

    import eoforeststac
    print(eoforeststac.__version__)
