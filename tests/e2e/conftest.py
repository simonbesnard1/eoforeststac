"""Browser tests of the explorer, against a running stack.

    BASE_URL=http://127.0.0.1:8080 pytest tests/e2e      # local or CI stack
    BASE_URL=https://eoforeststac.gfz.de pytest tests/e2e  # the live site

They need Playwright with Chromium (pip install playwright pytest &&
playwright install chromium) and a stack that can read the public S3 data.
BROWSER_CHANNEL=chrome uses an installed Google Chrome instead.
"""

import os

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8080").rstrip("/")
CHANNEL = os.environ.get("BROWSER_CHANNEL") or None


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, channel=CHANNEL)
        yield b
        b.close()


@pytest.fixture
def page(browser):
    """The explorer with its catalog loaded; fails the test on any page error."""
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = context.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE_URL + "/")
    pg.wait_for_function(
        "() => typeof S !== 'undefined' && S.catalog && S.catalog.themes.length",
        timeout=120_000,
    )
    pg.errors = errors
    yield pg
    context.close()
    assert not errors, f"page errors: {errors}"


def wait_for_tiles(pg, layer_id, timeout=180_000):
    pg.wait_for_function(
        "id => { const l = S.layers.get(id)?.leafletLayer; return l && !l.isLoading(); }",
        arg=layer_id,
        timeout=timeout,
    )
