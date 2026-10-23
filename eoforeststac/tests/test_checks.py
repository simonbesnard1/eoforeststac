import json

import fsspec
import numpy as np
import pytest
import zarr

from eoforeststac.checks.conventions import accepted, check_metadata, check_store

GEO_WKT = 'GEOGCS["WGS 84",DATUM["WGS_1984"]]'
PROJ_WKT = 'PROJCS["ETRS89 / LAEA Europe",GEOGCS["ETRS89"]]'


def metadata(
    dims=("time", "latitude", "longitude"),
    fill=-9999.0,
    dtype="<f4",
    attrs=None,
    wkt=GEO_WKT,
    time_units="days since 2000-01-01",
):
    """Consolidated metadata of a one-variable store that follows the rules."""
    var_attrs = {
        "_ARRAY_DIMENSIONS": list(dims),
        "units": "Mg ha-1",
        "grid_mapping": "spatial_ref",
    }
    var_attrs.update(attrs or {})
    md = {
        "v/.zarray": {
            "shape": [1, 10, 10][: len(dims)],
            "dtype": dtype,
            "fill_value": fill,
        },
        "v/.zattrs": var_attrs,
        "spatial_ref/.zarray": {"shape": [], "dtype": "<i8", "fill_value": None},
        "spatial_ref/.zattrs": {"crs_wkt": wkt},
    }
    if "time" in dims:
        md["time/.zattrs"] = {"_ARRAY_DIMENSIONS": ["time"], "units": time_units}
    return md


def rules(findings):
    return {f.rule for f in findings}


def test_a_conforming_store_has_no_findings():
    assert check_metadata(metadata(), y_values=(89.5, -89.5)) == []


@pytest.mark.parametrize(
    "md, y, rule, level",
    [
        (metadata(fill=None), None, "fill-undeclared", "error"),
        (metadata(fill=0, dtype="|u1"), None, "zero-fill", "warning"),
        (
            metadata(attrs={"display_range": [-9999.0, 0.3]}),
            None,
            "range-includes-fill",
            "error",
        ),
        (
            metadata(
                attrs={"display_range": [0, 120], "valid_min": 0, "valid_max": 100}
            ),
            None,
            "range-outside-valid",
            "error",
        ),
        (metadata(dims=("time", "y", "x")), None, "dim-names", "warning"),
        (
            metadata(dims=("time", "latitude", "longitude"), wkt=PROJ_WKT),
            None,
            "dim-names",
            "warning",
        ),
        (
            metadata(dims=("latitude", "longitude", "time")),
            None,
            "time-not-first",
            "warning",
        ),
        (metadata(time_units=None), None, "time-not-dates", "warning"),
        (metadata(attrs={"grid_mapping": None}), None, "grid-mapping", "warning"),
        (metadata(attrs={"units": None}), None, "units-missing", "warning"),
        (metadata(attrs={"units": "Mg/ha"}), None, "units-style", "info"),
        (
            metadata(attrs={"scale_factor": 1.0, "add_offset": 0.0}),
            None,
            "identity-scale",
            "info",
        ),
        (metadata(), (-89.5, 89.5), "y-ascending", "warning"),
    ],
)
def test_each_rule(md, y, rule, level):
    found = {f.rule: f.level for f in check_metadata(md, y_values=y)}
    assert found.get(rule) == level, found


def test_fill_zero_with_range_from_zero_is_fine():
    md = metadata(fill=0, dtype="|u1", attrs={"display_range": [0, 80]})
    assert "range-includes-fill" not in rules(check_metadata(md))


def test_classes_need_no_units():
    md = metadata(attrs={"units": None, "flag_values": [1, 2]})
    assert "units-missing" not in rules(check_metadata(md))


def test_accepted_by_rule_or_by_variable():
    md = metadata(fill=0, dtype="|u1", attrs={"units": None})
    findings = check_metadata(md)
    assert rules(accepted(findings, ["zero-fill"])) == {"units-missing"}
    assert rules(accepted(findings, ["zero-fill:v", "units-missing:other"])) == {
        "units-missing"
    }


def test_check_store_reads_orientation(tmp_path):
    path = str(tmp_path / "s.zarr")
    g = zarr.open_group(path, mode="w")
    lat = np.linspace(-89.5, 89.5, 4)  # south to north
    kwargs = {"zarr_format": 2} if not zarr.__version__.startswith("2") else {}
    if kwargs:
        g = zarr.open_group(path, mode="w", **kwargs)
        g.create_array("latitude", shape=(4,), dtype="f8")[:] = lat
    else:
        g.create_dataset("latitude", data=lat)
    g["latitude"].attrs["_ARRAY_DIMENSIONS"] = ["latitude"]
    zarr.consolidate_metadata(path)
    fs = fsspec.filesystem("file")
    assert "y-ascending" in rules(check_store(fs, path))
    assert rules(check_store(fs, str(tmp_path / "missing.zarr"))) == {"unconsolidated"}
