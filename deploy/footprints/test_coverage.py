"""The coverage grid from a fake fragment index (the real one needs listing rights)."""

import numpy as np

from coverage import coverage_document, grid_counts


def test_counts_land_in_the_right_cells():
    boxes = [
        (10.2, 10.8, 20.1, 20.9, 100),  # inside the cell 10-11 N, 20-21 E
        (-0.5, 0.5, -0.5, 0.5, 400),  # straddles four cells equally
        (51.3, 51.3, 30.4, 30.4, 7),  # one footprint (point box)
    ]
    counts = grid_counts(boxes, cell=1.0)
    assert counts.shape == (180, 360)
    assert counts[90 - 11, 180 + 20] == 100  # row 0 is 90 N, column 0 is 180 W
    for r, c in ((89, 179), (89, 180), (90, 179), (90, 180)):
        assert np.isclose(counts[r, c], 100)
    assert counts[90 - 52, 180 + 30] == 7
    assert np.isclose(counts.sum(), 507)


def test_document_is_compact_and_complete():
    doc = coverage_document(
        "gedi", grid_counts([(0.1, 0.9, 0.1, 0.9, 12)], cell=1.0), min_count=0
    )
    assert doc["total"] == 12 and doc["rows"] == 180 and doc["cols"] == 360
    assert doc["counts"][89][180] == 12


def test_sparse_cells_are_dropped():
    counts = grid_counts(
        [(0.1, 0.9, 0.1, 0.9, 50_000), (40.1, 40.9, 0.1, 0.9, 30)], cell=1.0
    )
    doc = coverage_document("gedi", counts)
    assert doc["counts"][89][180] == 50_000 and doc["counts"][49][180] == 0
