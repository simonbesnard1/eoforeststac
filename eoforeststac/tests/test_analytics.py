"""Tests for area-weighted region statistics (eoforeststac.analytics)."""

import numpy as np
import pytest
import xarray as xr

from eoforeststac.analytics import (
    geometry_area_ha,
    pixel_area_ha,
    region_statistics,
)


def geographic_grid(res=1.0, value=100.0, years=None, dims=("latitude", "longitude")):
    lats = np.arange(90 - res / 2, -90, -res)
    lons = np.arange(-180 + res / 2, 180, res)
    shape = (lats.size, lons.size)
    data = np.full(shape, value, dtype="float64")
    coords = {dims[0]: lats, dims[1]: lons}
    if years is None:
        return xr.DataArray(data, dims=dims, coords=coords)
    stacked = np.stack([data * (i + 1) for i in range(len(years))])
    coords["time"] = np.array([f"{y}-01-01" for y in years], dtype="datetime64[ns]")
    return xr.DataArray(stacked, dims=("time", *dims), coords=coords)


def box(w, s, e, n):
    return {
        "type": "Polygon",
        "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
    }


def test_geographic_pixel_areas_sum_to_earth_surface():
    da = geographic_grid(res=1.0)
    area = pixel_area_ha(da, "EPSG:4326")
    expected = 510_065_621.724 * 100  # WGS84 ellipsoid surface, km^2 -> ha
    assert float(area.sum()) * da.sizes["longitude"] == pytest.approx(
        expected, rel=1e-9
    )
    # Cells shrink towards the poles
    assert float(area.isel(latitude=0)) < float(area.isel(latitude=90))


def test_constant_density_total_equals_density_times_area():
    da = geographic_grid(res=0.05, value=100.0)
    geom = box(10, 50, 12, 52)
    (row,) = region_statistics(da, geom, crs="EPSG:4326")
    assert row["mean"] == pytest.approx(100.0)
    assert row["coverage"] == pytest.approx(1.0)
    assert row["total"] == pytest.approx(100.0 * row["region_area_ha"])
    # An aligned box: ellipsoidal pixel areas match its geodesic area
    assert row["region_area_ha"] == pytest.approx(geometry_area_ha(geom), rel=1e-4)


def test_missing_values_reduce_coverage_not_mean():
    da = geographic_grid(res=0.1, value=50.0)
    da = da.where(da.longitude < 11)  # western half of the box valid
    (row,) = region_statistics(da, box(10, 0, 12, 1), crs="EPSG:4326")
    assert row["mean"] == pytest.approx(50.0)
    assert row["coverage"] == pytest.approx(0.5, rel=1e-6)
    assert row["total"] == pytest.approx(50.0 * row["valid_area_ha"])


def test_projected_grid_uses_resolution_area():
    xs = np.arange(4_000_005, 4_001_000, 10.0)  # 10 m LAEA pixels
    ys = np.arange(3_001_000 - 5, 3_000_000, -10.0)
    da = xr.DataArray(
        np.full((ys.size, xs.size), 2.0), dims=("y", "x"), coords={"y": ys, "x": xs}
    )
    assert float(pixel_area_ha(da, "EPSG:3035")) == pytest.approx(0.01)
    # A square covering the whole grid, given in the grid's own CRS
    geom = box(4_000_000, 3_000_000, 4_001_000, 3_001_000)
    (row,) = region_statistics(da, geom, crs="EPSG:3035", geometry_crs="EPSG:3035")
    assert row["region_area_ha"] == pytest.approx(100.0)  # 1 km^2
    assert row["total"] == pytest.approx(200.0)


def test_one_row_per_year_with_labels():
    da = geographic_grid(res=0.5, value=10.0, years=[2010, 2011, 2012])
    rows = region_statistics(da, box(0, 0, 5, 5), crs="EPSG:4326")
    assert [r["time"] for r in rows] == ["2010-01-01", "2011-01-01", "2012-01-01"]
    assert [round(r["mean"], 6) for r in rows] == [10.0, 20.0, 30.0]


def test_integer_fill_value_is_missing():
    da = geographic_grid(res=0.5, value=7).astype("int32")
    da = da.where(da.longitude < 2.5, -9999).astype("int32")
    da.encoding["_FillValue"] = -9999
    (row,) = region_statistics(da, box(0, 0, 5, 5), crs="EPSG:4326")
    assert row["mean"] == pytest.approx(7.0)
    assert row["coverage"] == pytest.approx(0.5, rel=1e-6)


def test_hole_is_excluded_from_region():
    da = geographic_grid(res=0.1, value=1.0)
    outer = [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]
    hole = [[1, 1], [1, 3], [3, 3], [3, 1], [1, 1]]
    with_hole = {"type": "Polygon", "coordinates": [outer, hole]}
    (full,) = region_statistics(
        da, {"type": "Polygon", "coordinates": [outer]}, crs="EPSG:4326"
    )
    (holed,) = region_statistics(da, with_hole, crs="EPSG:4326")
    assert holed["region_area_ha"] == pytest.approx(
        full["region_area_ha"] * 12 / 16, rel=1e-3
    )
    assert geometry_area_ha(with_hole) == pytest.approx(
        holed["region_area_ha"], rel=5e-3
    )


def test_lazy_dask_input_matches_eager():
    da = geographic_grid(res=0.25, value=3.0, years=[2000, 2001])
    geom = box(-3, -2, 4, 5)
    eager = region_statistics(da, geom, crs="EPSG:4326")
    lazy = region_statistics(
        da.chunk({"time": 1, "latitude": 64, "longitude": 64}), geom, crs="EPSG:4326"
    )
    for a, b in zip(eager, lazy):
        assert a["total"] == pytest.approx(b["total"])
        assert a["region_area_ha"] == pytest.approx(b["region_area_ha"])


def test_region_outside_dataset_raises():
    da = geographic_grid(res=1.0).sel(latitude=slice(10, -10))
    with pytest.raises(ValueError, match="outside"):
        region_statistics(da, box(0, 40, 5, 45), crs="EPSG:4326")


def test_unknown_kind_and_web_mercator_are_refused():
    da = geographic_grid(res=1.0)
    with pytest.raises(ValueError, match="kind"):
        region_statistics(da, box(0, 0, 1, 1), kind="median", crs="EPSG:4326")
    xs = np.arange(5.0, 100, 10)
    ys = np.arange(95.0, 0, -10)
    merc = xr.DataArray(
        np.ones((ys.size, xs.size)), dims=("y", "x"), coords={"y": ys, "x": xs}
    )
    with pytest.raises(ValueError, match="Mercator"):
        pixel_area_ha(merc, "EPSG:3857")


def test_region_unprojectable_into_dataset_crs_is_outside():
    # A South American box cannot be projected into Finland's TM35FIN grid
    xs = np.arange(300_005.0, 301_000, 10)
    ys = np.arange(6_901_000 - 5.0, 6_900_000, -10)
    da = xr.DataArray(
        np.ones((ys.size, xs.size)), dims=("y", "x"), coords={"y": ys, "x": xs}
    )
    with pytest.raises(ValueError, match="outside"):
        region_statistics(da, box(-70, -15, -45, 3), crs="EPSG:3067")


def test_large_box_area_follows_drawn_edges_not_great_circles():
    # Edges along parallels, as drawn on the map: pixels and the polygon agree
    da = geographic_grid(res=0.25, value=1.0)
    geom = box(-70, -15, -45, 3)
    (row,) = region_statistics(da, geom, crs="EPSG:4326")
    assert row["region_area_ha"] == pytest.approx(geometry_area_ha(geom), rel=1e-3)
