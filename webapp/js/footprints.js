/* EOForestSTAC explorer: Spaceborne LiDAR footprints (GEDI, ICESat-2) from the footprint service.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   SPACEBORNE LIDAR FOOTPRINTS — GEDI and ICESat-2 shots from gediDB and
   icesat2DB, served by the footprint service (/api/footprints/). They are
   not in the STAC catalog: the service lists the sources, which appear as a
   "Spaceborne LiDAR" category like the catalog's themes.
══════════════════════════════════════════════════════════════════ */
const FP = { minZoom: 11, maxTiles: 24, concurrency: 4, tileDeg: 0.2, bins: 32 };
/* Points use the ramp from 20 % on: the palest steps vanish on light basemaps. */
const fpColor = (layer, t) => colorAt(layer.colormap, 0.2 + 0.8 * t);
const fpGradient = layer => `linear-gradient(90deg, ${Array.from({ length: 11 }, (_, i) => fpColor(layer, i / 10)).join(', ')})`;
const FP_THEME = 'spaceborne-lidar';
const FP_SENSORS = {
  gedi: { id: 'gedi', title: 'GEDI · 25 m footprints · 52° S–52° N · 2019–present' },
  icesat2: { id: 'icesat2', title: 'ICESat-2 · 100 m segments · global · 2018–present' },
};
S.fp = new Map();          // id -> footprint layer
S.fpSources = null;        // service metadata
let _fpQueue = [], _fpActive = 0, _fpCanvas = null, _fpRedrawTimer = null;

async function loadFootprintSources() {
  try {
    const meta = await fetchJSON(`${S.tiTiler}/footprints/sources`);
    S.fpSources = meta;
    FP.tileDeg = meta.tile_deg || FP.tileDeg;
    return {
      id: FP_THEME,
      title: 'Spaceborne LiDAR',
      // Grouped by sensor (a sub-header each, like the ALS countries); rows
      // are named by what they measure, the product code goes in the facts
      collections: meta.sources.map(src => ({
        id: src.id, title: src.title, footprint: true, fp: src,
        parent: FP_SENSORS[src.provider] || { id: src.provider, title: src.provider },
        siteLabel: src.quantity,
        version: '', variables: [src.quantity], zarrs: [], bbox: null,
        summaries: { variables: [src.quantity], units_by_variable: { [src.quantity]: src.units } },
        description: `${src.description}\n\nFootprints are samples along the satellite tracks, not a map: zoom in (level ${FP.minZoom}+) to load them, or draw an area in the Analysis tab for per-year statistics.`,
        license: 'Open data (NASA)',
        providers: [{ name: src.provider === 'gedi' ? 'NASA GEDI · gediDB (GFZ)' : 'NASA ICESat-2 · icesat2DB (GFZ)' }],
        keywords: ['lidar', 'footprints', src.provider === 'gedi' ? 'GEDI' : 'ICESat-2', src.quantity],
        links: [{ rel: 'about', href: src.docs, title: 'Database documentation' }],
        rowFacts: [(src.title.match(/\b(L\d[AB]|ATL\d+)\b/) || [])[1], src.units, 'quality-filtered']
          .filter(Boolean).join(' · '),
        facts: { time: src.provider === 'gedi' ? '2019–present' : '2018–present',
                 gsd: src.provider === 'gedi' ? '25 m footprints' : '100 m segments',
                 region: src.provider === 'gedi' ? '52° S–52° N' : 'global',
                 provider: src.provider === 'gedi' ? 'NASA GEDI' : 'NASA ICESat-2' },
      })),
    };
  } catch { return null; }   // no footprint service: the category is simply absent
}

function fpTileKey(i, j) { return `${i}:${j}`; }

/* Tiles of the fixed 0.2° grid that the current view touches. */
function fpTilesInView() {
  const b = S.map.getBounds(), d = FP.tileDeg;
  const w = Math.max(-180, b.getWest()), e = Math.min(180, b.getEast());
  const s = Math.max(-90, b.getSouth()), n = Math.min(90, b.getNorth());
  const out = [];
  for (let i = Math.floor((w + 180) / d); i <= Math.floor((e + 180 - 1e-9) / d); i++)
    for (let j = Math.floor((s + 90) / d); j <= Math.floor((n + 90 - 1e-9) / d); j++)
      out.push([i, j]);
  return out;
}

/* Footprint counts per 1° cell (deploy/footprints/coverage.py), shown below
   the zoom where footprints load so users see where to zoom in. Absent until
   that grid has been built; then this is simply skipped. */
const FP_COVERAGE_URL = p => CFG.catalog.replace(/catalog\.json$/, `footprints/coverage_${p}.json`);
const _fpCoverage = new Map();   // provider -> grid | null (missing) | Promise
function fpCoverage(provider) {
  if (!_fpCoverage.has(provider)) {
    _fpCoverage.set(provider, fetchJSON(FP_COVERAGE_URL(provider))
      .then(g => { _fpCoverage.set(provider, g?.counts ? g : null); fpRedraw(); })
      .catch(() => _fpCoverage.set(provider, null)));
  }
  const v = _fpCoverage.get(provider);
  return v instanceof Promise ? null : v;
}

function fpStatus(layer) {
  if (S.map.getZoom() < FP.minZoom) {
    const cov = fpCoverage(layer.src.provider);
    return { kind: 'zoom', coverage: !!cov, text: cov
      ? `Footprints per 1° cell; zoom in to level ${FP.minZoom}+ to see them`
      : `Zoom in to level ${FP.minZoom}+ to load footprints` };
  }
  const tiles = fpTilesInView();
  if (tiles.length > FP.maxTiles) return { kind: 'zoom', text: 'Zoom in a little further to load footprints' };
  let loading = 0, count = 0, shown = 0, errors = 0;
  for (const [i, j] of tiles) {
    const t = layer.tiles.get(fpTileKey(i, j));
    if (!t || t.state === 'loading') loading++;
    else if (t.state === 'error') errors++;
    else { count += t.data.count; shown += t.data.shown; }
  }
  const parts = [`${count.toLocaleString('en')} footprints in view`];
  if (shown < count) parts.push(`${shown.toLocaleString('en')} drawn`);
  if (loading) parts.push(`loading ${loading} tile${loading > 1 ? 's' : ''}…`);
  if (errors) parts.push(`${errors} tile${errors > 1 ? 's' : ''} failed`);
  return { kind: loading ? 'loading' : 'ok', text: parts.join(' · ') };
}

async function toggleFootprints(col, on) {
  if (!on) {
    S.fp.delete(col.id);
    fpRedraw();
    return;
  }
  const slot = freeColorSlot();
  S.fp.set(col.id, {
    id: col.id, title: col.title, col, src: col.fp, slot, color: LAYER_COLORS[slot],
    colormap: col.fp.colormap, tiles: new Map(), rMin: 0, rMax: 1, rangeSource: 'manual',
  });
  await loadLUT(col.fp.colormap);
  if (!_fpCanvas) { _fpCanvas = new FootprintCanvas().addTo(S.map); S.map.on('moveend', fpRefresh); }
  fpRefresh();
}

/* Queue the tiles in view for every footprint layer; tiles already loaded
   or loading are kept. Views far out of zoom only update the status. */
function fpRefresh() {
  if (!S.fp.size) return;
  _fpQueue = [];
  if (S.map.getZoom() >= FP.minZoom) {
    const tiles = fpTilesInView();
    if (tiles.length <= FP.maxTiles)
      for (const layer of S.fp.values())
        for (const [i, j] of tiles)
          if (!layer.tiles.has(fpTileKey(i, j))) _fpQueue.push({ layer, i, j });
  }
  fpPump();
  fpRedraw();
}

function fpPump() {
  while (_fpActive < FP.concurrency && _fpQueue.length) {
    const { layer, i, j } = _fpQueue.shift();
    const key = fpTileKey(i, j);
    if (layer.tiles.has(key) || !S.fp.has(layer.id)) continue;
    layer.tiles.set(key, { state: 'loading' });
    _fpActive++;
    fpLoadTile(layer, i, j)
      .then(data => { layer.tiles.set(key, { state: 'done', data }); fpUpdateRange(layer); })
      .catch(() => layer.tiles.set(key, { state: 'error' }))
      .finally(() => { _fpActive--; fpPump(); fpRedraw(); });
  }
}

async function fpPoll(start) {
  let st = start;
  while (st.status === 'running') {
    await new Promise(r => setTimeout(r, 1500));
    st = await fetchJSON(`${S.tiTiler}/footprints/jobs/${st.id}`, { noStore: true });
  }
  if (st.status !== 'done') throw new Error(st.message || 'Footprint query failed');
  return st.result;
}

async function fpLoadTile(layer, i, j) {
  return fpPoll(await postJSON('/footprints/tile', { source: layer.id, i, j }));
}

/* Colour range from the loaded footprints (p2–p98), as for measured rasters. */
function fpUpdateRange(layer) {
  if (layer.rangeSource === 'manual-set') return;
  const vals = [];
  for (const t of layer.tiles.values()) if (t.state === 'done') {
    const v = t.data.v, step = Math.max(1, Math.floor(v.length / 4000));
    for (let k = 0; k < v.length; k += step) vals.push(v[k]);
  }
  if (vals.length < 20) return;
  vals.sort((a, b) => a - b);
  const q = p => vals[Math.min(vals.length - 1, Math.floor(p * vals.length))];
  const lo = q(0.02), hi = q(0.98);
  if (hi > lo) { layer.rMin = roundRangeEnd(lo, hi - lo); layer.rMax = roundRangeEnd(hi, hi - lo); layer.rangeSource = 'footprints'; }
}

function fpRedraw() {
  clearTimeout(_fpRedrawTimer);
  _fpRedrawTimer = setTimeout(() => {
    _fpCanvas?.draw();
    renderLegend();
    renderFootprintCards();
    syncLayerCount();
  }, 60);
}

/* One canvas over the map for all footprint layers. Points are binned by
   colour so the canvas switches fill style a few dozen times, not per point. */
const FootprintCanvas = L.Layer.extend({
  onAdd(map) {
    this._map = map;
    this._c = L.DomUtil.create('canvas', 'fp-canvas');
    map.getPanes().overlayPane.appendChild(this._c);
    map.on('moveend zoomend resize', this._reset, this);
    this._reset();
  },
  onRemove(map) {
    map.off('moveend zoomend resize', this._reset, this);
    this._c.remove();
  },
  _reset() {
    const size = this._map.getSize(), dpr = window.devicePixelRatio || 1;
    L.DomUtil.setPosition(this._c, this._map.containerPointToLayerPoint([0, 0]));
    this._c.width = size.x * dpr; this._c.height = size.y * dpr;
    this._c.style.width = `${size.x}px`; this._c.style.height = `${size.y}px`;
    this.draw();
  },
  draw() {
    const ctx = this._c.getContext('2d'), dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, this._c.width, this._c.height);
    const z = this._map.getZoom();
    if (z < FP.minZoom) { this.drawCoverage(ctx); return; }
    const r = z >= 15 ? 3 : z >= 13 ? 2 : 1.5;
    const size = this._map.getSize();
    for (const layer of S.fp.values()) {
      const span = layer.rMax - layer.rMin || 1;
      const fills = Array.from({ length: FP.bins }, (_, b) => fpColor(layer, (b + 0.5) / FP.bins));
      const buckets = Array.from({ length: FP.bins }, () => []);
      for (const t of layer.tiles.values()) {
        if (t.state !== 'done') continue;
        const { lon, lat, v } = t.data;
        for (let k = 0; k < v.length; k++) {
          const p = this._map.latLngToContainerPoint([lat[k], lon[k]]);
          if (p.x < -4 || p.y < -4 || p.x > size.x + 4 || p.y > size.y + 4) continue;
          const b = Math.max(0, Math.min(FP.bins - 1, Math.floor((v[k] - layer.rMin) / span * FP.bins)));
          buckets[b].push(p.x, p.y);
        }
      }
      ctx.globalAlpha = 0.9;
      buckets.forEach((pts, b) => {
        if (!pts.length) return;
        ctx.fillStyle = fills[b];
        for (let k = 0; k < pts.length; k += 2) ctx.fillRect(pts[k] - r, pts[k + 1] - r, 2 * r, 2 * r);
      });
    }
  },
});

/* Coverage grid: one cell per 1°, coloured by log(count) in the layer's ramp;
   each provider once, in its first layer's colours. */
FootprintCanvas.prototype.drawCoverage = function (ctx) {
  const seen = new Set();
  for (const layer of S.fp.values()) {
    const provider = layer.src.provider;
    if (seen.has(provider)) continue;
    seen.add(provider);
    const g = fpCoverage(provider);
    if (!g) continue;
    const max = Math.log10(1 + Math.max(...g.counts.flat()));
    const [lat0, lon0] = g.origin, d = g.cell_deg;
    ctx.globalAlpha = 0.75;
    g.counts.forEach((row, r) => row.forEach((n, c) => {
      if (!n) return;
      const nw = this._map.latLngToContainerPoint([lat0 - r * d, lon0 + c * d]);
      const se = this._map.latLngToContainerPoint([lat0 - (r + 1) * d, lon0 + (c + 1) * d]);
      ctx.fillStyle = fpColor(layer, Math.log10(1 + n) / (max || 1));
      ctx.fillRect(nw.x, nw.y, Math.max(1, se.x - nw.x), Math.max(1, se.y - nw.y));
    }));
  }
};

/* Nearest drawn footprint within a few pixels of a map click. */
function fpPick(latlng) {
  const at = S.map.latLngToContainerPoint(latlng);
  let best = null;
  for (const layer of S.fp.values())
    for (const t of layer.tiles.values()) {
      if (t.state !== 'done') continue;
      const { lon, lat, v, year } = t.data;
      for (let k = 0; k < v.length; k++) {
        const p = S.map.latLngToContainerPoint([lat[k], lon[k]]);
        const d = Math.hypot(p.x - at.x, p.y - at.y);
        if (d < 7 && (!best || d < best.d)) best = { d, layer, value: v[k], year: year[k], lat: lat[k], lon: lon[k] };
      }
    }
  return best;
}

function renderFootprintCards() {
  const host = el('fp-cards');
  if (!host) return;
  host.innerHTML = [...S.fp.values()].map(layer => {
    const st = fpStatus(layer);
    const filters = Object.entries(layer.src.filters || {}).map(([k, v]) => `${k} ${v}`).join(', ');
    return `<div class="lc" data-card="${esc(layer.id)}">
      <div class="lc-top">
        <span class="lc-swatch" style="background:${layer.color}"></span>
        <span class="lc-name" title="${esc(layer.id)}">${esc(layer.title)}</span>
        <button class="ghost-btn danger" data-fp-remove="${esc(layer.id)}" title="Remove layer">
          <svg class="ico-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div class="set-note" style="margin-top:0">${esc(st.text)}</div>
      <div class="set-note">${esc(layer.src.quantity)} (${esc(layer.src.units)})${filters ? ` · quality filter: ${esc(filters)}` : ''}</div>
    </div>`;
  }).join('');
  host.querySelectorAll('[data-fp-remove]').forEach(b => b.addEventListener('click', () => toggleDataset(b.dataset.fpRemove, false)));
}

function footprintLegendItems() {
  return [...S.fp.values()].map(layer => {
    const st = fpStatus(layer);
    const ticks = st.kind === 'zoom' && !st.coverage ? '' : st.coverage
      ? `<div class="leg-ramp" style="background:${fpGradient(layer)}"></div>
         <div class="leg-ticks"><span>few</span><span>footprints per cell (log)</span><span>many</span></div>`
      : `<div class="leg-ramp" style="background:${fpGradient(layer)}"></div>
      <div class="leg-ticks">${Array.from({ length: 5 }, (_, i) => `<span>${fmtNum(layer.rMin + (layer.rMax - layer.rMin) * i / 4)}</span>`).join('')}</div>`;
    return `<div class="leg-item">
      <div class="leg-vn"><span class="leg-key" style="background:${layer.color}"></span>${esc(layer.src.quantity)}</div>
      <div class="leg-ds">${esc(layer.title)} · ${esc(layer.src.units)}</div>
      ${ticks}
      <div class="leg-prov">${esc(st.text)}${layer.rangeSource === 'footprints' && st.kind !== 'zoom' ? ' · range from loaded footprints (p2–p98)' : ''}</div>
    </div>`;
  }).join('');
}

/* Area of a GeoJSON polygon on the sphere (ha), for footprint-only analyses
   where no raster job reports the region's area. */
function geodesicAreaHa(g) {
  const R = 6371008.8, rad = Math.PI / 180;
  const ring = pts => {
    let a = 0;
    for (let k = 0; k < pts.length - 1; k++) {
      const [x1, y1] = pts[k], [x2, y2] = pts[k + 1];
      a += (x2 - x1) * rad * (2 + Math.sin(y1 * rad) + Math.sin(y2 * rad));
    }
    return Math.abs(a * R * R / 2);
  };
  const poly = rings => rings.reduce((sum, r, k) => sum + (k ? -ring(r) : ring(r)), 0);
  const polys = g.type === 'MultiPolygon' ? g.coordinates : g.type === 'Polygon' ? [g.coordinates] : [];
  return polys.reduce((sum, p) => sum + poly(p), 0) / 1e4;
}

/* Analysis: per-year statistics of every footprint in the drawn area. */
async function fpAnalyse(id, geometry) {
  try {
    return await fpPoll(await postJSON('/footprints/analysis', { source: id, geometry }));
  } catch (e) {
    return { name: id, kind: 'footprints', error: e.message };
  }
}
