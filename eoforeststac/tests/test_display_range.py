import numpy as np
import zarr

from eoforeststac.core.zarr import add_display_range


def _store(path, data, fill_value):
    """A Zarr v2 store, under zarr 2 (the pinned version) or zarr 3."""
    if zarr.__version__.startswith("2"):
        group = zarr.open_group(str(path), mode="w")
        arr = group.create_dataset(
            "v",
            shape=data.shape,
            chunks=(50, 50),
            dtype=data.dtype,
            fill_value=fill_value,
        )
    else:
        group = zarr.open_group(str(path), mode="w", zarr_format=2)
        arr = group.create_array(
            "v",
            shape=data.shape,
            chunks=(50, 50),
            dtype=data.dtype,
            fill_value=fill_value,
        )
    arr[:] = data
    zarr.consolidate_metadata(str(path))


def test_fill_value_is_not_part_of_the_range(tmp_path):
    # Fill and valid values share chunks: all-fill chunks are never stored
    data = np.linspace(10, 20, 10000, dtype="f4").reshape(100, 100)
    data[::2] = -9999.0
    _store(tmp_path / "s.zarr", data, fill_value=-9999.0)

    lo, hi = add_display_range(str(tmp_path / "s.zarr"))["v"]

    assert 10 <= lo < hi <= 20
    attrs = zarr.open_group(str(tmp_path / "s.zarr"), mode="r")["v"].attrs
    assert attrs["display_range"] == [lo, hi]


def test_nan_fill_value_store(tmp_path):
    data = np.linspace(0, 5, 10000, dtype="f4").reshape(100, 100)
    data[::2] = np.nan
    _store(tmp_path / "s.zarr", data, fill_value=np.nan)

    lo, hi = add_display_range(str(tmp_path / "s.zarr"))["v"]

    assert 0 <= lo < hi <= 5


def test_explicit_integer_continuous_variable(tmp_path):
    data = np.arange(10000, dtype="int32").reshape(100, 100)
    _store(tmp_path / "s.zarr", data, fill_value=-9999)

    assert add_display_range(str(tmp_path / "s.zarr")) == {}
    lo, hi = add_display_range(str(tmp_path / "s.zarr"), variables=["v"])["v"]

    assert 0 <= lo < hi <= 9999
