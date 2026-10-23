/* EOForestSTAC explorer: Map layers: pyramids, variables, value ranges and tile URLs.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   PYRAMID HELPERS
══════════════════════════════════════════════════════════════════ */
function getPyramidLevel(layer, zoom) {
  if (!layer.pyramidUrl) return null;
  return Math.min(Math.max(0, layer.nativeMinZoom - zoom), layer.numPyramidLevels - 1);
}
function getEffectiveZarrUrl(layer, zoom) {
  const level = getPyramidLevel(layer, zoom ?? S.map.getZoom());
  if (level === null || level === 0) return layer.zarrUrl;
  return `${layer.pyramidUrl}/${level}`;
}

/* ══════════════════════════════════════════════════════════════════
   LAYERS
══════════════════════════════════════════════════════════════════ */
async function toggleDataset(id, on) {
  const row = el(`ds-${id}`);
  if (on) {
    row?.classList.add('on');
    const col = findCollection(id);
    if (!col) return;
    if (col.footprint) await toggleFootprints(col, true);
    else await activateLayer(col);
  } else {
    row?.classList.remove('on');
    const box = row?.querySelector('input[type=checkbox]');
    if (box) box.checked = false;
    if (S.fp.has(id)) toggleFootprints(findCollection(id), false);
    else removeLayer(id);
  }
  renderLayerPanel();
  renderLegend();
  syncLayerCount();
  /* Jump straight to the controls for the layer just switched on — otherwise
     the variable/colormap/range pickers sit unnoticed behind a rail tab. */
  if (on) openView('layers');
}

/* The zarr store is the authority on which variables exist — the STAC item's
   `variables` property is often absent or stale. `/dataset/keys` is the
   registered endpoint here; `/variables` is NOT mounted by titiler.xarray's
   default app, so asking for it just 404s. */
async function fetchVariables(zarrUrl, fallback = []) {
  if (S.tiOk) {
    for (const route of ['/dataset/keys', '/variables']) {
      try {
        const keys = await fetchJSON(`${S.tiTiler}${route}?` + new URLSearchParams({ url: zarrUrl }));
        const usable = (Array.isArray(keys) ? keys : []).filter(k => !CFG.skipVars.has(k));
        if (usable.length) return usable;
      } catch { /* try next route */ }
    }
  }
  const fb = fallback.filter(k => !CFG.skipVars.has(k));
  return fb.length ? fb : ['data'];
}

/* Pull everything that depends on the chosen variable: dimensions, value
   range, zoom floor and geographic bounds. tilejson carries minzoom/maxzoom
   and minmax; /info carries the variable's xarray attrs and dim names. */
async function fetchVariableMeta(layer, { resetRange = true } = {}) {
  if (!S.tiOk) return;
  const qs = new URLSearchParams({ url: layer.zarrUrl, variable: layer.activeVar });
  for (const s of extraSels(layer)) qs.append('sel', s);

  const [info, tj] = await Promise.all([
    fetchJSON(`${S.tiTiler}/info?${qs}`).catch(() => null),
    fetchJSON(`${S.tiTiler}/WebMercatorQuad/tilejson.json?${qs}`).catch(() => null),
  ]);

  /* /info refuses variables with more than one extra dimension (GAMI is
     members × time × y × x). Pin every extra dimension but the time-like one
     and ask again; the remaining one becomes the usual slider. */
  if (!info && !layer.extraDims) {
    const res = await fetchJSON(`${S.tiTiler}/dataset/dims?` +
      new URLSearchParams({ url: layer.zarrUrl, variable: layer.activeVar })).catch(() => null);
    const dims = res?.dims || [];
    if (dims.length >= 2) {
      const main = dims.find(d => d.values.some(v => /^\d{4}-\d{2}-\d{2}/.test(v))) || dims[0];
      /* Numeric labels in numeric order: GAMI stores its members as
         4, 1, 2, 7, 0, ... Selection is by value, so reordering is safe;
         text labels (age classes) keep the store's order. */
      const ordered = values => values.every(v => v !== '' && Number.isFinite(Number(v)))
        ? [...values].sort((a, b) => Number(a) - Number(b)) : values;
      layer.extraDims = dims.filter(d => d !== main).map(d => ({ name: d.name, values: ordered(d.values), index: 0 }));
      return fetchVariableMeta(layer, { resetRange });
    }
  }

  if (info) {
    layer.dimInfo = parseDimInfo(info);
    if (layer.dimValue >= (layer.dimInfo?.length ?? 1)) layer.dimValue = 0;
    layer.attrs  = info.attrs || {};
    layer.dtype  = info.dtype || '';
    layer.width  = info.width  || 0;
    layer.height = info.height || 0;
    const band = stacBand(layer);
    const unitsByVariable = layer.summaries?.units_by_variable || {};
    layer.units  = layer.attrs.units || band?.unit || unitsByVariable[layer.activeVar] || '';
    layer.label  = layer.attrs.long_name || layer.attrs.standard_name
      || band?.description || band?.name || layer.activeVar;
    if (Array.isArray(info.bounds) && info.bounds.length === 4) layer.bounds = info.bounds.map(Number);
  }

  if (tj) {
    if (Number.isFinite(tj.minzoom)) {
      layer.nativeMinZoom = tj.minzoom;
      if (!layer.pyramidUrl) layer.minZoom = tj.minzoom;
    }
    if (Number.isFinite(tj.maxzoom)) layer.maxZoom = tj.maxzoom;
    if (Array.isArray(tj.bounds) && tj.bounds.length === 4) layer.bounds = tj.bounds.map(Number);
    if (!layer.dtype && tj.data_type) layer.dtype = tj.data_type;
    if (resetRange) applyRange(layer, tj.minmax, info?.attrs);
  } else if (resetRange && info) {
    applyRange(layer, info.minmax, info.attrs);
  }

  if (!layer.colormapManual) layer.colormap = automaticColormap(layer);
  if (resetRange) {
    const declared = metadataClasses(layer);
    if (!(declared?.length && applyClassRange(layer, declared))) await reconcileRange(layer);
  }
  await loadLUT(layer.colormap);   // class swatches need the real LUT
  layer.classes = buildClasses(layer);

  /* tilejson reports minzoom 0 for zarr regardless of size, so the real
     constraint is the array budget, not the declared zoom range. */
  layer.zoomFloor = computeZoomFloor(layer);
  if (layer.zoomFloor !== null) {
    layer.nativeMinZoom = Math.max(layer.nativeMinZoom, layer.zoomFloor);
    layer.minZoom = layer.pyramidUrl
      ? Math.max(0, layer.zoomFloor - (layer.numPyramidLevels - 1))
      : layer.zoomFloor;
  }
}

/* Levels the pyramid builder finished, counted from 1. Each finished level
   gets a _SUCCESS marker; an interrupted build leaves levels that exist but
   are partly or wholly empty (HANSEN's level 1 had no loss_year chunks), which
   rendered blank maps and empty statistics. Read straight from S3. */
async function completePyramidLevels(pyramidUrl) {
  let n = 0;
  for (let lvl = 1; lvl <= 10; lvl++) {
    try {
      const r = await fetch(`${pyramidUrl}/${lvl}/_SUCCESS`, { method: 'HEAD', cache: 'no-store' });
      if (!r.ok) break;
      n = lvl;
    } catch { break; }
  }
  return n;
}

/* Where, and over what area, can /statistics read? rio-tiler clips to the
   feature and refuses anything over its 1 GB array ceiling BEFORE downsampling
   to max_size, so the clipped slice must fit STATS_BUDGET. Measure the whole
   extent at the coarsest level when that fits. Otherwise (HANSEN's coarsest
   pyramid level is still 720k × 280k px) measure the part of the layer in
   view, shrunk around its centre until it fits. */
function statisticsTarget(layer) {
  const bb = boundsToLatLng(layer.bounds);
  if (!bb || !layer.width || !layer.height) return null;
  const itemsize = DTYPE_BYTES[String(layer.dtype).replace(/^[<>|=]/, '')] ?? 4;
  const bands = selParams(layer).length ? 1 : Math.max(1, layer.dimInfo?.length ?? 1);
  const level = layer.pyramidUrl && layer.numPyramidLevels >= 2 ? layer.numPyramidLevels - 1 : 0;
  const url = level ? `${layer.pyramidUrl}/${level}` : layer.zarrUrl;
  // Pyramid level k halves the native grid k times
  const pxLon = (bb.getEast() - bb.getWest()) / (layer.width / 2 ** level);
  const pxLat = (bb.getNorth() - bb.getSouth()) / (layer.height / 2 ** level);
  const bytes = (w, s, e, n) => ((e - w) / pxLon) * ((n - s) / pxLat) * bands * itemsize;

  let [w, s, e, n] = [bb.getWest(), bb.getSouth(), bb.getEast(), bb.getNorth()];
  if (bytes(w, s, e, n) < STATS_BUDGET) return { url, area: [w, s, e, n], whole: true };

  const view = S.map.getBounds();
  [w, s, e, n] = [Math.max(w, view.getWest()), Math.max(s, view.getSouth()),
                  Math.min(e, view.getEast()), Math.min(n, view.getNorth())];
  if (!(e > w && n > s)) {          // layer out of view: use its centre
    const c = bb.getCenter();
    [w, s, e, n] = [c.lng, c.lat, c.lng, c.lat];
  }
  const cx = (w + e) / 2, cy = (s + n) / 2;
  // Largest window around the centre that fits, keeping the view's aspect
  const fit = STATS_BUDGET * 0.9 / (bands * itemsize);          // pixels
  const aspect = (e - w) / pxLon > 0 && (n - s) / pxLat > 0 ? ((e - w) / pxLon) / ((n - s) / pxLat) : 1;
  const hPx = Math.min((n - s) / pxLat || Infinity, Math.sqrt(fit / aspect));
  const wPx = Math.min((e - w) / pxLon || Infinity, hPx * aspect);
  const hw = (wPx * pxLon) / 2, hh = (hPx * pxLat) / 2;
  return { url, area: [cx - hw, cy - hh, cx + hw, cy + hh], whole: false };
}

/* Measure the actual distribution. Returns null when it can't be read.
   titiler.xarray only serves POST /statistics, with the area as a GeoJSON
   Feature; the result comes back in properties.statistics. */
async function measureStatistics(layer) {
  const target = statisticsTarget(layer);
  if (!target || !S.tiOk) return null;
  try {
    const qs = new URLSearchParams({ url: target.url, variable: layer.activeVar, max_size: '1024' });
    for (const s of selParams(layer)) qs.append('sel', s);
    const [w, s, e, n] = target.area;
    const feature = {
      type: 'Feature', properties: {},
      geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] },
    };
    const r = await fetch(`${S.tiTiler}/statistics?${qs}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(feature),
    });
    if (!r.ok) return null;
    const stats = (await r.json())?.properties?.statistics;
    const band = stats && typeof stats === 'object' ? Object.values(stats)[0] : null;
    if (!band) return null;
    const pick = (...k) => { for (const n of k) if (Number.isFinite(Number(band[n]))) return Number(band[n]); return null; };
    return {
      min: pick('min'), max: pick('max'),
      p2:  pick('percentile_2', 'percentile_2.0'),
      p98: pick('percentile_98', 'percentile_98.0'),
      whole: target.whole,
    };
  } catch { return null; }
}

/* A declared valid_min/valid_max is a validity contract, not a display range:
   SAATCHI declares 0–1000 Mg/ha while 98 % of its pixels sit below 280, so a
   declared stretch leaves most of the map in the bottom of the ramp. Display
   the measured p2–p98 whenever it can be read, kept inside the declared
   bounds; the declared/STAC/tilejson range is only the fallback. */
async function reconcileRange(layer) {
  layer.dataRange = null;
  /* Small integer ranges are codes or masks — a percentile stretch would cut
     off the rare values. */
  const isInt = /^u?int|^bool/i.test(layer.dtype || '');
  if (layer.rangeKnown && isInt && layer.rMax - layer.rMin <= 11) return;

  /* Stores too large to measure here (ALS 1 m, ALS biomass countries) carry
     a p2–p98 computed from the data at ingestion. */
  const stored = parseRangeAttr(layer.attrs?.display_range);
  if (stored) { setDataRange(layer, stored[0], stored[1], 'data'); return; }

  const st = await measureStatistics(layer);
  if (!st) return;
  /* A sample of the view is only a stand-in: it must not override a range the
     dataset declares (HANSEN tree_cover is 0–100 %, a West African window
     gave 1–12 %). Use it only when nothing else is known. */
  if (!st.whole && layer.rangeKnown) return;
  layer.stats = st;

  let lo = st.p2 ?? st.min, hi = st.p98 ?? st.max;
  if (layer.rangeKnown) { lo = Math.max(lo, layer.rMin); hi = Math.min(hi, layer.rMax); }
  if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi <= lo) return;
  setDataRange(layer, lo, hi, st.whole ? 'measured' : 'measured-view');
}

function parseRangeAttr(v) {
  if (typeof v === 'string') { try { v = JSON.parse(v); } catch { return null; } }
  if (!Array.isArray(v) || v.length < 2) return null;
  const [lo, hi] = v.map(Number);
  return Number.isFinite(lo) && Number.isFinite(hi) && hi > lo ? [lo, hi] : null;
}

/* Three significant digits of the value or of the span, whichever is finer:
   toPrecision(3) alone turned years 2001–2023 into 2000–2020. */
function roundRangeEnd(v, span) {
  if (!Number.isFinite(v) || v === 0) return v;
  const digits = (x) => 2 - Math.floor(Math.log10(Math.abs(x)));
  const d = Math.min(12, Math.max(0, digits(v), span > 0 ? digits(span) : 0));
  return +v.toFixed(d);
}

/* Kept on the layer so a manual range can be reset back to it. */
function setDataRange(layer, lo, hi, source) {
  layer.rMin = roundRangeEnd(lo, hi - lo);
  layer.rMax = roundRangeEnd(hi, hi - lo);
  layer.rangeKnown = true;
  layer.rangeSource = source;
  layer.dataRange = { lo: layer.rMin, hi: layer.rMax, source };
}

/* Class rasters are coloured by value position in the rescale range, so the
   range must be exactly the declared class values — never a percentile cut. */
function applyClassRange(layer, classes) {
  const values = classes.map(c => c.value);
  const lo = Math.min(...values), hi = Math.max(...values);
  if (!(hi > lo)) return false;
  layer.rMin = lo; layer.rMax = hi;
  layer.rangeKnown = true;
  layer.rangeSource = 'classes';
  return true;
}

/* Bytes one tile or statistics request may read. The map fetches ~a dozen
   tiles at once and the server runs up to 8 reads in parallel, so this has
   to stay far below rio-tiler's 1 GB per-array ceiling. */
const READ_BUDGET = 1.5e8;

/* One /statistics call runs alone, so it may read more than a tile: CCI's
   coarsest level (6328 × 3164 float64, 160 MB) must fit, while staying well
   inside rio-tiler's 1e9-element ceiling and the server's memory. */
const STATS_BUDGET = 5e8;

const DTYPE_BYTES = {
  bool:1, int8:1, uint8:1, int16:2, uint16:2, float16:2,
  int32:4, uint32:4, float32:4, int64:8, uint64:8, float64:8,
  complex64:8, complex128:16,
};

/* rio-tiler clips the array to the tile bbox and then refuses anything over
   RIO_TILER_MAX_ARRAY_SIZE (1 GB), returning a 500. At low zoom a tile covers
   most of a continental grid, so the clip barely helps. Work out the first
   zoom whose clipped slice fits, and refuse to request tiles below it — the
   footprint outline is shown instead. */
function computeZoomFloor(layer) {
  const { width, height, dtype } = layer;
  const bb = boundsToLatLng(layer.bounds);
  if (!width || !height || !bb) return null;

  const itemsize = DTYPE_BYTES[String(dtype).replace(/^[<>|=]/, '')] ?? 4;
  const bands = selParam(layer) ? 1 : Math.max(1, layer.dimInfo?.length ?? 1);
  const lonSpan = Math.max(1e-6, bb.getEast() - bb.getWest());
  const latSpan = Math.max(1e-6, bb.getNorth() - bb.getSouth());
  const pxLon = lonSpan / width, pxLat = latSpan / height;

  for (let z = 0; z <= 22; z++) {
    const deg = 360 / 2 ** z;
    const w = Math.min(width,  deg / pxLon);
    const h = Math.min(height, deg / pxLat);
    if (w * h * bands * itemsize < READ_BUDGET) return z;
  }
  return 22;
}

function stacBand(layer) {
  return layer.rasterBands?.find(b => b.name === layer.activeVar)
    || (layer.rasterBands?.length === 1 ? layer.rasterBands[0] : null);
}

function metadataClasses(layer) {
  const attrs = layer.attrs || {};
  let legend = attrs.legend;
  if (typeof legend === 'string') {
    try { legend = JSON.parse(legend); } catch { legend = null; }
  }
  if (legend && typeof legend === 'object' && !Array.isArray(legend)) {
    return Object.entries(legend).map(([value, label]) => ({ value: +value, label: String(label) }))
      .filter(c => Number.isFinite(c.value)).sort((a, b) => a.value - b.value);
  }

  const values = Array.isArray(attrs.flag_values) ? attrs.flag_values : null;
  const meanings = attrs.flag_meanings
    ? String(attrs.flag_meanings).trim().split(/[\s,]+/).map(v => v.replaceAll('_', ' '))
    : null;
  if (values?.length) return values.map((value, i) => ({ value: +value, label: meanings?.[i] || String(value) }));

  const byVariable = layer.summaries?.classes_by_variable?.[layer.activeVar];
  const generic = layer.variables?.length === 1 ? layer.summaries?.classes : null;
  const declared = Array.isArray(byVariable) ? byVariable : generic;
  if (!Array.isArray(declared)) return null;
  return declared.map(item => typeof item === 'object'
    ? { value: +(item.value ?? item.id), label: String(item.name ?? item.label ?? item.value), color: item.color }
    : { value: +item, label: String(item) }
  ).filter(c => Number.isFinite(c.value));
}

function automaticColormap(layer) {
  /* Declared classes are categories, not magnitudes: a sequential ramp makes
     neighbouring classes indistinguishable. */
  const classes = metadataClasses(layer);
  if (classes?.length > 2) return classes.length <= 10 ? 'tab10' : 'tab20';
  const name = `${layer.activeVar} ${layer.label} ${layer.units}`.toLowerCase();
  if (/(uncertainty|standard deviation|std|error)/.test(name)) return 'blues';
  if (/(loss|deforest|degrad|disturb|change)/.test(name)) return 'ylorbr';
  if (/(year|age)/.test(name)) return 'viridis';
  if (/(height|biomass|carbon|cover|forest)/.test(name)) return 'greens';
  return 'viridis';
}

/* Prefer declared STAC/Zarr ranges over service estimates, so the legend is
   stable across locations, zoom levels and pyramid resolutions. */
function applyRange(layer, minmax, attrs) {
  let lo = null, hi = null;
  const band = stacBand(layer);
  const stats = band?.statistics || {};
  const pair = Array.isArray(minmax) ? (Array.isArray(minmax[0]) ? minmax[0] : minmax) : null;
  if (attrs && Number.isFinite(+attrs.valid_min) && Number.isFinite(+attrs.valid_max)) {
    lo = +attrs.valid_min; hi = +attrs.valid_max;
  } else if (Number.isFinite(+(stats.minimum ?? stats.min)) && Number.isFinite(+(stats.maximum ?? stats.max))) {
    lo = +(stats.minimum ?? stats.min); hi = +(stats.maximum ?? stats.max);
  } else if (pair && pair.length >= 2 && Number.isFinite(+pair[0]) && Number.isFinite(+pair[1])) {
    lo = +pair[0]; hi = +pair[1];
  }
  if (lo === null || hi === null || hi <= lo) {
    /* Start from the neutral default, not the previous variable's range
       (switching tree_cover -> loss_year used to keep 0–100). */
    layer.rMin = 0; layer.rMax = 1;
    layer.rangeKnown = false; layer.rangeSource = 'manual'; return;
  }
  layer.rMin = lo; layer.rMax = hi; layer.rangeKnown = true;
  layer.rangeSource = (attrs && Number.isFinite(+attrs.valid_min)) ? 'declared'
    : (Number.isFinite(+(stats.minimum ?? stats.min)) ? 'stac' : 'tilejson');
}

/* Integer variables spanning a handful of values (masks, class rasters) read
   far better as discrete swatches than as a continuous ramp. */
function buildClasses(layer) {
  /* A class swatch must show the colour the tile actually gets, which is the
     LUT sampled at the value's position in the rescale range — not at the
     class's position in the list. */
  const span = layer.rMax - layer.rMin;
  const at = v => colorAt(layer.colormap, span > 0 ? (v - layer.rMin) / span : 0);

  const declared = metadataClasses(layer);
  if (declared?.length)
    return declared.map(item => ({ ...item, color: item.color || at(item.value) }));

  const isInt = /^u?int|^bool/i.test(layer.dtype || '');
  if (!layer.rangeKnown || !isInt || span < 1 || span > 11) return null;
  return Array.from({ length: span + 1 }, (_, i) => ({
    value: layer.rMin + i,
    label: String(layer.rMin + i),
    color: at(layer.rMin + i),
  }));
}

async function activateLayer(col, { slot } = {}) {
  const zarrIndex = Math.min(col.zarrIndex ?? 0, col.zarrs.length - 1);
  const zarr = col.zarrs[zarrIndex];
  const zarrUrl = zarr.href;
  const layer = {
    id: col.id,
    title: col.title,
    zarrUrl,
    variables: ['data'],
    activeVar: 'data',
    label: '', units: '', attrs: {}, dtype: '',
    width: 0, height: 0, zoomFloor: null,
    colormap: 'greens',
    colormapManual: false,
    rMin: 0, rMax: 1, rangeKnown: false, classes: null,
    opacity: 0.9,
    dimInfo: null, dimValue: 0, extraDims: null,
    nativeMinZoom: 4, minZoom: 4, maxZoom: 18,
    bounds: col.bbox,
    summaries: col.summaries || {},
    rasterBands: zarr.rasterBands || [],
    zarrIndex,
    resolution: col.zarrs.length > 1 ? zarr.resLabel : '',
    slot: slot ?? freeColorSlot(),
    color: null,          // set from slot below
    footprintLayer: null, footprintLabel: null, leafletLayer: null,
    pyramidUrl: null, numPyramidLevels: 0, _lastPyramidLevel: null,
  };

  layer.color = LAYER_COLORS[layer.slot];
  layer.variables = await fetchVariables(zarrUrl, col.variables);
  layer.activeVar = layer.variables[0];
  layer.label = layer.activeVar;

  if (S.tiOk) {
    // The catalog lists the pyramid as an overview asset; older catalogs
    // only by name (<store>_pyramid.zarr)
    const pyramidUrl = zarr.overview || zarrUrl.replace(/\.zarr\/?$/, '_pyramid.zarr');
    const numLevels = await completePyramidLevels(pyramidUrl);
    if (numLevels) {                // otherwise no (finished) pyramid for this dataset
      layer.pyramidUrl = pyramidUrl;
      layer.numPyramidLevels = numLevels + 1;
      layer.minZoom = 0;
    }

    await fetchVariableMeta(layer);
  }

  S.layers.set(col.id, layer);
  addLeafletLayer(layer);
  updateFootprint(layer);
  if (S.autoZoom) zoomToLayer(layer);
}

function parseDimInfo(info) {
  const spatial = new Set(['x','y','latitude','longitude','lat','lon']);
  const dims = (info.dimensions || []).filter(d => !spatial.has(d));
  if (!dims.length) return null;
  const bands = info.band_descriptions || [];
  if (bands.length < 2) return null;
  const labels = bands.map(([, l]) => l).filter(Boolean);
  const isTimelike = labels.some(l => /^\d{4}/.test(l));
  const isCategorical = !isTimelike && labels.some(l => l && !/^\d+$/.test(l) && !/^b\d+$/.test(l));
  return { name: dims[0], type: isCategorical ? 'categorical' : 'index', values: labels, length: bands.length };
}

/* Dates as people read them: "2010" for annual data, "2010-06" for monthly,
   "2010-06-15" otherwise, instead of 2010-01-01T00:00:00.000000000. Only for
   display: requests keep the full value. */
function dimLabel(value, values = [value]) {
  const iso = v => String(v).match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$/);
  const m = iso(value);
  if (!m) return String(value);
  const all = values.map(iso).filter(Boolean);
  if (all.every(d => d[2] === '01' && d[3] === '01')) return m[1];
  if (all.every(d => d[3] === '01')) return `${m[1]}-${m[2]}`;
  return `${m[1]}-${m[2]}-${m[3]}`;
}

/* titiler.xarray exposes only `sel` — there is no `isel`. An unrecognised
   query param is silently dropped, which leaves every band of the extra
   dimension loaded (and renders the wrong slice). `sel` selects by coordinate
   VALUE, so send the band label rather than an integer index. */
function selParam(layer) {
  const di = layer.dimInfo;
  if (!di || di.length < 2) return null;
  const label = di.values[layer.dimValue];
  if (label == null) return null;
  const s = String(label);
  if (/^b\d+$/.test(s) || s.includes('::')) return null;   // no real coordinate to select on
  const timeLike = /^\d{4}-\d{2}-\d{2}/.test(s);
  return `${di.name}=${timeLike ? 'nearest::' : ''}${s}`;
}

function extraSels(layer) {
  return (layer.extraDims || []).map(d => {
    const v = String(d.values[d.index]);
    return `${d.name}=${/^\d{4}-\d{2}-\d{2}/.test(v) ? 'nearest::' : ''}${v}`;
  });
}

/* Every `sel` a request needs: pinned extra dimensions plus the slider's. */
function selParams(layer) {
  return [...extraSels(layer), selParam(layer)].filter(Boolean);
}

function buildTileUrl(layer, zoom) {
  const zarr = getEffectiveZarrUrl(layer, zoom ?? S.map.getZoom());
  /* No `nodata` override: xarray already decodes the zarr fill_value to NaN,
     and passing a value here calls write_nodata() on top of that — which
     un-masks the NaNs and renders the fill as if it were real data. */
  const p = new URLSearchParams({
    url: zarr,
    variable: layer.activeVar,
    rescale: `${layer.rMin},${layer.rMax}`,
    colormap_name: layer.colormap,
  });
  for (const s of selParams(layer)) p.append('sel', s);
  /* Without an extension TiTiler sends JPEG for gap-free tiles; its artefacts
     smear class colours into shades no legend swatch shows. */
  const ext = layer.classes ? '.png' : '';
  return `${S.tiTiler}/tiles/WebMercatorQuad/{z}/{x}/{y}${ext}?${p}`;
}

function addLeafletLayer(layer) {
  const zoom = S.map.getZoom();
  layer._lastPyramidLevel = getPyramidLevel(layer, zoom);
  const opts = {
    opacity: layer.opacity, minZoom: layer.minZoom, maxZoom: 22, tileSize: 256,
  };
  /* Tiles that miss the data entirely still cost a full server-side read, and
     for projected grids a bbox outside the CRS's area of use reprojects to
     something enormous. Let Leaflet skip them. */
  const bb = boundsToLatLng(layer.bounds);
  if (bb) opts.bounds = bb;
  layer.leafletLayer = L.tileLayer(buildTileUrl(layer, zoom), opts).addTo(S.map);
}

/* Leaflet's redraw (run by setUrl) clamps only to the native zoom range, not
   to minZoom, so redrawing below the layer's zoom floor requested tiles far
   too large to read (HTTP 500 on every variable switch at low zoom). Below
   the floor just swap the URL; Leaflet uses it once the map zooms in. */
function setTileUrl(layer, zoom) {
  layer.leafletLayer.setUrl(buildTileUrl(layer, zoom), zoom < layer.minZoom);
}

async function updateLeafletLayer(id, { refreshMeta = false } = {}) {
  const layer = S.layers.get(id);
  if (!layer?.leafletLayer) return;
  if (refreshMeta) {
    await fetchVariableMeta(layer).catch(() => {});
    renderLayerPanel();
  } else {
    layer.classes = buildClasses(layer);
  }
  const zoom = S.map.getZoom();
  layer._lastPyramidLevel = getPyramidLevel(layer, zoom);
  layer.leafletLayer.options.minZoom = layer.minZoom;
  const bb = boundsToLatLng(layer.bounds);
  if (bb) layer.leafletLayer.options.bounds = bb;
  setTileUrl(layer, zoom);
  layer.leafletLayer.setOpacity(layer.opacity);
  updateFootprint(layer);
  renderLegend();
  if (S.view === 'download') refreshDownload();
}

function removeLayer(id) {
  const layer = S.layers.get(id);
  if (!layer) return;
  [layer.leafletLayer, layer.footprintLayer, layer.footprintLabel]
    .forEach(l => { if (l) S.map.removeLayer(l); });
  S.layers.delete(id);
}

/* Reopen a layer on another resolution of the same data, keeping its colour,
   opacity, variable and ramp; the value range is measured again. */
async function switchResolution(layer, index) {
  const col = findCollection(layer.id);
  if (!col || index === layer.zarrIndex) return;
  col.zarrIndex = index;
  const keep = { activeVar: layer.activeVar, opacity: layer.opacity,
                 colormap: layer.colormapManual ? layer.colormap : null };
  const autoZoom = S.autoZoom;
  removeLayer(layer.id);
  S.autoZoom = false;
  try { await activateLayer(col, { slot: layer.slot }); } finally { S.autoZoom = autoZoom; }
  const fresh = S.layers.get(layer.id);
  if (fresh) {
    fresh.opacity = keep.opacity;
    if (keep.colormap) Object.assign(fresh, { colormap: keep.colormap, colormapManual: true });
    if (keep.activeVar !== fresh.activeVar && fresh.variables.includes(keep.activeVar)) {
      fresh.activeVar = fresh.label = keep.activeVar;
      await fetchVariableMeta(fresh);
    }
    updateLeafletLayer(fresh.id);
  }
  renderLayerPanel();
  renderLegend();
  syncLayerCount();
}

/* Footprint outline while the map is zoomed out past the layer's tile floor */
function updateFootprint(layer) {
  const bb = boundsToLatLng(layer.bounds);
  if (!bb) return;
  const show = S.map.getZoom() < layer.minZoom;
  if (show && !layer.footprintLayer) {
    layer.footprintLayer = L.rectangle(bb, {
      color: layer.color, weight: 1.5, fillColor: layer.color,
      fillOpacity: 0.06, dashArray: '5 4', interactive: false,
    }).addTo(S.map);
    layer.footprintLabel = L.marker(bb.getCenter(), {
      interactive: false,
      icon: L.divIcon({
        className: '',
        iconSize: null,
        html: `<div style="font:500 11px/1.35 'Fira Sans',sans-serif;color:${layer.color};
                 background:var(--attrib-bg);padding:4px 8px;border-radius:4px;white-space:nowrap;
                 border:1px solid ${layer.color}55;transform:translate(-50%,-50%)">
                 ${esc(layer.title)}
                 <span style="display:block;font-size:9px;opacity:.7">zoom in to load tiles</span>
               </div>`,
      }),
    }).addTo(S.map);
  } else if (!show && layer.footprintLayer) {
    S.map.removeLayer(layer.footprintLayer);
    S.map.removeLayer(layer.footprintLabel);
    layer.footprintLayer = layer.footprintLabel = null;
  }
}

function syncLayerCount() {
  const n = S.layers.size + S.fp.size;
  const badge = el('rail-badge');
  badge.textContent = n;
  badge.hidden = n === 0;
  syncRail();
  el('map-empty').hidden = n !== 0;
  el('t-fit').disabled = ![...S.layers.values()].some(l => boundsToLatLng(l.bounds));
  if (S.view === 'download') refreshDownload();
}
