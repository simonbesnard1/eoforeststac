import numpy as np
import xarray as xr

import json

import fsspec
import pytest

from eoforeststac.pyramids.build import (
    add_store_display_ranges,
    build_pyramid,
    coarsen_level,
    infer_reducer,
    level_count,
    pyramid_path,
)
from eoforeststac.pyramids.maintain import plan, product_configs, remove_pyramid


def test_coarsen_level_uses_variable_specific_reducers():
    dataset = xr.Dataset(
        {
            "continuous": (
                ("y", "x"),
                np.array([[1.0, 3.0, 5.0], [5.0, 7.0, 9.0], [2.0, 4.0, 6.0]]),
            ),
            "event_year": (
                ("y", "x"),
                np.array([[0.0, 2020.0, 0.0], [2019.0, 0.0, 0.0], [0.0, 0.0, 2021.0]]),
            ),
            "classes": (
                ("y", "x"),
                np.array([[1.0, 2.0, 3.0], [2.0, 2.0, 3.0], [4.0, 4.0, 5.0]]),
            ),
        },
        coords={"y": [3.0, 2.0, 1.0], "x": [1.0, 2.0, 3.0]},
    )

    result = coarsen_level(
        dataset,
        "y",
        "x",
        {"continuous": "mean", "event_year": "max", "classes": "first"},
        "float32",
    )

    assert result.sizes == {"y": 2, "x": 2}
    np.testing.assert_allclose(result.continuous, [[4.0, 7.0], [3.0, 6.0]])
    np.testing.assert_allclose(result.event_year, [[2020.0, 0.0], [0.0, 2021.0]])
    np.testing.assert_allclose(result.classes, [[1.0, 3.0], [4.0, 5.0]])
    assert result.continuous.dtype == np.dtype("float32")


def test_first_reducer_stays_lazy_and_skips_nans():
    """`first` must not compute the dask graph while building the level."""
    import dask
    import dask.array as da

    values = np.array(
        [
            [np.nan, 2.0, 3.0, np.nan],
            [4.0, 5.0, np.nan, 6.0],
            [np.nan, np.nan, 7.0, 8.0],
        ]
    )
    dataset = xr.Dataset(
        {"classes": (("y", "x"), da.from_array(values, chunks=2))},
        coords={"y": [3.0, 2.0, 1.0], "x": [1.0, 2.0, 3.0, 4.0]},
    )

    def refuse_compute(*args, **kwargs):
        raise AssertionError("coarsen_level computed the dask graph")

    with dask.config.set(scheduler=refuse_compute):
        result = coarsen_level(dataset, "y", "x", {"classes": "first"}, "float32")
    assert isinstance(result.classes.data, da.Array)

    np.testing.assert_allclose(result.classes.values, [[2.0, 3.0], [np.nan, 7.0]])
    np.testing.assert_allclose(result.y, [2.5, 1.0])
    np.testing.assert_allclose(result.x, [1.5, 3.5])


def test_pyramid_helpers():
    assert level_count(202_500, 405_000, target_size=8192) == 6
    assert pyramid_path("b/c/X_v1.0.zarr") == "b/c/X_v1.0_pyramid.zarr"
    assert infer_reducer("loss_year", {}) == "max"
    assert infer_reducer("land_class", {}) == "first"
    assert infer_reducer("biomass", {"units": "Mg/ha"}) == "mean"


# ── Finding stores and building on an in-memory filesystem ────────────────

PREFIX = "bucket/collections"


@pytest.fixture
def fs():
    memory = fsspec.filesystem("memory")
    memory.store.clear()
    memory.pseudo_dirs.clear()
    yield memory
    memory.store.clear()


def _metadata(fs, path, height, width):
    """Consolidated metadata of a store with one (time, y, x) variable."""
    fs.pipe(
        f"{path}/.zmetadata",
        json.dumps(
            {
                "metadata": {
                    "v/.zarray": {"shape": [1, height, width]},
                    "v/.zattrs": {"_ARRAY_DIMENSIONS": ["time", "y", "x"]},
                }
            }
        ).encode(),
    )


def _pyramid(fs, path, levels, done):
    datasets = [{"path": str(i)} for i in range(1, levels + 1)]
    fs.pipe(
        f"{path}/.zattrs",
        json.dumps({"multiscales": [{"datasets": datasets}]}).encode(),
    )
    for i in range(1, done + 1):
        fs.pipe(f"{path}/{i}/_SUCCESS", b"")


def test_plan_builds_missing_finishes_partial_and_lists_unused(fs):
    big, small = (20_000, 10_000), (500, 500)
    _metadata(fs, f"{PREFIX}/A/A_v1.0.zarr", *big)  # older version
    _metadata(fs, f"{PREFIX}/A/A_v2.0.zarr", *big)  # newest, no pyramid
    _pyramid(fs, f"{PREFIX}/A/A_v1.0_pyramid.zarr", 2, 2)  # unused now
    _metadata(fs, f"{PREFIX}/B/B_10m_v1.0.zarr", *big)  # partly built
    _pyramid(fs, f"{PREFIX}/B/B_10m_v1.0_pyramid.zarr", 3, 1)
    _metadata(fs, f"{PREFIX}/B/B_100m_v1.0.zarr", *small)  # needs none
    _metadata(fs, f"{PREFIX}/C/C_v1.0.zarr", *big)  # complete
    _pyramid(fs, f"{PREFIX}/C/C_v1.0_pyramid.zarr", 2, 2)
    fs.pipe(f"{PREFIX}/D/D_v1.0.zarr/.zgroup", b"{}")  # still being written
    _pyramid(fs, f"{PREFIX}/E/E_v1.0_pyramid.zarr", 1, 1)  # data gone

    kinds = {t.label: (t.kind, t.reason) for t in plan(fs, PREFIX)}

    assert kinds["A_v2.0"][0] == "build"
    assert kinds["B_10m_v1.0"] == ("finish", "1/3 levels done")
    assert kinds["B_100m_v1.0"][0] == "small"
    assert kinds["C_v1.0"][0] == "ok"
    assert kinds["D_v1.0.zarr"][0] == "unfinished-data"
    assert kinds["A_v1.0_pyramid.zarr"] == (
        "delete",
        "older version; the explorer shows the newest",
    )
    assert kinds["E_v1.0_pyramid.zarr"] == ("delete", "its data store is gone")
    rebuilt = {t.label: t.kind for t in plan(fs, PREFIX, rebuild={"C"})}
    assert rebuilt["C_v1.0"] == "rebuild"


def test_remove_pyramid_refuses_anything_else(fs):
    for path in (f"{PREFIX}/A/A_v1.0.zarr", "elsewhere/A_v1.0_pyramid.zarr"):
        with pytest.raises(RuntimeError):
            remove_pyramid(fs, path, PREFIX)


def test_build_pyramid_end_to_end_and_resume(fs):
    path = f"{PREFIX}/T/T_v1.0.zarr"
    values = np.arange(64, dtype="float32").reshape(1, 8, 8)
    ds = xr.Dataset(
        {"v": (("time", "y", "x"), values)},
        coords={"time": [0], "y": np.arange(8.0)[::-1], "x": np.arange(8.0)},
    )
    try:
        ds.to_zarr(fs.get_mapper(path), consolidated=True, zarr_format=2)
    except TypeError:
        ds.to_zarr(fs.get_mapper(path), consolidated=True)

    out = build_pyramid(fs, path, {"v": "mean"}, target_size=2, log=lambda m: None)

    assert out == pyramid_path(path)
    assert [t.kind for t in plan(fs, PREFIX, target_size=2)] == ["ok"]
    level1 = xr.open_zarr(fs.get_mapper(f"{out}/1"), consolidated=True)
    np.testing.assert_allclose(level1.v.values[0, 0, 0], np.mean([0, 1, 8, 9]))
    assert xr.open_zarr(fs.get_mapper(f"{out}/2"), consolidated=True).sizes["x"] == 2

    ranges = add_store_display_ranges(fs, path, {"v": "mean"}, log=lambda m: None)
    assert "v" in ranges
    for target in (path, f"{out}/1", f"{out}/2"):
        attrs = xr.open_zarr(fs.get_mapper(target), consolidated=True).v.attrs
        assert attrs["display_range"] == ranges["v"]
        assert "pyramid level 2" in attrs["display_range_method"]

    # An interrupted run: level 2 lost its marker; only it is rebuilt
    fs.rm(f"{out}/2/_SUCCESS")
    messages = []
    build_pyramid(fs, path, {"v": "mean"}, target_size=2, log=messages.append)
    assert any("level 1: already complete" in m for m in messages)
    assert any("level 2: replacing an unfinished level" in m for m in messages)


def test_every_configured_reducer_is_valid():
    for cid, config in product_configs().items():
        for var, reducer in config.get("pyramid", {}).get("reducers", {}).items():
            assert reducer in {"mean", "max", "first"}, (cid, var, reducer)


def test_dropped_chunk_writes_are_retried():
    from eoforeststac.pyramids.build import RetryingStore

    class Flaky(dict):
        """Drops the first two writes of every key, as a busy Ceph might (499)."""

        def __init__(self):
            super().__init__()
            self.failures = {}

        def __setitem__(self, key, value):
            n = self.failures.get(key, 0)
            if n < 2:
                self.failures[key] = n + 1
                raise OSError(
                    "An error occurred (499) when calling the PutObject operation"
                )
            super().__setitem__(key, value)

    store = RetryingStore(Flaky(), attempts=4, pause=0)
    store["0.0"] = b"chunk"
    assert store["0.0"] == b"chunk" and "0.0" in store and len(store) == 1

    hopeless = RetryingStore(Flaky(), attempts=2, pause=0)
    with pytest.raises(OSError):
        hopeless["0.0"] = b"chunk"
