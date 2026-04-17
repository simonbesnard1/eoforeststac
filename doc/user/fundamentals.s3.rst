.. _fundamentals-s3:

#################
S3 / HTTPS Access
#################

All datasets are stored on GFZ Ceph object storage and are accessible either via **anonymous HTTPS** (read-only, no credentials) or via **authenticated S3** (for data producers with write access).

Anonymous HTTPS access (recommended for users)
-----------------------------------------------

All public assets are served as HTTPS URLs. Both ``DiscoveryProvider`` and ``ZarrProvider`` default to anonymous access when ``anon=True``:

.. code-block:: python

    from eoforeststac.providers.zarr import ZarrProvider

    provider = ZarrProvider(
        catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
        endpoint_url="https://s3.gfz-potsdam.de",
        anon=True,
    )

    ds = provider.open_dataset("CCI_BIOMASS", "6.0")

No credentials are required. Data is streamed over HTTPS directly from the Ceph object store.

Authenticated S3 access (for data producers)
----------------------------------------------

If you have write access to the bucket (e.g. for uploading new product versions), initialise the provider with credentials:

.. code-block:: python

    provider = ZarrProvider(
        catalog_url="https://s3.gfz-potsdam.de/dog.atlaseo-glm.eo-gridded-data/collections/public/catalog.json",
        endpoint_url="https://s3.gfz-potsdam.de",
        anon=False,
        aws_access_key_id="YOUR_ACCESS_KEY",
        aws_secret_access_key="YOUR_SECRET_KEY",
    )

Using boto3 / AWS profiles
---------------------------

If you manage credentials via ``~/.aws/credentials`` or environment variables, use ``boto3`` to retrieve them:

.. code-block:: python

    import boto3

    session = boto3.Session(profile_name="atlas-eo-glm")
    creds = session.get_credentials().get_frozen_credentials()

    provider = ZarrProvider(
        catalog_url="https://s3.gfz-potsdam.de/.../catalog.json",
        endpoint_url="https://s3.gfz-potsdam.de",
        anon=False,
        aws_access_key_id=creds.access_key,
        aws_secret_access_key=creds.secret_key,
    )

Security considerations
-----------------------

- Never hardcode credentials in scripts. Use environment variables or an AWS credentials file.
- For public read access always use ``anon=True``.
- Restrict bucket policies so that only authorised users have write access.
- The GFZ Ceph bucket has CORS configured to allow ``GET`` and ``HEAD`` requests from any origin, so datasets can be streamed directly from browser-based environments.
