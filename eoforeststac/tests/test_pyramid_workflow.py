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
