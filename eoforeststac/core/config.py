# Base S3 path for the catalog and collections
BASE_S3_URL = "s3://dog.atlaseo-glm.eo-gridded-data/collections"
S3_HTTP_BASE = "https://s3.gfz.de/dog.atlaseo-glm.eo-gridded-data/collections"
# The browser-facing catalog (https links) lives under public/; its self links
# must point there, not at the internal (s3://) copy one level up
S3_HTTP_PUBLIC_BASE = f"{S3_HTTP_BASE}/public"

# AWS S3 profile and endpoint used with fsspec
S3_PROFILE = "atlaseo-glm"
S3_ENDPOINT_URL = "https://s3.gfz.de"
