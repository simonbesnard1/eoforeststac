/* EOForestSTAC explorer: Rail and panel wiring, and start-up.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   PANEL / RAIL WIRING
══════════════════════════════════════════════════════════════════ */
const VIEW_TITLES = { data: 'Datasets', layers: 'Active layers', basemap: 'Basemap & view', download: 'Download data', settings: 'Settings' };

/* Clicking the rail button you're already on collapses the panel;
   openView() is the non-toggling form used when code needs a view shown.
   The 'data' view is shown per category (`cat`, a STAC theme id). */
function showView(view, cat) {
  const same = S.view === view && (view !== 'data' || !cat || cat === S.cat);
  if (same && S.panelOpen) { setPanelOpen(false); return; }
  openView(view, cat);
}

function openView(view, cat) {
  S.view = view;
  if (view === 'data') S.cat = cat || S.cat || firstThemeId();
  setPanelOpen(true);
  syncRail();
  document.querySelectorAll('.pnl-view').forEach(v => v.classList.toggle('active', v.id === `view-${view}`));
  if (view === 'data') applyCatalogFilter();
  else syncPanelHead();
  if (view === 'download') refreshDownload();
}

function syncPanelHead(hits = 0) {
  let title = VIEW_TITLES[S.view], sub = '';
  if (S.view === 'data') {
    const theme = S.catalog?.themes.find(t => t.id === S.cat);
    if (el('ds-search').value.trim()) {
      title = 'Search results';
      sub = `${hits} found`;
    } else {
      title = themeInfo(theme || { id: S.cat }).label;
      sub = theme ? `${theme.collections.length} datasets` : '';
    }
  } else if (S.view === 'layers') {
    sub = `${S.layers.size + S.fp.size} active`;
  }
  el('pnl-title').textContent = title;
  el('pnl-sub').textContent = sub;
}

function setPanelOpen(open) {
  S.panelOpen = open;
  el('panel').classList.toggle('closed', !open);
  setTimeout(() => S.map?.invalidateSize({ pan: false }), 240);
}

function renderBasemapGrid() {
  el('bm-grid').innerHTML = Object.entries(BASEMAPS).map(([id, bm]) => `
    <button class="bm-opt ${id === S.basemapId ? 'on' : ''}" data-bm="${id}">
      <div class="bm-thumb" style="background:${bm.thumb}"></div>
      <div class="bm-cap">${esc(bm.name)}</div>
    </button>`).join('');
  el('bm-grid').querySelectorAll('.bm-opt').forEach(b => {
    b.addEventListener('click', () => setBasemap(b.dataset.bm));
  });
}

function initUI() {
  applyTheme(localStorage.getItem('theme') || 'light');
  el('cat-url').textContent = CFG.catalog;
  el('titiler-url').value = S.tiTiler;
  el('labels-sw').checked = S.showLabels;
  el('autozoom-sw').checked = S.autoZoom;
  renderBasemapGrid();
  renderRailCats();
  initDownload();

  document.querySelectorAll('.rail-btn[data-view]:not([data-cat])').forEach(b => {
    b.addEventListener('click', () => showView(b.dataset.view));
  });
  openView('data');

  el('nav-about').addEventListener('click', e => { e.preventDefault(); openAbout(); });
  document.addEventListener('click', e => {
    if (e.target.closest('[data-about]')) { e.preventDefault(); openAbout(); }
  });
  const dlg = el('ds-info-dlg');
  el('dlg-close').addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
  el('pnl-close').addEventListener('click', () => setPanelOpen(false));

  el('theme-btn').addEventListener('click', () => {
    applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  el('ds-search').addEventListener('input', applyCatalogFilter);

  el('labels-sw').addEventListener('change', e => setLabels(e.target.checked));
  el('autozoom-sw').addEventListener('change', e => {
    S.autoZoom = e.target.checked;
    localStorage.setItem('autozoom', S.autoZoom ? '1' : '0');
  });

  el('connect-btn').addEventListener('click', async () => {
    const url = el('titiler-url').value.trim().replace(/\/+$/, '');
    if (!url) return;
    S.tiTiler = url;
    localStorage.setItem('tiTilerUrl', url);
    await checkTiTiler();
    if (!S.catalog) await loadCatalog();
    S.layers.forEach((_, id) => updateLeafletLayer(id));
  });

  el('t-in').addEventListener('click', () => S.map.zoomIn());
  el('t-out').addEventListener('click', () => S.map.zoomOut());
  el('t-fit').addEventListener('click', zoomToAllLayers);
  el('t-home').addEventListener('click', () => S.map.flyTo(CFG.home.center, CFG.home.zoom, { duration: 0.8 }));
  el('t-share').addEventListener('click', e => copyShareLink(e.currentTarget));
  el('t-full').addEventListener('click', () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen?.();
  });

  el('ins-close').addEventListener('click', () => el('inspector').hidden = true);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') el('inspector').hidden = true;
    if (e.key === '/' && document.activeElement !== el('ds-search')) {
      e.preventDefault(); openView('data'); el('ds-search').focus();
    }
  });
}

/* ══════════════════════════════════════════════════════════════════
   BOOT
══════════════════════════════════════════════════════════════════ */
(async function main() {
  initUI();
  initMap();
  initCompare();
  await checkTiTiler();
  await Promise.all([loadColormapNames(), loadCatalog()]);
  syncLayerCount();
  await restoreFromUrl();
  // Settings change through many controls; checking the state once a second
  // keeps the address bar shareable without wiring every one of them
  setInterval(syncShareUrl, 1000);
})();

/* Who made the explorer and what it builds on: from the header's About link
   and the credit line on the map. */
function openAbout() {
  el('dlg-eyebrow').textContent = 'About';
  el('dlg-title').textContent = 'EOForestSTAC explorer';
  el('dlg-body').innerHTML = `
    <p>An interactive map of the forest Earth observation datasets in the
      EOForestSTAC catalog, developed at the
      <a href="https://www.gfz.de" target="_blank" rel="noopener noreferrer">GFZ Helmholtz Centre for Geosciences</a>
      by Simon Besnard.</p>
    <dl class="dlg-facts">
      <dt>Code</dt>
      <dd>Written with <a href="https://claude.com/claude-code" target="_blank" rel="noopener noreferrer">Claude Code</a>
        (Anthropic), directed and reviewed by the author.</dd>
      <dt>Design</dt>
      <dd>Interface inspired by <a href="https://www.globalforestwatch.org" target="_blank" rel="noopener noreferrer">Global Forest Watch</a>.</dd>
      <dt>Data</dt>
      <dd>Each dataset belongs to its producers; its info button lists the source, licence and how to cite it.</dd>
      <dt>Source</dt>
      <dd><a href="https://github.com/simonbesnard1/eoforeststac" target="_blank" rel="noopener noreferrer">github.com/simonbesnard1/eoforeststac</a>
        (EUPL 1.2)</dd>
    </dl>`;
  el('dlg-body').scrollTop = 0;
  el('ds-info-dlg').showModal();
}
