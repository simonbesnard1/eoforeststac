"""Check every Zarr store on S3 against the catalog's conventions.

    eoforeststac-check                       # newest version of every store
    eoforeststac-check --collection HANSEN_GFC
    eoforeststac-check --all-versions --level info

Exits with status 1 when a store has an error, so it can gate publishing.
Exceptions a product really has (e.g. 0 = no data in LIU) are accepted in
its config under "checks": {"accept": [...]} and not reported.
"""

from __future__ import annotations

import argparse
import sys

from eoforeststac.checks.conventions import LEVELS, accepted, check_store
from eoforeststac.core.config import BASE_S3_URL, S3_PROFILE
from eoforeststac.pyramids.cli import make_fs
from eoforeststac.pyramids.maintain import find_stores, product_configs


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eoforeststac-check",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--collection",
        action="append",
        default=[],
        help="Only this collection (S3 folder); repeatable",
    )
    parser.add_argument(
        "--all-versions",
        action="store_true",
        help="Check older versions too (default: newest only)",
    )
    parser.add_argument(
        "--level",
        choices=LEVELS,
        default="warning",
        help="Lowest level to show (default: warning)",
    )
    parser.add_argument("--profile", help=f"Credential profile (default {S3_PROFILE})")
    parser.add_argument("--prefix", default=BASE_S3_URL)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = make_parser().parse_args(argv)
    fs = make_fs(args.profile)
    prefix = args.prefix.removeprefix("s3://").rstrip("/")
    shown = set(LEVELS[: LEVELS.index(args.level) + 1])

    stores, unfinished, _ = find_stores(fs, prefix)
    if not args.all_versions:
        newest = {}
        for s in stores:
            key = (s.collection, s.name)
            if key not in newest or s.version > newest[key].version:
                newest[key] = s
        stores = list(newest.values())
    if args.collection:
        stores = [s for s in stores if s.collection in args.collection]
        unfinished = [p for p in unfinished if p.split("/")[-2] in args.collection]

    configs = product_configs()
    counts = {level: 0 for level in LEVELS}
    for store in sorted(stores, key=lambda s: s.path):
        accept = configs.get(store.collection, {}).get("checks", {}).get("accept", [])
        findings = [
            f for f in accepted(check_store(fs, store.path), accept) if f.level in shown
        ]
        mark = (
            "ERROR"
            if any(f.level == "error" for f in findings)
            else "ok" if not findings else "warn"
        )
        print(f"{mark:5s} {store.label}")
        # One line per rule: the same finding on 27 variables is one problem
        by_rule: dict[tuple[str, str], list] = {}
        for f in findings:
            by_rule.setdefault((f.level, f.rule), []).append(f)
        for (level, rule), group in by_rule.items():
            counts[level] += 1
            names = [f.variable for f in group if f.variable]
            where = (
                f" [{names[0]}]"
                if len(names) == 1
                else (
                    f" [{len(names)} variables: {', '.join(names[:3])}{', ...' if len(names) > 3 else ''}]"
                    if names
                    else ""
                )
            )
            print(f"      {level:7s} {rule}{where}: {group[0].message}")
    for path in unfinished:
        print(f"wait  {path.rsplit('/', 1)[-1]} (still being written)")
    print(
        f"\n{len(stores)} stores: "
        + ", ".join(f"{n} {lvl}" for lvl, n in counts.items() if lvl in shown)
    )
    if counts["error"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
