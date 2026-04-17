.. _devindex:

*****************************
Contributing to EOForestSTAC
*****************************

.. highlight:: shell

Overview
========

We welcome your skills and enthusiasm for the EOForestSTAC project! There are many ways to contribute beyond writing code: bug reports, documentation improvements, usage examples, new product integrations, and feature suggestions are all valuable.

Types of Contributions
-----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/simonbesnard1/eoforeststac/issues.

Please include:

* Your operating system name and version.
* The output of ``python -c "import eoforeststac; print(eoforeststac.__version__)"``
* A minimal reproducible example.
* The full traceback.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs tagged ``"bug"`` and ``"help wanted"``. These are open to anyone.

Implement Features
~~~~~~~~~~~~~~~~~~

Look for issues tagged ``"enhancement"`` and ``"help wanted"``. Before starting work on a large feature, open an issue first to discuss the design.

Add a New Product
~~~~~~~~~~~~~~~~~~

To add a new EO product to the catalog:

1. Add a product config in ``eoforeststac/products/<product>.py``.
2. Add a catalog module in ``eoforeststac/catalog/<product>.py``.
3. Add a writer in ``eoforeststac/writers/<product>.py`` that extends ``BaseZarrWriter``.
4. Register the product in ``eoforeststac/catalog/root.py``.

See the ``CCI_BIOMASS`` or ``GAMI_AGECLASS`` implementations as templates.

Write Documentation
~~~~~~~~~~~~~~~~~~~~

EOForestSTAC documentation lives in ``doc/``. Improvements to explanations, additional usage examples, and fixes to typos are always welcome.

Submit Feedback
~~~~~~~~~~~~~~~

Use the `GitHub Discussions <https://github.com/simonbesnard1/eoforeststac/discussions>`_ board for questions, ideas, and general feedback.

Development Setup
-----------------

1. Fork the repository on GitHub.

2. Clone your fork and install in editable mode:

   .. code-block:: bash

       git clone https://github.com/YOUR_USERNAME/eoforeststac.git
       cd eoforeststac
       pip install -e ".[dev]"

3. Create a feature branch:

   .. code-block:: bash

       git checkout -b feature/my-new-feature

4. Make your changes, add tests, and verify everything passes:

   .. code-block:: bash

       pytest eoforeststac/tests/ -v --cov=eoforeststac

5. Check code style (Ruff):

   .. code-block:: bash

       ruff check eoforeststac/
       ruff format --check eoforeststac/

   To auto-format:

   .. code-block:: bash

       ruff format eoforeststac/

6. Commit and push to your fork, then open a pull request.

Code Style
----------

EOForestSTAC uses `Ruff <https://docs.astral.sh/ruff/>`_ for linting and formatting with a line length of 100 characters. All code must pass ``ruff check`` and ``ruff format --check`` before merging.

Tests
-----

Tests live in ``eoforeststac/tests/``. The test suite uses `pytest <https://docs.pytest.org>`_.

Run the full suite:

.. code-block:: bash

    pytest eoforeststac/tests/ -v --cov=eoforeststac --cov-report=term-missing

Building the Documentation
--------------------------

.. code-block:: bash

    cd doc
    python -m sphinx -b html . _build/html
    # Open _build/html/index.html in a browser

Pull Request Guidelines
-----------------------

Before submitting a pull request:

1. Add tests for any new functionality.
2. Update docstrings (NumPy style) for any changed public functions.
3. Ensure ``pytest eoforeststac/tests/`` passes with no failures.
4. Ensure ``ruff check eoforeststac/`` passes with no errors.
5. Update ``doc/`` if your change affects user-visible behaviour.

Pull requests are reviewed by Simon Besnard (``@simonbesnard1``). Response times are best-effort; please be patient.

License
-------

By contributing to EOForestSTAC you agree that your contributions will be licensed under the `EUPL-1.2 <https://opensource.org/licenses/EUPL-1.2>`_ license.
