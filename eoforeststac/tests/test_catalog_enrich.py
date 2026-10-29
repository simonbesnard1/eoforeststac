import io
import json
import urllib.error
from unittest.mock import patch

from eoforeststac.catalog.enrich import pyramid_levels


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def test_pyramid_levels_counts_only_contiguous_success_markers():
    attrs = {"multiscales": [{"datasets": [{"path": "1"}, {"path": "2"}, {"path": "3"}]}]}

    def open_url(request, **_):
        url = request if isinstance(request, str) else request.full_url
        if url.endswith("/.zattrs"):
            return _Response(json.dumps(attrs).encode())
        if url.endswith("/1/_SUCCESS") or url.endswith("/2/_SUCCESS"):
            return _Response()
        raise urllib.error.HTTPError(url, 404, "missing", {}, None)

    pyramid_levels.cache_clear()
    with patch("urllib.request.urlopen", side_effect=open_url):
        assert pyramid_levels("https://example.test/X_v1.zarr") == 2
