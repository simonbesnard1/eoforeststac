/* EOForestSTAC explorer: shareable links. The URL hash holds the map view,
   basemap and active layers with their settings, so a link opens exactly
   what its sender saw:
     #map=5/48.300/8.200&bm=light&layer=GAMI_AGECLASS~v:forest_age~r:0~t:1~x:0.3
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

const SHARE_DEFAULT_OPACITY = 0.9;

/* The hash for the current state ('' when nothing is shown). */
function shareHash() {
  if (!S.map) return '';
  const c = S.map.getCenter();
  const p = new URLSearchParams();
  p.set('map', `${S.map.getZoom()}/${c.lat.toFixed(3)}/${L.Util.wrapNum(c.lng, [-180, 180], true).toFixed(3)}`);
  if (S.basemapId) p.set('bm', S.basemapId);
  for (const layer of S.layers.values()) {
    const parts = [layer.id, `v:${layer.activeVar}`];
    if (layer.zarrIndex) parts.push(`r:${layer.zarrIndex}`);
    if (layer.dimValue) parts.push(`t:${layer.dimValue}`);
    if (layer.extraDims?.some(d => d.index)) parts.push(`x:${layer.extraDims.map(d => d.index).join('.')}`);
    if (layer.colormapManual) parts.push(`c:${layer.colormap}`);
    if (layer.opacity !== SHARE_DEFAULT_OPACITY) parts.push(`o:${layer.opacity}`);
    if (layer.rangeSource === 'manual') parts.push(`lo:${layer.rMin}`, `hi:${layer.rMax}`);
    p.append('layer', parts.join('~'));
  }
  for (const id of S.fp?.keys() || []) p.append('fp', id);
  return p.toString();
}

/* Keep the address bar current without filling the browser history. */
let _shareLast = null;
function syncShareUrl() {
  if (S.restoring) return;
  const hash = shareHash();
  if (hash === _shareLast) return;
  _shareLast = hash;
  history.replaceState(null, '', hash ? `#${hash}` : location.pathname + location.search);
}

function parseShareHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const view = (p.get('map') || '').split('/').map(Number);
  const layers = p.getAll('layer').map(spec => {
    const [id, ...rest] = spec.split('~');
    const opts = Object.fromEntries(rest.map(kv => [kv.slice(0, kv.indexOf(':')), kv.slice(kv.indexOf(':') + 1)]));
    return { id, ...opts };
  });
  return {
    view: view.length === 3 && view.every(Number.isFinite) ? { zoom: view[0], center: [view[1], view[2]] } : null,
    basemap: p.get('bm'),
    layers,
    footprints: p.getAll('fp'),
  };
}

/* Open what a link describes; unknown datasets or settings are skipped. */
async function restoreFromUrl() {
  const share = parseShareHash();
  if (!share.layers.length && !share.footprints.length) return;
  S.restoring = true;
  const autoZoom = S.autoZoom;
  S.autoZoom = false;
  try {
    if (share.basemap && BASEMAPS[share.basemap]) setBasemap(share.basemap);
    for (const spec of share.layers) {
      const col = findCollection(spec.id);
      if (!col || col.footprint) continue;
      const r = parseInt(spec.r, 10);
      if (r > 0 && r < col.zarrs.length) col.zarrIndex = r;
      await toggleDataset(spec.id, true);
      const layer = S.layers.get(spec.id);
      if (!layer) continue;
      if (spec.v && spec.v !== layer.activeVar && layer.variables.includes(spec.v)) {
        Object.assign(layer, { activeVar: spec.v, label: spec.v, extraDims: null, colormapManual: false });
        await fetchVariableMeta(layer);
      }
      const extra = (spec.x || '').split('.').map(Number);
      (layer.extraDims || []).forEach((d, i) => {
        if (Number.isInteger(extra[i]) && extra[i] >= 0 && extra[i] < d.values.length) d.index = extra[i];
      });
      const t = parseInt(spec.t, 10);
      if (layer.dimInfo && t >= 0 && t < layer.dimInfo.length) layer.dimValue = t;
      if (spec.c) Object.assign(layer, { colormap: spec.c, colormapManual: true });
      const o = parseFloat(spec.o);
      if (o >= 0 && o <= 1) layer.opacity = o;
      const lo = parseFloat(spec.lo), hi = parseFloat(spec.hi);
      if (Number.isFinite(lo) && Number.isFinite(hi) && hi > lo) Object.assign(layer, { rMin: lo, rMax: hi, rangeSource: 'manual' });
      await updateLeafletLayer(spec.id);
    }
    for (const id of share.footprints) if (findCollection(id)?.footprint) await toggleDataset(id, true);
    if (share.view) S.map.setView(share.view.center, share.view.zoom, { animate: false });
  } finally {
    S.autoZoom = autoZoom;
    S.restoring = false;
  }
  renderLayerPanel();
  renderLegend();
  syncLayerCount();
}

/* The toolbar's "Copy link" button. */
async function copyShareLink(button) {
  syncShareUrl();
  let ok = true;
  try { await navigator.clipboard.writeText(location.href); } catch { ok = false; }
  const tip = button.dataset.tip;
  button.dataset.tip = ok ? 'Link copied' : 'Copy the address bar to share';
  el('share-status').textContent = button.dataset.tip;
  setTimeout(() => { button.dataset.tip = tip; }, 2000);
}
