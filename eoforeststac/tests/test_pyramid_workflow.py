import numpy as np
import xarray as xr

from scripts.build_pyramid import (
    automatic_levels,
    coarsen_level,
    infer_reducer,
    normalize_s3_url,
)


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
    dataset = xr.Dataset(coords={"y": range(202_500), "x": range(405_000)})
    assert automatic_levels(dataset, "y", "x", target_size=8192) == 6
    assert (
        normalize_s3_url("https://s3.gfz-potsdam.de/bucket/product.zarr")
        == "s3://bucket/product.zarr"
    )
    assert infer_reducer("loss_year", {}) == "max"
    assert infer_reducer("land_class", {}) == "first"
    assert infer_reducer("biomass", {"units": "Mg/ha"}) == "mean"
