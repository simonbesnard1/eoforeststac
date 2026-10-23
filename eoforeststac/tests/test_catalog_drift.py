from eoforeststac.catalog.drift import differences


def test_identical_documents_have_no_differences():
    doc = {
        "id": "X",
        "links": [{"rel": "self", "href": "a"}],
        "assets": {"zarr": {"gsd": 10}},
    }
    assert differences(doc, doc) == []


def test_hand_edits_and_unpublished_changes_are_reported():
    code = {"id": "X", "assets": {"zarr": {"nodata": 255}}, "links": [{"rel": "self"}]}
    live = {"id": "X", "assets": {"zarr": {"nodata": 0}}, "links": [], "extra": 1}
    found = differences(code, live)
    assert "/assets/zarr/nodata: live 0 -> code 255" in found
    assert "/extra: only live" in found
    assert any(line.startswith("/links") for line in found)
