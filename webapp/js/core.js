/* EOForestSTAC explorer: Configuration, state, fetching, theme, map and tile-server connection.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   CONFIG
══════════════════════════════════════════════════════════════════ */
/* Colour ramps as stop arrays, so the same definition drives both the
   continuous gradient bar and the discrete class swatches. */
const RAMPS = {
  greens:  ['#f7fcf5','#c7e9c0','#74c476','#238b45','#00441b'],
  rdylgn:  ['#a50026','#f46d43','#fee08b','#a6d96a','#006837'],
  viridis: ['#440154','#414487','#2a788e','#22a884','#7ad151','#fde725'],
  plasma:  ['#0d0887','#6a00a8','#b12a90','#e16462','#fca636','#f0f921'],
  inferno: ['#000004','#420a68','#932667','#dd513a','#fca50a','#fcffa4'],
  magma:   ['#000004','#3b0f70','#8c2981','#de4968','#fe9f6d','#fcfdbf'],
  reds:    ['#fff5f0','#fcbba1','#fb6a4a','#cb181d','#67000d'],
  blues:   ['#f7fbff','#c6dbef','#6baed6','#2171b5','#08306b'],
  ylorbr:  ['#ffffe5','#fee391','#fe9929','#cc4c02','#662506'],
  ylgnbu:  ['#ffffd9','#c7e9b4','#41b6c4','#225ea8','#081d58'],
  hot:     ['#0a0000','#ff0000','#ffff00','#ffffff'],
  greys:   ['#ffffff','#d9d9d9','#969696','#404040','#000000'],
  rdbu:    ['#b2182b','#ef8a62','#f7f7f7','#67a9cf','#2166ac'],
  spectral:['#9e0142','#f46d43','#ffffbf','#66c2a5','#5e4fa2'],
};
const rampCSS = n => `linear-gradient(to right,${(RAMPS[n] || RAMPS.greys).join(',')})`;

/* RAMPS above are only a fallback. The tiles are coloured by rio-tiler's own
   256-entry lookup table, so a hand-written 5-stop approximation puts the wrong
   colours in the legend. Fetch the real LUT and key the legend off that. */
const LUT = new Map();          // colormap name -> [[r,g,b,a] x 256]
const LUT_INFLIGHT = new Map(); // name -> promise, so concurrent layers share one fetch

function loadLUT(name) {
  if (LUT.has(name)) return Promise.resolve(LUT.get(name));
  if (LUT_INFLIGHT.has(name)) return LUT_INFLIGHT.get(name);
  if (!S.tiOk) return Promise.resolve(null);

  const p = (async () => {
    try {
      const raw = await fetchJSON(`${S.tiTiler}/colorMaps/${encodeURIComponent(name)}?f=json`);
      /* Sequential maps come back keyed 0..255; interval maps as
         [[[lo,hi],[r,g,b,a]], ...]. Normalise both to 256 stops. */
      let stops = null;
      if (Array.isArray(raw)) {
        stops = Array.from({ length: 256 }, (_, i) => {
          const hit = raw.find(e => Array.isArray(e?.[0]) && i >= e[0][0] && i <= e[0][1]);
          return (hit || raw[raw.length - 1])?.[1] || [0, 0, 0, 0];
        });
      } else if (raw && typeof raw === 'object') {
        stops = Array.from({ length: 256 }, (_, i) => raw[i] || raw[String(i)] || [0, 0, 0, 0]);
      }
      if (stops) LUT.set(name, stops);
      return stops;
    } catch { return null; }
    finally { LUT_INFLIGHT.delete(name); }
  })();
  LUT_INFLIGHT.set(name, p);
  return p;
}

const rgba = c => `rgba(${c[0]},${c[1]},${c[2]},${(c[3] ?? 255) / 255})`;

/* Exact colour for a normalised position, straight out of the server LUT. */
function colorAt(name, t) {
  const lut = LUT.get(name);
  if (!lut) return sampleRamp(name, t);
  const i = Math.max(0, Math.min(255, Math.round(Math.max(0, Math.min(1, t)) * 255)));
  return rgba(lut[i]);
}

/* Build the gradient from the LUT. 48 stops is visually exact for smooth maps
   and keeps hard edges of stepped maps roughly in place. */
function gradientFor(name) {
  const lut = LUT.get(name);
  if (!lut) { loadLUT(name).then(s => { if (s) renderLegend(); }); return rampCSS(name); }
  const N = 48;
  const stops = Array.from({ length: N }, (_, k) => {
    const t = k / (N - 1);
    return `${rgba(lut[Math.round(t * 255)])} ${(t * 100).toFixed(1)}%`;
  });
  return `linear-gradient(to right,${stops.join(',')})`;
}

/* The server knows which colormaps it supports — 211 of them — so don't ship
   a guessed subset in the client. */
async function loadColormapNames() {
  if (!S.tiOk) return;
  try {
    /* Without f=json this endpoint negotiates to HTML. */
    const res = await fetchJSON(`${S.tiTiler}/colorMaps?f=json`);
    const list = res?.colormaps ?? res?.colorMaps ?? res;
    const names = (Array.isArray(list) ? list : [])
      .map(c => (typeof c === 'string' ? c : c?.id ?? c?.name))
      .filter(Boolean);
    if (names.length) S.colormapNames = names;
  } catch { /* keep the built-in list */ }
}

/* Curated names first, then everything else the server offers. */
function colormapOptions(selected) {
  const curated = Object.keys(RAMPS).filter(n => S.colormapNames.includes(n));
  const rest = S.colormapNames.filter(n => !curated.includes(n)).sort();
  const opt = n => `<option value="${esc(n)}" ${n === selected ? 'selected' : ''}>${esc(n)}</option>`;
  if (!rest.length) return curated.map(opt).join('');
  return `<optgroup label="Common">${curated.map(opt).join('')}</optgroup>` +
         `<optgroup label="All (${rest.length})">${rest.map(opt).join('')}</optgroup>`;
}
function sampleRamp(name, t) {
  const s = RAMPS[name] || RAMPS.greys;
  const x = Math.max(0, Math.min(1, t)) * (s.length - 1);
  const i = Math.min(Math.floor(x), s.length - 2);
  const f = x - i;
  const rgb = h => [1, 3, 5].map(k => parseInt(h.slice(k, k + 2), 16));
  const a = rgb(s[i]), b = rgb(s[i + 1]);
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(',')})`;
}

const CFG = {
  catalog: 'https://s3.gfz.de/dog.atlaseo-glm.eo-gridded-data/collections/catalog.json',
  defaultTiTiler: window.EOFOREST_CONFIG?.tiTilerUrl || 'http://localhost:8000',
  home: { center: [20, 10], zoom: 3 },
  /* data_vars that are grid/CRS carriers rather than renderable rasters */
  skipVars: new Set(['spatial_ref','crs','transverse_mercator','lambert_azimuthal_equal_area','latitude_longitude','polar_stereographic']),
  /* Rail order follows the catalog; `short` is the rail label, `label` the
     panel title. Icons are 24×24 stroke paths. */
  themeInfo: {
    'biomass-carbon':       { label:'Biomass & Carbon',       short:'Biomass',     cls:'bc',
      icon:'<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>' },
    'disturbance-change':   { label:'Disturbance & Change',   short:'Disturbance', cls:'dc',
      icon:'<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>' },
    'structure-demography': { label:'Structure & Demography', short:'Structure',   cls:'sd',
      icon:'<path d="m17 14 3 3.3a1 1 0 0 1-.7 1.7H4.7a1 1 0 0 1-.7-1.7L7 14h-.3a1 1 0 0 1-.7-1.7L9 9h-.2A1 1 0 0 1 8 7.3L12 3l4 4.3a1 1 0 0 1-.8 1.7H15l3 3.3a1 1 0 0 1-.7 1.7H17Z"/><path d="M12 22v-3"/>' },
    // A drone (side view) sending laser pulses down
    'uls':                  { label:'ULS / UAV LiDAR',        short:'ULS',         cls:'al',
      icon:'<line x1="3" y1="4" x2="9" y2="4"/><line x1="15" y1="4" x2="21" y2="4"/><path d="M6 4v3h12V4"/><rect x="9" y="7" width="6" height="3.5" rx="1"/><path d="M12 13v1.5M12 17.5V19"/><path d="M9.2 13.5l-1 1.6M6.9 17.2l-.9 1.5"/><path d="M14.8 13.5l1 1.6M17.1 17.2l.9 1.5"/>' },
    'als-biomass':          { label:'ALS Biomass',            short:'ALS biomass', cls:'ab',
      icon:'<path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>' },
    'land-use-land-cover':  { label:'Land Use & Land Cover',  short:'Land use',    cls:'lu',
      icon:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>' },
    'spaceborne-lidar':     { label:'Spaceborne LiDAR',       short:'Spaceborne LiDAR', cls:'sl',
      icon:'<path d="M13 7 9 3 5 7l4 4"/><path d="m17 11 4 4-4 4-4-4"/><path d="m8 12 4 4 6-6-4-4Z"/><path d="m16 8 3-3"/><path d="M9 21a6 6 0 0 0-6-6"/>' },
  },
  themeIconFallback: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
};

/* Key-free tile services. Esri's ArcGIS Online basemaps and OSM need no token. */
const ESRI_ATTR = 'Tiles &copy; <a href="https://www.esri.com">Esri</a>';
const BASEMAPS = {
  dark: {
    name: 'Dark canvas',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attr: ESRI_ATTR, maxZoom: 16,
    thumb: 'linear-gradient(135deg,#2b2f31,#3c4245 60%,#22262a)',
  },
  satellite: {
    name: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr: ESRI_ATTR + ', Maxar, Earthstar Geographics', maxZoom: 19,
    thumb: 'linear-gradient(135deg,#1d3b1c,#3e5a25 45%,#7a6a3a 75%,#2b4a6b)',
  },
  terrain: {
    name: 'Terrain',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}',
    attr: ESRI_ATTR, maxZoom: 13,
    thumb: 'linear-gradient(135deg,#cdd6c0,#a8b894 55%,#8fa07c)',
  },
  light: {
    name: 'Light canvas',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
    attr: ESRI_ATTR, maxZoom: 16,
    thumb: 'linear-gradient(135deg,#f2f2f0,#e0e0dc 60%,#cfcfca)',
  },
  street: {
    name: 'OpenStreetMap',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attr: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 19,
    thumb: 'linear-gradient(135deg,#eee9e2,#d8e6cf 55%,#b9d4e8)',
  },
  none: {
    name: 'No basemap',
    url: null, attr: '', maxZoom: 22,
    thumb: 'repeating-conic-gradient(#3a423d 0% 25%,#2a302c 0% 50%) 0/14px 14px',
  },
};

const LABELS_URL = 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}';

/* Categorical layer colours, validated for colour-vision deficiency on the
   panel (light and dark); the same slot colours a layer on the map, in the
   legend and in analysis charts (var(--sN) gives the dark-mode step). */
const LAYER_COLORS = ['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300'];

/* First slot no active layer uses, so a colour stays with its layer. */
function freeColorSlot() {
  const used = new Set([...S.layers.values(), ...(S.fp?.values() || [])].map(l => l.slot));
  for (let i = 0; i < LAYER_COLORS.length; i++) if (!used.has(i)) return i;
  return (S.layers.size + (S.fp?.size || 0)) % LAYER_COLORS.length;
}

/* ══════════════════════════════════════════════════════════════════
   STATE
══════════════════════════════════════════════════════════════════ */
const S = {
  /* A deployment-provided endpoint is authoritative. Saved values are only
     useful for local development where config.js has no explicit override. */
  tiTiler:   window.EOFOREST_CONFIG?.tiTilerUrl !== 'http://localhost:8000'
               ? window.EOFOREST_CONFIG.tiTilerUrl
               : localStorage.getItem('tiTilerUrl') || CFG.defaultTiTiler,
  tiOk:      false,
  catalog:   null,
  layers:    new Map(),
  map:       null,
  baseLayer: null,
  labelLayer:null,
  basemapId: localStorage.getItem('basemap') || 'light',
  showLabels:localStorage.getItem('labels') !== '0',
  autoZoom:  localStorage.getItem('autozoom') !== '0',
  view:      'data',
  cat:       null,
  panelOpen: true,
  legendOpen: true,
  legTab: 'legend',            // legend | analysis
  an: { running: false, progress: 0, message: '', error: null, result: null, resultSig: null, measure: 'mean' },
  dl: { drawing: null, geometry: null, shape: null, excluded: new Set(), estimate: null, polling: null },
  colormapNames: Object.keys(RAMPS),
};

const el  = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

/* ══════════════════════════════════════════════════════════════════
   FETCH (CORS-proxied through TiTiler when available)
══════════════════════════════════════════════════════════════════ */
/* noStore: for polling. TiTiler marks GET responses cacheable for an hour, so
   without it every poll after the first was answered from the browser cache. */
async function fetchJSON(url, { viaTiTiler = false, noStore = false } = {}) {
  const target = (viaTiTiler && S.tiOk)
    ? `${S.tiTiler}/proxy/fetch?url=${encodeURIComponent(url)}`
    : url;
  let r;
  try { r = await fetch(target, noStore ? { cache: 'no-store' } : undefined); }
  catch (e) {
    if (!viaTiTiler && S.tiOk)
      r = await fetch(`${S.tiTiler}/proxy/fetch?url=${encodeURIComponent(url)}`);
    else throw e;
  }
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}
const resolveUrl = (base, rel) => { try { return new URL(rel, base).href; } catch { return rel; } };

/* ══════════════════════════════════════════════════════════════════
   THEME
══════════════════════════════════════════════════════════════════ */
function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem('theme', t);
}

/* ══════════════════════════════════════════════════════════════════
   MAP
══════════════════════════════════════════════════════════════════ */
function initMap() {
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem('mapState')); } catch {}
  // A shared link's view wins over the one remembered in this browser
  const shared = parseShareHash().view;
  if (shared) saved = { lat: shared.center[0], lng: shared.center[1], z: shared.zoom };

  S.map = L.map('map', {
    center: saved ? [saved.lat, saved.lng] : CFG.home.center,
    zoom:   saved ? saved.z : CFG.home.zoom,
    zoomControl: false,
    attributionControl: true,
    worldCopyJump: true,
    minZoom: 2,
  });
  // The pixel inspector sits above the credit line, whose height depends on
  // the basemap's attribution
  new ResizeObserver(([entry]) => document.documentElement.style.setProperty(
    '--attrib-h', `${Math.ceil(entry.target.getBoundingClientRect().height)}px`))
    .observe(S.map.attributionControl.getContainer());
  // Who made the explorer, on the map itself (the About dialog has the details)
  S.map.attributionControl.setPrefix(
    '<a href="#" data-about>EOForestSTAC</a> by GFZ · this map viewer coded with Claude Code, '
    + 'design inspired by <a href="https://www.globalforestwatch.org" target="_blank" rel="noopener noreferrer">Global Forest Watch</a>');

  // Labels ride above data tiles (tilePane 200) but below vectors (overlayPane 400)
  S.map.createPane('labels');
  Object.assign(S.map.getPane('labels').style, { zIndex: 350, pointerEvents: 'none' });

  setBasemap(S.basemapId);
  setLabels(S.showLabels);

  S.map.on('click', onMapClick);
  S.map.on('mousemove', e => {
    el('ro-lat').textContent = e.latlng.lat.toFixed(3);
    el('ro-lon').textContent = L.Util.wrapNum(e.latlng.lng, [-180, 180], true).toFixed(3);
  });
  S.map.on('moveend', () => {
    const c = S.map.getCenter();
    localStorage.setItem('mapState', JSON.stringify({ lat: c.lat, lng: c.lng, z: S.map.getZoom() }));
    syncShareUrl();
  });
  S.map.on('zoomend', () => {
    const zoom = S.map.getZoom();
    el('ro-z').textContent = zoom;
    S.layers.forEach(layer => {
      updateFootprint(layer);
      if (!layer.pyramidUrl || !layer.leafletLayer) return;
      const lvl = getPyramidLevel(layer, zoom);
      if (lvl !== layer._lastPyramidLevel) {
        layer._lastPyramidLevel = lvl;
        setTileUrl(layer, zoom);
      }
    });
    renderLegend();
  });
  el('ro-z').textContent = S.map.getZoom();
}

function setBasemap(id) {
  const bm = BASEMAPS[id] || BASEMAPS.dark;
  if (S.baseLayer) { S.map.removeLayer(S.baseLayer); S.baseLayer = null; }
  if (bm.url) {
    S.baseLayer = L.tileLayer(bm.url, { attribution: bm.attr, maxZoom: 22, maxNativeZoom: bm.maxZoom });
    S.baseLayer.addTo(S.map);
    S.baseLayer.bringToBack();
  }
  S.basemapId = id;
  localStorage.setItem('basemap', id);
  document.querySelectorAll('.bm-opt').forEach(b => b.classList.toggle('on', b.dataset.bm === id));
}

function setLabels(on) {
  S.showLabels = on;
  localStorage.setItem('labels', on ? '1' : '0');
  if (on && !S.labelLayer) {
    S.labelLayer = L.tileLayer(LABELS_URL, { pane: 'labels', maxZoom: 22, maxNativeZoom: 13, attribution: '' }).addTo(S.map);
  } else if (!on && S.labelLayer) {
    S.map.removeLayer(S.labelLayer);
    S.labelLayer = null;
  }
}

/* ── Zoom to a bounding box ────────────────────────────────────────── */
function boundsToLatLng(b) {
  if (!Array.isArray(b) || b.length !== 4 || b.some(v => !Number.isFinite(v))) return null;
  const [w, s, e, n] = b;
  const clamp = v => Math.max(-85.05, Math.min(85.05, v));
  return L.latLngBounds([clamp(Math.min(s, n)), Math.min(w, e)], [clamp(Math.max(s, n)), Math.max(w, e)]);
}

function zoomToLayer(layer, { animate = true } = {}) {
  const bb = boundsToLatLng(layer.bounds);
  if (!bb || !bb.isValid()) return false;
  S.map.flyToBounds(bb, { padding: [56, 56], maxZoom: 12, duration: animate ? 0.9 : 0 });
  return true;
}

function zoomToAllLayers() {
  let combined = null;
  S.layers.forEach(l => {
    const bb = boundsToLatLng(l.bounds);
    if (!bb) return;
    combined = combined ? combined.extend(bb) : bb;
  });
  if (combined?.isValid()) S.map.flyToBounds(combined, { padding: [56, 56], maxZoom: 12, duration: 0.9 });
}

/* ══════════════════════════════════════════════════════════════════
   TITILER CONNECTION
══════════════════════════════════════════════════════════════════ */
async function checkTiTiler() {
  const dot = el('rail-status'), note = el('conn-note');
  dot.className = 'rail-status wait';
  note.textContent = 'Checking connection…';
  try {
    const ac = new AbortController();
    const t = setTimeout(() => ac.abort(), 4500);
    const r = await fetch(`${S.tiTiler}/`, { signal: ac.signal });
    clearTimeout(t);
    S.tiOk = r.ok || r.status === 404;
  } catch { S.tiOk = false; }
  dot.className = `rail-status ${S.tiOk ? 'ok' : 'err'}`;
  dot.title = S.tiOk ? `Tile server connected — ${S.tiTiler}` : 'Tile server unreachable';
  dot.setAttribute('aria-label', dot.title);
  note.innerHTML = S.tiOk
    ? `Connected to <code>${esc(S.tiTiler)}</code>.`
    : `Cannot reach <code>${esc(S.tiTiler)}</code>. Tiles and pixel queries are unavailable.`;
}
