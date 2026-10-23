"""The conventions every Zarr store in the catalog should follow, as checks.

Each check looks only at a store's metadata (consolidated ``.zmetadata``) and
two small coordinate reads (first/last latitude, time units), so checking the
whole bucket takes seconds. A finding has a level:

  error    the explorer or the analytics would show wrong values
  warning  works today, but differs from the other products
  info     harmless leftover worth cleaning at the next rewrite

A product can accept a known exception in its config, e.g. LIU, whose source
maps use 0 for no data::

    "checks": {"accept": ["zero-fill"]}             # every variable
    "checks": {"accept": ["zero-fill:canopy_cover"]}  # one variable
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

import fsspec

LEVELS = ("error", "warning", "info")
GEOGRAPHIC_DIMS = ("latitude", "longitude")
PROJECTED_DIMS = ("y", "x")
SPATIAL = {"latitude", "longitude", "lat", "lon", "y", "x"}


@dataclass
class Finding:
    level: str
    rule: str
    variable: str  # "" for the whole store
    message: str

    def key(self) -> str:
        return f"{self.rule}:{self.variable}" if self.variable else self.rule


def _crs_kind(metadata: dict[str, Any]) -> str | None:
    """'geographic', 'projected' or None, from the CRS variable's WKT."""
    for name in ("spatial_ref", "crs"):
        attrs = metadata.get(f"{name}/.zattrs")
        if not attrs:
            continue
        wkt = str(attrs.get("crs_wkt") or attrs.get("spatial_ref") or "")
        if wkt.startswith(("PROJCS", "PROJCRS")):
            return "projected"
        if wkt.startswith(("GEOGCS", "GEOGCRS")):
            return "geographic"
    return None


def _gridded(metadata: dict[str, Any]) -> dict[str, tuple[dict, dict]]:
    """name -> (.zarray, .zattrs) of every variable with two spatial dims."""
    out = {}
    for key, array in metadata.items():
        if not key.endswith("/.zarray") or key.count("/") != 1:
            continue
        name = key[: -len("/.zarray")]
        attrs = metadata.get(f"{name}/.zattrs", {})
        dims = attrs.get("_ARRAY_DIMENSIONS", [])
        if len(SPATIAL.intersection(dims)) >= 2:
            out[name] = (array, attrs)
    return out


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def check_metadata(
    metadata: dict[str, Any],
    y_values: tuple[float, float] | None = None,
) -> list[Finding]:
    """Findings for one store from its consolidated metadata.

    ``y_values`` is (first, last) of the latitude/y coordinate, which the
    metadata does not hold; without it the orientation check is skipped.
    """
    findings: list[Finding] = []

    def add(level: str, rule: str, variable: str, message: str) -> None:
        findings.append(Finding(level, rule, variable, message))

    kind = _crs_kind(metadata)
    if kind is None:
        add("warning", "crs-missing", "", "no CRS variable (spatial_ref) with a WKT")
    crs_vars = {k.split("/")[0] for k in metadata if k.endswith("/.zattrs")}

    time = metadata.get("time/.zattrs")
    if time is not None and "since" not in str(time.get("units", "")):
        add(
            "warning",
            "time-not-dates",
            "time",
            f"time is stored as plain numbers (units {time.get('units')!r}), "
            "not as CF dates ('days since ...')",
        )

    for name, (array, attrs) in sorted(_gridded(metadata).items()):
        dims = attrs.get("_ARRAY_DIMENSIONS", [])
        fill = array.get("fill_value")
        dtype = str(array.get("dtype", ""))
        is_int = bool(re.match(r"^[<>|]?[iu]", dtype))
        categorical = any(
            k in attrs for k in ("flag_values", "flag_meanings", "legend")
        )

        if fill is None:
            add(
                "error",
                "fill-undeclared",
                name,
                "no fill value: no-data pixels are read as real values",
            )
        elif is_int and _number(fill) == 0:
            add(
                "warning",
                "zero-fill",
                name,
                "0 is declared as no data, so real zeros are dropped; "
                "accept it in the product config if 0 really means no data",
            )

        expected = (
            GEOGRAPHIC_DIMS
            if kind == "geographic"
            else PROJECTED_DIMS if kind else None
        )
        if expected and not set(expected).issubset(dims):
            add(
                "warning",
                "dim-names",
                name,
                f"{kind} grid with dimensions {dims}; expected {list(expected)}",
            )
        if "time" in dims and dims[0] != "time":
            add(
                "warning",
                "time-not-first",
                name,
                f"time is not the first dimension: {dims}",
            )

        gm = attrs.get("grid_mapping")
        if not gm or gm not in crs_vars:
            add(
                "warning",
                "grid-mapping",
                name,
                "no grid_mapping attribute naming the CRS variable",
            )

        units = attrs.get("units")
        if not units and not categorical:
            add(
                "warning", "units-missing", name, "no units (and not marked as classes)"
            )
        elif units and "/" in str(units):
            add(
                "info",
                "units-style",
                name,
                f"units {units!r}: write them as CF does, e.g. 'Mg ha-1'",
            )

        rng = attrs.get("display_range")
        if isinstance(rng, list) and len(rng) == 2:
            lo, hi = (_number(v) for v in rng)
            fill_value = _number(fill)
            vmin, vmax = _number(attrs.get("valid_min")), _number(
                attrs.get("valid_max")
            )
            # A negative sentinel (-9999) read as data pulls the low end down to
            # it; a range starting at a fill of 0 is fine (0 is masked)
            if (
                fill_value is not None
                and lo is not None
                and (lo < fill_value or (fill_value < 0 and lo <= fill_value))
            ):
                add(
                    "error",
                    "range-includes-fill",
                    name,
                    f"legend range {rng} reaches the fill value {fill}",
                )
            elif (vmin is not None and lo is not None and lo < vmin) or (
                vmax is not None and hi is not None and hi > vmax
            ):
                add(
                    "error",
                    "range-outside-valid",
                    name,
                    f"legend range {rng} outside the valid range {vmin}..{vmax}",
                )

        if (
            _number(attrs.get("scale_factor")) == 1
            and _number(attrs.get("add_offset", 0)) == 0
        ):
            add(
                "info",
                "identity-scale",
                name,
                "scale_factor 1 / add_offset 0 attributes do nothing",
            )

    if y_values is not None and y_values[0] < y_values[1]:
        add(
            "warning",
            "y-ascending",
            "",
            "latitude/y runs south to north; the others run north to south",
        )
    return findings


def accepted(findings: Iterable[Finding], accept: Iterable[str]) -> list[Finding]:
    """Drop findings a product config accepts (rule or rule:variable)."""
    accept = set(accept)
    return [f for f in findings if f.rule not in accept and f.key() not in accept]


def check_store(fs: fsspec.AbstractFileSystem, path: str) -> list[Finding]:
    """Findings for the store at ``path`` (bucket/key or local path)."""
    try:
        metadata = json.loads(fs.cat(f"{path}/.zmetadata"))["metadata"]
    except (FileNotFoundError, KeyError, ValueError):
        return [
            Finding(
                "error", "unconsolidated", "", "no consolidated metadata (.zmetadata)"
            )
        ]
    y_values = None
    for name in ("latitude", "lat", "y"):
        if f"{name}/.zarray" in metadata:
            try:
                import zarr

                y = zarr.open_array(fs.get_mapper(f"{path}/{name}"), mode="r")
                y_values = (float(y[0]), float(y[-1]))
            except Exception:  # coordinate unreadable: skip the orientation check
                pass
            break
    return check_metadata(metadata, y_values)
