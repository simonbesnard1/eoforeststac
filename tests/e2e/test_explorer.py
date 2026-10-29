"""What a user does in the explorer, checked by what is rendered."""

import re

from conftest import wait_for_tiles

GAMI = "GAMI_AGECLASS"


def tile_responses(pg):
    responses = []
    pg.on("response", lambda r: "/tiles/" in r.url and responses.append(r))
    return responses


def test_catalog_lists_the_categories(page):
    labels = page.locator("#rail-cats .rail-label").all_inner_texts()
    for expected in ("Biomass", "Disturbance", "Structure", "Land use"):
        assert expected in labels, labels
    page.locator('#rail-cats .rail-btn[data-cat="biomass-carbon"]').click()
    rows = page.locator('.grp[data-grp="biomass-carbon"] .ds-name').all_inner_texts()
    assert len(rows) >= 3, rows


def test_a_layer_draws_tiles_and_a_legend(page):
    tiles = tile_responses(page)
    page.evaluate("() => S.map.setView([0, 20], 3, {animate: false})")
    page.evaluate(f"() => toggleDataset('{GAMI}', true)")
    wait_for_tiles(page, GAMI)
    assert tiles and all(r.status == 200 for r in tiles), [r.status for r in tiles]
    legend = page.locator("#leg-items").inner_text()
    assert "Forest age-class fraction" in legend
    ticks = [float(t) for t in page.locator(".leg-ticks span").all_inner_texts()]
    assert ticks[0] >= 0 and ticks[-1] <= 1, ticks  # never a fill value like -9999
    options = page.evaluate(f"() => S.layers.get('{GAMI}').leafletLayer.options")
    assert options["updateWhenIdle"] is True
    assert options["updateWhenZooming"] is False
    assert options["keepBuffer"] == 1


def test_pyramid_level_matches_display_resolution(page):
    """Global 100 m products use overviews until the map can show native detail."""
    levels = page.evaluate(
        """() => {
          const layer = {
            pyramidUrl: 'test', numPyramidLevels: 7, nativeMinZoom: 7,
            bounds: [-180, -60, 180, 80], width: 415158, height: 161272,
          };
          return Object.fromEntries([2, 5, 7, 11].map(z => [z, getPyramidLevel(layer, z)]));
        }"""
    )
    assert levels == {"2": 6, "5": 5, "7": 3, "11": 0}


def test_resolution_and_member_pickers(page):
    page.evaluate("() => S.map.setView([0, 20], 3, {animate: false})")
    page.evaluate(f"() => toggleDataset('{GAMI}', true)")
    wait_for_tiles(page, GAMI)
    card = page.locator(f'.lc[data-card="{GAMI}"]')
    res = card.locator('select[data-prop="resolution"]')
    options = res.locator("option").all_inner_texts()
    assert options[0].endswith("finest") and "1°" in options[-1], options

    members = (
        card.locator('select[data-prop^="extra:"]')
        .first.locator("option")
        .all_inner_texts()
    )
    assert members == sorted(members, key=float), members

    tiles = tile_responses(page)
    res.select_option(index=len(options) - 1)
    page.wait_for_function(
        f"() => S.layers.get('{GAMI}')?.zarrIndex === {len(options) - 1}"
    )
    wait_for_tiles(page, GAMI)
    assert tiles and all("_1deg_" in r.url for r in tiles)
    assert "1°" in page.locator(".leg-ds").first.inner_text()


def test_analysis_of_a_drawn_area(page):
    page.evaluate(f"() => toggleDataset('{GAMI}', true)")
    page.wait_for_function(
        f"() => S.layers.get('{GAMI}')?.leafletLayer", timeout=120_000
    )
    page.evaluate(
        """() => { S.legTab = 'analysis'; renderLegend();
                   setArea({type: 'Polygon', coordinates: [[[20, -5], [24, -5], [24, -1], [20, -1], [20, -5]]]}); }"""
    )
    page.locator("#an-go").click()
    page.wait_for_function(
        "() => !S.an.running && (S.an.result || S.an.error)", timeout=300_000
    )
    assert page.evaluate("() => S.an.error") is None
    assert page.locator("#an-results .an-card").count() >= 1


def test_both_themes_render(page):
    for theme, accent in (("light", "#002864"), ("dark", "#43d3ff")):
        page.evaluate("t => applyTheme(t)", theme)
        value = page.evaluate(
            "() => getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()"
        )
        assert value == accent, (theme, value)


def test_time_labels_are_readable(page):
    page.evaluate(f"() => toggleDataset('{GAMI}', true)")
    page.wait_for_function(
        f"() => S.layers.get('{GAMI}')?.leafletLayer", timeout=120_000
    )
    text = (
        page.locator(f'.lc[data-card="{GAMI}"]').inner_text()
        + page.locator("#leg-items").inner_text()
    )
    assert not re.search(r"T00:00:00", text), "raw timestamps shown"


def test_every_panel_opens(page):
    for view in ("layers", "basemap", "download", "appearance", "settings"):
        button = page.locator(f'.rail-btn[data-view="{view}"]')
        if button.count():
            button.first.click()
            page.wait_for_timeout(200)
    assert "About" in page.locator("#view-settings").inner_text()


def test_clicking_the_map_shows_pixel_values(page):
    page.evaluate("() => S.map.setView([-1, 21], 6, {animate: false})")
    page.evaluate(f"() => toggleDataset('{GAMI}', true)")
    wait_for_tiles(page, GAMI)
    box = page.locator("#map").bounding_box()
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.wait_for_function(
        "() => !el('inspector').hidden && !/Querying/.test(el('ins-rows').innerText)",
        timeout=60_000,
    )
    assert "forest_age" in page.locator("#ins-rows").inner_text()


def test_spaceborne_lidar_groups_by_sensor(page):
    group = page.locator('.grp[data-grp="spaceborne-lidar"]')
    if not group.count():  # no footprint service in this stack (e.g. CI)
        return
    headers = group.locator(".ds-sub").all_inner_texts()
    assert any(h.startswith("GEDI") for h in headers) and any(
        h.startswith("ICESat-2") for h in headers
    ), headers


def test_a_shared_link_reopens_the_same_view(page, browser):
    from conftest import BASE_URL

    page.evaluate(f"() => toggleDataset('{GAMI}', true)")
    wait_for_tiles(page, GAMI)
    # After switching on: "zoom to layer" flies to GAMI's global extent
    page.wait_for_timeout(1500)
    page.evaluate("() => S.map.setView([-3, 22], 5, {animate: false})")
    card = page.locator(f'.lc[data-card="{GAMI}"]')
    card.locator('select[data-prop="resolution"]').select_option(index=2)
    page.wait_for_function(f"() => S.layers.get('{GAMI}')?.zarrIndex === 2")
    card = page.locator(f'.lc[data-card="{GAMI}"]')
    card.locator('select[data-prop^="extra:"]').first.select_option(index=3)
    card.locator('select[data-prop="colormap"]').select_option("magma")
    page.wait_for_function(
        "() => /c%3Amagma|c:magma/.test(location.hash) && /map=5(%2F|\\/)/.test(location.hash)",
        timeout=10_000,
    )
    url = page.url

    other = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    other.goto(url)
    other.wait_for_function(
        f"() => S.layers.get('{GAMI}')?.leafletLayer && !S.restoring", timeout=180_000
    )
    state = other.evaluate(
        f"""() => {{ const l = S.layers.get('{GAMI}'); const c = S.map.getCenter();
              return {{ res: l.zarrIndex, member: l.extraDims[0].index, cmap: l.colormap,
                        zoom: S.map.getZoom(), lat: c.lat, lng: c.lng }}; }}"""
    )
    other.context.close()
    assert (
        state["res"] == 2 and state["member"] == 3 and state["cmap"] == "magma"
    ), state
    # Within a pixel (0.044 degrees at zoom 5): opening the side panel shifts
    # the map by a fraction of one
    assert (
        state["zoom"] == 5
        and abs(state["lat"] + 3) < 0.05
        and abs(state["lng"] - 22) < 0.05
    ), state


def test_compare_two_layers_side_by_side(page):
    page.evaluate(
        "() => { S.autoZoom = false; S.map.setView([0, 20], 3, {animate: false}); }"
    )
    assert page.locator("#t-compare").is_disabled()
    for layer in (GAMI, "SAATCHI_BIOMASS"):
        page.evaluate(f"() => toggleDataset('{layer}', true)")
        wait_for_tiles(page, layer)
    page.locator("#t-compare").click()
    assert page.locator("#compare-handle").is_visible()
    tags = page.locator(".cmp-tag").all_inner_texts()
    assert any("GAMI" in t for t in tags) and any(
        "Saatchi" in t or "SAATCHI" in t for t in tags
    ), tags
    clips = page.evaluate(
        f"""() => [S.layers.get('{GAMI}'), S.layers.get('SAATCHI_BIOMASS')]
        .map(l => l.leafletLayer.getContainer().style.clip)"""
    )
    assert all(c.startswith("rect(") for c in clips), clips

    # Drag the divider to the left: the left layer's clip narrows
    handle = page.locator("#compare-handle").bounding_box()
    before = page.evaluate("() => CMP.x")
    page.mouse.move(
        handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2
    )
    page.mouse.down()
    page.mouse.move(handle["x"] - 200, handle["y"] + handle["height"] / 2, steps=5)
    page.mouse.up()
    assert page.evaluate("() => CMP.x") < before

    page.evaluate("() => toggleDataset('SAATCHI_BIOMASS', false)")
    assert not page.locator(
        "#compare-handle"
    ).is_visible()  # one layer left: comparison ends
    assert (
        page.evaluate(
            f"() => S.layers.get('{GAMI}').leafletLayer.getContainer().style.clip"
        )
        == ""
    )


def test_credits_are_visible(page):
    credit = page.locator(".leaflet-control-attribution").inner_text()
    assert "Claude Code" in credit and "Global Forest Watch" in credit, credit
    page.locator("#nav-about").click()
    dialog = page.locator("#ds-info-dlg")
    assert dialog.is_visible()
    text = dialog.inner_text()
    for expected in ("GFZ", "Simon Besnard", "Claude Code", "Global Forest Watch"):
        assert expected in text, expected
