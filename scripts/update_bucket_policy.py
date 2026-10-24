"""Set the access policy of the EOForestSTAC bucket.

- the maintainers may write and delete objects;
- everyone may read everything ...
- ... except the ALS biomass data and its catalog entries, which can only be
  read from GFZ addresses (139.17.0.0/16, 10.0.0.0/8): the producers asked to
  keep V1.0 within GFZ. The explorer's tile server runs on a GFZ VM, so it
  keeps working; colleagues on the GFZ network or VPN can read it too.

    python scripts/update_bucket_policy.py            # show the policy
    python scripts/update_bucket_policy.py --apply    # set it

Ceph only accepts principals as arn:aws:iam:::user/<name>. The previous
policy is printed before it is replaced, so it can be restored.
"""

from __future__ import annotations

import argparse
import json

import boto3

BUCKET = "dog.atlaseo-glm.eo-gridded-data"
MAINTAINERS = ["dog-oidc-besnard", "dog-oidc-magnus", "dog-oidc-felixd"]
GFZ_NETWORKS = ["139.17.0.0/16", "10.0.0.0/8"]
# Readable from GFZ addresses only
GFZ_ONLY = [
    "collections/ALS_BIOMASS_PRODUCTS/*",  # data stores and pyramids
    "collections/als-biomass/*",  # internal catalog entries
    "collections/_gfz_only_check/*",  # a test file, to check the rule from outside
]


def policy() -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "MaintainersWrite",
                "Effect": "Allow",
                "Principal": {"AWS": [f"arn:aws:iam:::user/{u}" for u in MAINTAINERS]},
                "Action": ["s3:PutObject", "s3:DeleteObject"],
                "Resource": f"arn:aws:s3:::{BUCKET}/*",
            },
            {
                "Sid": "PublicRead",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{BUCKET}/*",
            },
            {
                "Sid": "GfzOnlyRead",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": [f"arn:aws:s3:::{BUCKET}/{p}" for p in GFZ_ONLY],
                "Condition": {"NotIpAddress": {"aws:SourceIp": GFZ_NETWORKS}},
            },
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="Set the policy (default: show it)")
    ap.add_argument("--profile", default="atlaseo-glm")
    args = ap.parse_args()

    s3 = boto3.Session(profile_name=args.profile).client("s3", endpoint_url="https://s3.gfz.de")
    new = json.dumps(policy(), indent=2)
    if not args.apply:
        print(new)
        print("\nDry run; re-run with --apply to set it.")
        return
    try:
        print("Previous policy:\n" + s3.get_bucket_policy(Bucket=BUCKET)["Policy"])
    except s3.exceptions.ClientError:
        print("No previous policy.")
    s3.put_bucket_policy(Bucket=BUCKET, Policy=new)
    print(f"\nPolicy set on {BUCKET}.")


if __name__ == "__main__":
    main()
