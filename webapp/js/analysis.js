/* EOForestSTAC explorer: The Analysis tab: region statistics, charts, table and CSV.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   ANALYSIS — area-weighted statistics of the active layers in a drawn
   area. Computed by the server with eoforeststac.analytics (the same code
   notebooks use); which variables qualify, and how, comes from each
   collection's eoforeststac:analytics recipe.
══════════════════════════════════════════════════════════════════ */
function analysisTarget(layer) {
  const recipes = findCollection(layer.id)?.analytics;
  if (!recipes || typeof recipes !== 'object') return null;
  const variable = recipes[layer.activeVar] ? layer.activeVar : Object.keys(recipes)[0];
  return variable ? { variable, ...recipes[variable] } : null;
}

function analysisRequest() {
  const layers = [...S.layers.values()]
    .map(layer => ({ layer, target: analysisTarget(layer) }))
    .filter(x => x.target);
  return {
    geometry: S.dl.geometry,
    footprints: [...S.fp.keys()],
    layers: layers.map(({ layer, target }) => {
      const keep = new Set(target.keep_dims || []);
      const options = {};
      for (const k of ['classes', 'exclude', 'years', 'encoding', 'scale'])
        if (target[k] != null) options[k] = target[k];
      return {
        url: layer.zarrUrl, variable: target.variable, kind: target.kind, options,
        sel: extraSels(layer).filter(s => !keep.has(s.split('=')[0])), name: layer.id,
      };
    }),
  };
}

async function startAnalysis() {
  const req = analysisRequest();
  if (!req.geometry || !(req.layers.length || req.footprints.length) || S.an.running) return;
  Object.assign(S.an, { running: true, progress: 0, message: 'Starting…', error: null });
  renderAnalysis();
  try {
    const { footprints, ...rasterReq } = req;
    const shots = Promise.all(footprints.map(id => fpAnalyse(id, req.geometry)));
    let result = { region_area_ha: geodesicAreaHa(req.geometry), layers: [] };
    if (rasterReq.layers.length) {
      const { id } = await postJSON('/analysis', rasterReq);
      for (;;) {
        await new Promise(r => setTimeout(r, 1200));
        const st = await fetchJSON(`${S.tiTiler}/analysis/${id}`, { noStore: true });
        S.an.progress = st.progress || 0;
        S.an.message = st.message || '';
        if (st.status === 'done') { result = st.result; break; }
        if (st.status === 'error') throw new Error(st.message || 'Analysis failed');
        renderAnalysisProgress();
      }
    } else {
      S.an.message = 'Querying footprints…';
      renderAnalysisProgress();
    }
    result.layers = [...(result.layers || []), ...await shots];
    S.an.result = result; S.an.resultSig = JSON.stringify(req);
  } catch (e) {
    S.an.error = e.message;
  }
  S.an.running = false;
  renderAnalysis();
}

/* One entry per analysed layer, in the layer's colour slot. `catKey` is the
   dimension results are split by besides time: the class, the event year, or
   a kept dimension such as GAMI's age class or XU's disturbance type. */
const AN_METRICS = new Set(['mean', 'total', 'cover_area_ha', 'area_ha', 'share', 'label',
  'valid_area_ha', 'region_area_ha', 'coverage', 'time']);

function analysisSeries(result) {
  return (result?.layers || []).map(res => {
    const layer = S.layers.get(res.name) || S.fp.get(res.name);
    const col = findCollection(res.name);
    const recipe = col?.analytics?.[res.variable] || (col?.fp ? { quantity: col.fp.quantity } : {});
    const rows = res.rows || [];
    const catKey = res.kind === 'footprints' ? null
      : res.kind === 'event_year' ? 'year'
      : res.kind === 'class_area' ? 'class'
      : Object.keys(rows[0] || {}).find(k => !AN_METRICS.has(k)) || null;
    const fallbackT = col?.startYear ? Date.UTC(+col.startYear, 0, 1) : null;
    const timeOf = r => r.time != null && r.time !== '' ? Date.parse(String(r.time)) : fallbackT;
    return {
      id: res.name,
      title: col?.title || res.name,
      short: shortSeriesName(col?.title || res.name),
      slot: layer?.slot ?? 0,
      kind: res.kind, variable: res.variable,
      quantity: recipe.quantity || res.variable,
      units: prettyUnit(res.units || ''),
      totalUnits: prettyUnit(recipe.total_units || ''),
      approx: !!res.approximate, res: res.resolution_m, level: res.level,
      error: res.error || null,
      catKey,
      ordinal: !!recipe.ordinal,
      timed: rows.some(r => r.time != null && r.time !== ''),
      rows: rows.map(r => ({ ...r, t: timeOf(r) })),
    };
  });
}

/* Store units as people write them: "m2 ha-1" -> "m²/ha", "Mg C ha-1 yr-1" -> "Mg C/ha/yr". */
function prettyUnit(u) {
  return String(u).trim()
    .replace(/^percent$/i, '%')
    .replace(/\bm2\b/g, 'm²').replace(/\bm3\b/g, 'm³')
    .replace(/\s+(\w+)-1\b/g, '/$1');
}

function shortSeriesName(title) {
  const head = String(title).split(/\s[–—-]\s/)[0].replace(/\s*\(.*?\)\s*$/, '');
  return head.length > 22 ? head.slice(0, 21) + '…' : head;
}

/* What can be plotted for a kind: a value per row, its label and units. */
function analysisMeasures(s) {
  switch (s.kind) {
    case 'density': case 'amount':
      return [{ key: 'mean', label: s.kind === 'amount' ? 'Mean per hectare' : 'Mean density',
                unit: s.kind === 'amount' ? `${s.totalUnits}/ha` : s.units, perHa: s.kind === 'amount' },
              { key: 'total', label: 'Total', unit: s.totalUnits, scale: true }];
    case 'mean':
      return [{ key: 'mean', label: `Mean ${s.quantity.toLowerCase()}`, unit: s.units }];
    case 'footprints':
      return [{ key: 'median', label: 'Median', unit: s.units },
              { key: 'mean', label: 'Mean', unit: s.units },
              { key: 'count', label: 'Footprints', unit: '' }];
    case 'cover': {
      const mean = { key: 'mean', label: 'Mean cover', unit: s.units, fraction: s.units === 'fraction' };
      const area = { key: 'cover_area_ha', label: s.catKey ? 'Area' : 'Equivalent area', unit: 'ha', area: true };
      return s.catKey ? [area, mean] : [mean, area];
    }
    default:
      return [{ key: 'area_ha', label: 'Area', unit: 'ha', area: true },
              { key: 'share', label: 'Share of the area', unit: '%', percent: true }];
  }
}

/* Large values in a readable unit: Mg-based totals as Gg/Tg/Pg, kg via Mg,
   areas in ha or km², anything else with thousand/million/billion. */
function displayScale(unit, maxValue, measure) {
  if (measure?.percent || measure?.fraction) return { f: 0.01, unit: '%' };
  if (measure?.area) return maxValue >= 1e4 ? { f: 100, unit: 'km²' } : { f: 1, unit: 'ha' };
  // Per-hectare amounts in kg read as Mg/ha like every other biomass density
  if (measure?.perHa && /^kg\/ha$/.test(unit)) return { f: 1e3, unit: 'Mg/ha' };
  if (!measure?.scale) return { f: 1, unit };
  let base = unit, f0 = 1;
  if (/^kg\b/.test(base)) { base = base.replace(/^kg/, 'Mg'); f0 = 1e3; }
  if (/^Mg\b/.test(base)) {
    const v = maxValue / f0;
    for (const [f, p] of [[1e9, 'Pg'], [1e6, 'Tg'], [1e3, 'Gg']])
      if (v >= f) return { f: f * f0, unit: base.replace(/^Mg/, p) };
    return { f: f0, unit: base };
  }
  for (const [f, w] of [[1e9, 'billion'], [1e6, 'million'], [1e3, 'thousand']])
    if (maxValue >= f) return { f, unit: `${w} ${unit}` };
  return { f: 1, unit };
}

/* Charts to draw: line-type kinds with the same kind and units share one chart
   (comparing products is the point); everything split by class or year gets
   its own chart. */
function analysisGroups(series) {
  const groups = [];
  const lineKinds = new Set(['density', 'amount', 'mean', 'cover', 'footprints']);
  for (const s of series.filter(x => !x.error && x.rows.length)) {
    if (lineKinds.has(s.kind) && !s.catKey) {
      const key = `line:${s.kind}:${s.units}:${s.totalUnits}`;
      let g = groups.find(x => x.key === key);
      if (!g) groups.push(g = { key, type: 'line', series: [] });
      g.series.push(s);
    } else {
      const type = s.kind === 'event_year' ? 'columns' : s.timed ? 'stack' : 'bars';
      groups.push({ key: `${type}:${s.id}:${s.variable}`, type, series: [s] });
    }
  }
  return groups;
}

function fmtCompact(v) {
  if (!Number.isFinite(v)) return '—';
  const a = Math.abs(v);
  if (a >= 100) return Math.round(v).toLocaleString('en');
  if (a >= 10) return v.toFixed(1);
  return v.toFixed(a >= 1 ? 2 : 3);
}

function niceStep(span, target = 4) {
  const raw = span / target, mag = 10 ** Math.floor(Math.log10(raw || 1));
  return [1, 2, 2.5, 5, 10].map(m => m * mag).find(st => raw <= st) || mag * 10;
}

function renderAnalysis() {
  const host = el('an-body');
  if (!host || S.legTab !== 'analysis') return;
  syncLegendTabs();
  const g = S.dl.geometry;
  const req = analysisRequest();
  const candidates = [...S.layers.values(), ...S.fp.values()];
  const stale = S.an.result && S.an.resultSig !== JSON.stringify(req);

  let html = `<div class="an-head">Analyse forest change</div>`;
  if (!g) {
    html += `
      <p class="an-lede">Draw the area you want to analyse on the map, or upload a polygon.</p>
      <div class="an-draw">
        <button class="btn dl-tool an-tool" data-draw="poly" title="Click vertices; double-click to finish">Draw polygon</button>
        <button class="btn btn-ghost dl-tool an-tool" data-draw="rect" title="Drag on the map">Draw rectangle</button>
      </div>
      <div class="an-or">or</div>
      <label class="an-drop" id="an-drop">
        <input type="file" id="an-file" accept=".geojson,.json,application/geo+json" hidden>
        <span>Drag and drop a <strong>GeoJSON polygon</strong>, or click to upload</span>
        <small>Recommended file size &lt; 1 MB</small>
      </label>`;
  } else {
    html += `
      <div class="an-area">
        <span>${esc(areaLabel(g))}${S.an.result && !stale ? ` · ${fmtCompact(S.an.result.region_area_ha / 100)} km²` : ''}</span>
        <a class="dl-link" id="an-zoom">zoom</a><a class="dl-link" id="an-clear">clear</a>
      </div>
      <div class="an-layers">` +
      (candidates.length ? candidates.map(l => {
        const t = l.src ? { quantity: `${l.src.quantity} per year (areas up to ${S.fpSources?.max_analysis_deg2 ?? 1}°²)` } : analysisTarget(l);
        return `<div class="an-layer${t ? '' : ' off'}">
          <span class="leg-key" style="background:var(--s${l.slot + 1})"></span>
          <span class="an-layer-name">${esc(l.title)}</span>
          <span class="an-layer-meta">${t ? esc(t.quantity || t.variable) : 'no statistics for this product yet'}</span>
        </div>`;
      }).join('') : '<div class="set-note">Switch on a biomass layer (CCI, Saatchi, ALS biomass) to analyse it.</div>') +
      `</div>
      <div class="an-actions">
        <button class="btn" id="an-go" ${!(req.layers.length || req.footprints.length) || S.an.running ? 'disabled' : ''}>
          ${S.an.result && !stale ? 'Analyse again' : 'Analyse'}</button>
      </div>
      <div id="an-progress" ${S.an.running ? '' : 'hidden'}>
        <div class="dl-bar"><span id="an-bar" style="width:${Math.round(S.an.progress * 100)}%"></span></div>
        <div class="set-note" id="an-status" aria-live="polite">${esc(S.an.message)}</div>
      </div>
      ${S.an.error ? `<div class="set-note err">${esc(S.an.error)}</div>` : ''}
      <div id="an-results"></div>`;
  }
  host.innerHTML = html;

  host.querySelectorAll('.an-tool[data-draw]').forEach(b => b.addEventListener('click', () => {
    b.blur();
    if (S.dl.drawing?.kind === b.dataset.draw) cancelDraw(); else startDraw(b.dataset.draw);
  }));
  const file = el('an-file');
  if (file) {
    file.addEventListener('change', e => { if (e.target.files[0]) loadAreaFile(e.target.files[0]); });
    const drop = el('an-drop');
    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', e => {
      e.preventDefault(); drop.classList.remove('over');
      if (e.dataTransfer.files[0]) loadAreaFile(e.dataTransfer.files[0]);
    });
  }
  el('an-clear')?.addEventListener('click', () => { S.an.result = null; setArea(null); });
  el('an-zoom')?.addEventListener('click', zoomToArea);
  el('an-go')?.addEventListener('click', e => { e.currentTarget.blur(); startAnalysis(); });
  if (g && S.an.result) renderAnalysisResults(el('an-results'), S.an.result, stale);
}

function renderAnalysisProgress() {
  const bar = el('an-bar'), status = el('an-status');
  if (bar) bar.style.width = `${Math.round(S.an.progress * 100)}%`;
  if (status) status.textContent = S.an.message;
}

function renderAnalysisResults(host, result, stale) {
  const series = analysisSeries(result);
  const groups = analysisGroups(series);
  S.an.measures = S.an.measures || {};
  host.replaceChildren();
  if (stale) host.insertAdjacentHTML('beforeend',
    '<div class="set-note warn">The area or layers changed since this result — analyse again to update it.</div>');

  for (const g of groups) {
    const lead = g.series[0];
    const measures = analysisMeasures(lead);
    const mKey = S.an.measures[g.key] && measures.some(m => m.key === S.an.measures[g.key]) ? S.an.measures[g.key] : measures[0].key;
    const m = measures.find(x => x.key === mKey);
    const card = document.createElement('section');
    card.className = 'an-card';
    host.append(card);

    if (measures.length > 1) {
      const seg = document.createElement('div');
      seg.className = 'an-seg'; seg.setAttribute('role', 'radiogroup'); seg.setAttribute('aria-label', 'Measure');
      for (const x of measures) {
        const b = document.createElement('button');
        b.textContent = x.label; b.dataset.measure = x.key;
        b.setAttribute('role', 'radio'); b.setAttribute('aria-checked', String(x.key === mKey));
        if (x.key === mKey) b.classList.add('on');
        b.addEventListener('click', () => { S.an.measures[g.key] = x.key; b.blur(); renderAnalysis(); });
        seg.append(b);
      }
      card.append(seg);
    }

    const raw = s => s.rows.map(r => r[m.key]).filter(v => v != null);
    const maxRaw = Math.max(0, ...g.series.flatMap(raw));
    const sc = displayScale(m.unit, maxRaw, m);
    const val = v => (v == null ? null : v / sc.f);
    const title = document.createElement('div');
    title.className = 'an-chart-title';
    const q = lead.quantity.charAt(0).toLowerCase() + lead.quantity.slice(1);
    const lineTitle = lead.kind === 'footprints'
      ? (m.key === 'count' ? 'Footprints per year' : `${m.label} ${q} of the footprints`)
      : { mean: `Mean ${q}`, total: `Total ${q}`, cover_area_ha: `${lead.quantity}, equivalent area` }[m.key] || m.label;
    title.textContent = `${g.type === 'line' ? lineTitle : lead.quantity}${sc.unit ? ` (${sc.unit})` : ''}`;
    card.append(title);
    const legend = document.createElement('div');
    legend.className = 'an-legend';
    card.append(legend);
    const chart = document.createElement('div');
    chart.className = 'an-chart'; chart.tabIndex = 0;
    card.append(chart);

    const single = g.type === 'line' && g.series.every(s => s.rows.filter(r => r[m.key] != null).length <= 1);
    if (single) {
      chart.replaceWith(statTiles(g.series, m, val, sc.unit));
      legend.remove();
    } else if (g.type === 'line') {
      if (g.series.length >= 2) g.series.forEach(s => legend.append(legendItem(`var(--s${s.slot + 1})`, s.short + (s.timed ? '' : ' (single year)'), 'line')));
      else legend.textContent = lead.title, legend.classList.add('single');
      chart.setAttribute('aria-label', `${title.textContent} over time; arrow keys step through years`);
      drawLines(chart, g.series.map(s => ({
        name: s.short, color: `var(--s${s.slot + 1})`,
        points: s.rows.filter(r => r.t != null).map(r => ({ t: r.t, v: val(r[m.key]), coverage: r.coverage })),
      })), sc.unit);
    } else {
      legend.textContent = lead.title; legend.classList.add('single');
      const cats = analysisCategories(lead, m.key);
      if (g.type === 'bars') {
        drawBars(chart, cats.map(c => ({ label: c.label, v: val(c.values.get(null) ?? c.total) })), sc.unit, `var(--s${lead.slot + 1})`);
      } else {
        const colors = new Map(cats.map((c, i) => [c.key,
          c.other ? 'var(--s-other)'
          : g.type === 'columns' ? `var(--s${lead.slot + 1})`
          : lead.ordinal ? `var(--o${i + 1})`
          : `var(--s${i + 1})`]));
        if (g.type === 'stack' && cats.length >= 2) {
          legend.replaceChildren();
          legend.classList.remove('single');
          cats.forEach(c => legend.append(legendItem(colors.get(c.key), c.label, 'box')));
        }
        const times = g.type === 'columns'
          ? cats.map(c => ({ t: Date.UTC(+c.key, 0, 1), label: String(c.key), segments: [{ key: c.key, label: lead.quantity, color: colors.get(c.key), v: val(c.total) }] }))
          : [...new Set(lead.rows.map(r => r.t))].sort((a, b) => a - b).map(t => ({
              t, label: fmtTime(t, lead.rows),
              segments: cats.map(c => ({ key: c.key, label: c.label, color: colors.get(c.key), v: val(c.values.get(t) ?? 0) })),
            }));
        chart.setAttribute('aria-label', `${title.textContent}; arrow keys step through ${g.type === 'columns' ? 'years' : 'time steps'}`);
        drawColumns(chart, times, sc.unit);
      }
    }

    const notes = [];
    if (lead.approx) notes.push(`${lead.short}: approximate, from a ~${fmtCompact(lead.res)} m overview (the area is too large for native resolution).`);
    if (g.type === 'line' && g.series.some(s => s.rows.some(r => r.coverage != null && r.coverage < 0.5)))
      notes.push('Some years cover less than half of the area; see the coverage column in the table.');
    if (g.type !== 'line') notes.push(`${lead.short}: shares are of the drawn area.`);
    if (lead.kind === 'footprints') notes.push('Statistics of the footprints inside the area (quality-filtered), not an area-weighted mean; the table lists counts and quartiles per year.');
    if (notes.length) {
      const n = document.createElement('div');
      n.className = 'an-notes';
      notes.forEach(t => n.append(Object.assign(document.createElement('div'), { textContent: t })));
      card.append(n);
    }
  }

  const errors = series.filter(s => s.error);
  if (errors.length) {
    const n = document.createElement('div');
    n.className = 'an-notes';
    errors.forEach(s => n.append(Object.assign(document.createElement('div'), { textContent: `${s.short}: ${s.error}` })));
    host.append(n);
  }
  if (!groups.length && !errors.length)
    host.append(Object.assign(document.createElement('div'), { className: 'set-note', textContent: 'No valid data in this area.' }));

  const details = document.createElement('details');
  details.className = 'an-table-wrap';
  details.innerHTML = '<summary>Table</summary>';
  details.append(analysisTable(series));
  host.append(details);
  const actions = document.createElement('div');
  actions.className = 'an-actions';
  const csv = Object.assign(document.createElement('button'), { className: 'btn btn-ghost', textContent: 'Download CSV' });
  csv.addEventListener('click', () => downloadAnalysisCsv(series, result));
  actions.append(csv);
  host.append(actions);
}

/* One number per product: the value, its unit, and how much of the area it covers. */
function statTiles(series, m, val, unit) {
  const wrap = document.createElement('div');
  wrap.className = 'an-tiles';
  for (const s of series) {
    const r = s.rows.find(x => x[m.key] != null) || s.rows[0];
    const tile = document.createElement('div');
    tile.className = 'an-tile';
    const label = Object.assign(document.createElement('div'), { className: 'an-tile-label', textContent: s.title });
    const value = Object.assign(document.createElement('div'), { className: 'an-tile-value' });
    value.append(document.createTextNode(r && r[m.key] != null ? fmtCompact(val(r[m.key])) : '—'),
                 Object.assign(document.createElement('span'), { textContent: ` ${unit}` }));
    const meta = Object.assign(document.createElement('div'), { className: 'an-tile-meta',
      textContent: [s.timed && r?.t != null ? fmtTime(r.t, s.rows) : null, r?.coverage != null ? `${Math.round(r.coverage * 100)} % of the area covered` : null].filter(Boolean).join(' · ') });
    tile.append(label, value, meta);
    wrap.append(tile);
  }
  return wrap;
}

function legendItem(color, text, shape) {
  const item = document.createElement('span');
  item.className = 'an-leg-item';
  const key = document.createElement('span');
  key.className = shape === 'box' ? 'an-box-key' : 'an-line-key';
  key.style.background = color;
  item.append(key, document.createTextNode(text));
  return item;
}

/* Categories of a split result, largest first, with more than seven folded
   into "Other"; each has a value per time step (Map keyed by t, or null when
   there is no time) and a total. */
function analysisCategories(s, key) {
  const cats = new Map();
  for (const r of s.rows) {
    const k = r[s.catKey];
    const label = s.kind === 'class_area' ? (r.label ?? String(k)) : String(k);
    if (!cats.has(k)) cats.set(k, { key: k, label, values: new Map(), total: 0 });
    const c = cats.get(k);
    const v = r[key] ?? 0;
    const tk = s.timed ? r.t : null;
    c.values.set(tk, (c.values.get(tk) || 0) + v);
    c.total += v;
  }
  let list = [...cats.values()];
  if (s.kind === 'event_year') return list.sort((a, b) => a.key - b.key);
  if (s.ordinal) return mergeOrdinal(list, 5);       // e.g. age classes: keep order, <= 5 ramp steps
  if (s.catKey !== 'class') return list;
  list.sort((a, b) => b.total - a.total);
  if (list.length > 8) {
    const keep = list.slice(0, 7), rest = list.slice(7);
    const other = { key: '__other', label: `Other (${rest.length} classes)`, values: new Map(), total: 0, other: true };
    for (const c of rest) { other.total += c.total; for (const [t, v] of c.values) other.values.set(t, (other.values.get(t) || 0) + v); }
    list = [...keep, other];
  }
  return list;
}

/* Neighbouring ordered categories merged so at most `n` remain, e.g. twelve
   20-year age classes into five bins labelled "0-60", "60-120", ... */
function mergeOrdinal(list, n) {
  if (list.length <= n) return list;
  const size = Math.ceil(list.length / n), out = [];
  for (let i = 0; i < list.length; i += size) {
    const part = list.slice(i, i + size);
    const first = String(part[0].label), last = String(part[part.length - 1].label);
    const lo = first.split('-')[0];
    // An open-ended last class (">299") makes the bin open-ended too: "180+"
    const label = part.length === 1 ? first
      : /^[>≥]/.test(last) ? `${lo}+`
      : `${lo}-${last.includes('-') ? last.split('-').pop() : last}`;
    const merged = { key: part.map(c => c.key).join('|'), label, values: new Map(), total: 0 };
    for (const c of part) { merged.total += c.total; for (const [t, v] of c.values) merged.values.set(t, (merged.values.get(t) || 0) + v); }
    out.push(merged);
  }
  return out;
}

function fmtTime(t, rows) {
  const d = new Date(t);
  const monthly = new Set(rows.map(r => new Date(r.t).getUTCFullYear())).size < rows.length && rows.some(r => new Date(r.t).getUTCMonth() > 0);
  return monthly ? `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}` : String(d.getUTCFullYear());
}

/* Shared SVG scaffolding: hairline grid, y ticks with one precision. */
function svgPlot(host, W, H, M, ymax, step) {
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('width', W); svg.setAttribute('height', H);
  svg.setAttribute('role', 'img');
  const add = (tag, attrs, parent = svg) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    parent.append(n);
    return n;
  };
  const text = (str, attrs) => { const n = add('text', attrs); n.textContent = str; return n; };
  const ph = H - M.t - M.b;
  const y = v => M.t + ph - (v / ymax) * ph;
  const decimals = Math.max(0, -Math.floor(Math.log10(step) + 1e-9));
  const ticks = [];
  for (let v = 0; v <= ymax + 1e-9; v += step)
    ticks.push([v, v === 0 ? '0' : v.toLocaleString('en', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })]);
  /* The left margin fits the widest tick label (callers read M.l after this),
     so "150,000" is never cut off. */
  const ctx = document.createElement('canvas').getContext('2d');
  ctx.font = `10px ${getComputedStyle(host).getPropertyValue('--mono') || 'monospace'}`;
  M.l = Math.max(M.l, Math.ceil(Math.max(...ticks.map(([, t]) => ctx.measureText(t).width))) + 12);
  for (const [v, label] of ticks) {
    add('line', { x1: M.l, x2: W - M.r, y1: y(v), y2: y(v), class: 'an-grid' });
    text(label, { x: M.l - 6, y: y(v) + 3, class: 'an-tick', 'text-anchor': 'end' });
  }
  host.replaceChildren(svg);
  return { svg, add, text, y, ph };
}

function yScale(vmax) {
  const step = niceStep(vmax || 1);
  return { step, ymax: Math.max(step, Math.ceil(vmax / step) * step) };
}

function attachTooltip(host, svg, W, M, H, xs, rowsAt) {
  const cross = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  for (const [k, v] of Object.entries({ y1: M.t, y2: H - M.b, class: 'an-cross', visibility: 'hidden' })) cross.setAttribute(k, v);
  svg.append(cross);
  const hit = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  for (const [k, v] of Object.entries({ x: M.l, y: M.t, width: W - M.l - M.r, height: H - M.t - M.b, fill: 'transparent' })) hit.setAttribute(k, v);
  svg.append(hit);
  const tip = document.createElement('div');
  tip.className = 'an-tip'; tip.hidden = true;
  host.append(tip);
  let cur = -1;
  const show = i => {
    cur = Math.max(0, Math.min(xs.length - 1, i));
    const cx = xs[cur];
    cross.setAttribute('x1', cx); cross.setAttribute('x2', cx); cross.setAttribute('visibility', 'visible');
    const { head, rows } = rowsAt(cur);
    tip.replaceChildren(Object.assign(document.createElement('div'), { className: 'an-tip-head', textContent: head }));
    for (const r of rows) {
      const row = document.createElement('div');
      row.className = 'an-tip-row';
      const key = document.createElement('span');
      key.className = r.box ? 'an-box-key' : 'an-line-key'; key.style.background = r.color;
      const v = document.createElement('strong'); v.textContent = r.value;
      const name = document.createElement('span'); name.textContent = r.name;
      row.append(key, v, name);
      tip.append(row);
    }
    tip.hidden = false;
    const w = tip.offsetWidth, sx = (svg.getBoundingClientRect().width || W) / W;
    const px = cx * sx, width = host.clientWidth || W;
    tip.style.left = `${Math.max(0, Math.min(width - w, px + 10 + w <= width ? px + 10 : px - w - 10))}px`;
    tip.style.top = `${M.t}px`;
  };
  const hide = () => { cross.setAttribute('visibility', 'hidden'); tip.hidden = true; };
  hit.addEventListener('pointermove', e => {
    const r = svg.getBoundingClientRect();
    const px = (e.clientX - r.left) * (W / r.width);
    let best = 0;
    xs.forEach((x, i) => { if (Math.abs(x - px) < Math.abs(xs[best] - px)) best = i; });
    show(best);
  });
  hit.addEventListener('pointerleave', hide);
  host.addEventListener('keydown', e => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); show(cur < 0 ? 0 : cur + (e.key === 'ArrowRight' ? 1 : -1)); }
    else if (e.key === 'Escape') hide();
  });
  host.addEventListener('blur', hide);
}

/* Lines over time: 2px lines, r 4 dots with a 2px surface ring, direct end
   labels (up to four series, measured so they are never clipped). */
function drawLines(host, series, unit) {
  const W = Math.max(280, host.clientWidth || 340), H = 190;
  const labelled = series.length <= 4 && series.length >= 2;
  const ctx = document.createElement('canvas').getContext('2d');
  ctx.font = `10.5px ${getComputedStyle(host).fontFamily}`;
  const labelW = labelled ? Math.max(0, ...series.map(s => ctx.measureText(s.name).width)) : 0;
  const M = { l: 44, r: labelled ? Math.min(130, Math.ceil(labelW) + 14) : 14, t: 10, b: 24 };
  const pts = series.flatMap(s => s.points.filter(p => p.v != null));
  if (!pts.length) { host.textContent = 'No valid data in this area.'; return; }
  let t0 = Math.min(...pts.map(p => p.t)), t1 = Math.max(...pts.map(p => p.t));
  if (t0 === t1) { t0 -= 365 * 864e5; t1 += 365 * 864e5; }
  const { step, ymax } = yScale(Math.max(...pts.map(p => p.v)));
  const { svg, add, text, y } = svgPlot(host, W, H, M, ymax, step);
  const x = t => M.l + (t - t0) / (t1 - t0) * (W - M.l - M.r);

  const y0 = new Date(t0).getUTCFullYear(), y1 = new Date(t1).getUTCFullYear();
  const every = Math.max(1, Math.ceil((y1 - y0 + 1) / 6));
  for (let yr = y0; yr <= y1; yr++) {
    const t = Date.UTC(yr, 0, 1);
    if (t < t0 || t > t1 || (yr - y0) % every) continue;
    text(String(yr), { x: x(t), y: H - 6, class: 'an-tick', 'text-anchor': 'middle' });
  }
  const ends = [];
  for (const s of series) {
    const sp = s.points.filter(p => p.v != null).sort((a, b) => a.t - b.t);
    if (!sp.length) continue;
    if (sp.length > 1)
      add('path', { d: sp.map((p, i) => `${i ? 'L' : 'M'}${x(p.t)},${y(p.v)}`).join(''), class: 'an-line', stroke: s.color });
    for (const p of sp.length <= 24 ? sp : [sp[sp.length - 1]]) add('circle', { cx: x(p.t), cy: y(p.v), r: 4, class: 'an-dot', fill: s.color });
    const last = sp[sp.length - 1];
    ends.push({ s, x: x(last.t), y: y(last.v) });
  }
  if (labelled) {
    ends.sort((a, b) => a.y - b.y);
    let prev = -Infinity;
    for (const e of ends) { if (e.y - prev < 12) continue; text(e.s.name, { x: e.x + 8, y: e.y + 3, class: 'an-end' }); prev = e.y; }
  }
  const times = [...new Set(pts.map(p => p.t))].sort((a, b) => a - b);
  attachTooltip(host, svg, W, M, H, times.map(x), i => ({
    head: String(new Date(times[i]).getUTCFullYear()),
    rows: series.map(s => {
      const p = s.points.find(q => q.t === times[i]);
      return { color: s.color, value: p && p.v != null ? `${fmtCompact(p.v)} ${unit}` : '—',
               name: s.name + (p?.coverage != null ? ` · ${Math.round(p.coverage * 100)} % covered` : '') };
    }),
  }));
}

/* Columns per time step, stacked by category; <= 24px wide, 2px surface gap
   between segments, 4px rounded top on the column end. */
function drawColumns(host, times, unit) {
  const W = Math.max(280, host.clientWidth || 340), H = 200;
  const M = { l: 44, r: 10, t: 10, b: 24 };
  if (!times.length) { host.textContent = 'No valid data in this area.'; return; }
  const totals = times.map(c => c.segments.reduce((a, s) => a + (s.v || 0), 0));
  const { step, ymax } = yScale(Math.max(...totals));
  const { svg, add, text, y } = svgPlot(host, W, H, M, ymax, step);
  const band = (W - M.l - M.r) / times.length;
  const bw = Math.max(2, Math.min(24, band * 0.7));
  const cx = i => M.l + band * (i + 0.5);
  const every = Math.max(1, Math.ceil(times.length / 6));
  times.forEach((c, i) => {
    if (i % every === 0) text(c.label, { x: cx(i), y: H - 6, class: 'an-tick', 'text-anchor': 'middle' });
    let base = 0;
    const segs = c.segments.filter(s => s.v > 0);
    segs.forEach((s, j) => {
      const top = base + s.v;
      const y0 = y(base), y1 = y(top);
      const gap = j > 0 ? 2 : 0;                       // surface gap between stacked fills
      const h = Math.max(0, y0 - y1 - gap);
      if (h > 0) {
        const xL = cx(i) - bw / 2, isTop = j === segs.length - 1, r = isTop ? Math.min(4, h, bw / 2) : 0;
        const yTop = y1, yBot = y1 + h;
        const d = r
          ? `M${xL},${yBot}V${yTop + r}Q${xL},${yTop} ${xL + r},${yTop}H${xL + bw - r}Q${xL + bw},${yTop} ${xL + bw},${yTop + r}V${yBot}Z`
          : `M${xL},${yBot}V${yTop}H${xL + bw}V${yBot}Z`;
        add('path', { d, fill: s.color, class: 'an-bar' });
      }
      base = top;
    });
  });
  attachTooltip(host, svg, W, M, H, times.map((_, i) => cx(i)), i => {
    const c = times[i];
    const rows = c.segments.filter(s => s.v > 0).reverse().map(s => ({ color: s.color, box: true, value: `${fmtCompact(s.v)} ${unit}`, name: s.label }));
    if (c.segments.length > 1) rows.push({ color: 'transparent', value: `${fmtCompact(totals[i])} ${unit}`, name: 'total' });
    return { head: c.label, rows: rows.length ? rows : [{ color: 'transparent', value: `0 ${unit}`, name: '' }] };
  });
}

/* Horizontal bars, one per category: label on the left, value at the tip. */
function drawBars(host, items, unit, color) {
  const NS = 'http://www.w3.org/2000/svg';
  const list = items.filter(it => it.v != null);
  if (!list.length) { host.textContent = 'No valid data in this area.'; return; }
  const W = Math.max(280, host.clientWidth || 340), row = 24, bh = 14;
  const ctx = document.createElement('canvas').getContext('2d');
  ctx.font = `11px ${getComputedStyle(host).fontFamily}`;
  const labelW = Math.min(150, Math.ceil(Math.max(...list.map(it => ctx.measureText(it.label).width))) + 8);
  const valueW = Math.ceil(Math.max(...list.map(it => ctx.measureText(`${fmtCompact(it.v)} ${unit}`).width))) + 10;
  const H = list.length * row + 6, x0 = labelW, pw = Math.max(40, W - labelW - valueW);
  const vmax = Math.max(...list.map(it => it.v)) || 1;
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.setAttribute('width', W); svg.setAttribute('height', H); svg.setAttribute('role', 'img');
  const add = (tag, attrs) => { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); svg.append(n); return n; };
  list.forEach((it, i) => {
    const yc = 3 + i * row + row / 2;
    const lab = add('text', { x: x0 - 8, y: yc + 3.5, class: 'an-bar-label', 'text-anchor': 'end' });
    let s = it.label;
    while (s.length > 3 && ctx.measureText(s).width > labelW - 8) s = s.slice(0, -2);
    lab.textContent = s === it.label ? s : s.replace(/.$/, '…');
    const title = document.createElementNS(NS, 'title'); title.textContent = it.label; lab.append(title);
    const w = Math.max(it.v > 0 ? 1 : 0, (it.v / vmax) * pw);
    if (w > 0) {
      const r = Math.min(4, w, bh / 2);
      add('path', { d: `M${x0},${yc - bh / 2}H${x0 + w - r}Q${x0 + w},${yc - bh / 2} ${x0 + w},${yc - bh / 2 + r}V${yc + bh / 2 - r}Q${x0 + w},${yc + bh / 2} ${x0 + w - r},${yc + bh / 2}H${x0}Z`, fill: color, class: 'an-bar' });
    }
    add('text', { x: x0 + w + 6, y: yc + 3.5, class: 'an-bar-value' }).textContent = `${fmtCompact(it.v)} ${unit}`;
  });
  host.replaceChildren(svg);
}

/* Every row of every layer, readable: the table view behind the charts. */
function analysisTable(series) {
  const table = document.createElement('table');
  table.className = 'an-table';
  const head = table.createTHead().insertRow();
  for (const h of ['Product', 'When', 'Class / year', 'Value', 'Coverage'])
    head.append(Object.assign(document.createElement('th'), { textContent: h }));
  const body = table.createTBody();
  for (const s of series.filter(x => !x.error)) {
    const m = analysisMeasures(s)[0];
    for (const r of s.rows) {
      if (s.kind === 'footprints') {
        const row = body.insertRow();
        [s.short, fmtTime(r.t, s.rows), `n = ${r.count.toLocaleString('en')}`,
         `${fmtCompact(r.median)} ${s.units} (IQR ${fmtCompact(r.p25)}–${fmtCompact(r.p75)})`, '—']
          .forEach(c => { row.insertCell().textContent = c; });
        continue;
      }
      if (s.kind === 'class_area' || s.kind === 'event_year') { if (!r.area_ha) continue; }
      const cells = [
        s.short,
        r.t != null && s.timed ? fmtTime(r.t, s.rows) : (s.timed ? '—' : 'single'),
        s.catKey ? (s.kind === 'class_area' ? r.label : String(r[s.catKey])) : '',
        r[m.key] != null ? `${fmtCompact(m.percent ? r[m.key] * 100 : r[m.key])} ${m.unit}` : '—',
        s.kind === 'event_year' ? `${fmtCompact((r.share || 0) * 100)} % of area`
          : s.kind === 'class_area' ? `${fmtCompact((r.share || 0) * 100)} % of area`
          : r.coverage != null ? `${Math.round(r.coverage * 100)} %` : '—',
      ];
      const row = body.insertRow();
      cells.forEach(c => { row.insertCell().textContent = c; });
    }
  }
  return table;
}

function downloadAnalysisCsv(series, result) {
  const cols = ['product', 'variable', 'kind', 'time', 'category', 'label', 'mean', 'total', 'cover_area_ha',
                'area_ha', 'share', 'valid_area_ha', 'region_area_ha', 'coverage', 'count', 'median', 'p25', 'p75', 'min', 'max',
                'units', 'resolution_m', 'approximate'];
  const q = v => (v == null ? '' : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  const lines = [cols.join(',')];
  for (const s of series) {
    if (s.error) { lines.push([s.id, s.variable, s.kind, '', '', `error: ${s.error}`].map(q).join(',')); continue; }
    for (const r of s.rows) lines.push([
      s.id, s.variable, s.kind, r.time ?? '', s.catKey ? r[s.catKey] : '', r.label ?? '',
      r.mean, r.total, r.cover_area_ha, r.area_ha, r.share, r.valid_area_ha, r.region_area_ha, r.coverage,
      r.count, r.median, r.p25, r.p75, r.min, r.max,
      s.kind === 'class_area' || s.kind === 'event_year' ? 'ha' : s.units, s.res, s.approx,
    ].map(q).join(','));
  }
  lines.push('', `# area_ha (as drawn),${result.region_area_ha}`, `# area_geojson,${q(JSON.stringify(S.dl.geometry))}`,
             '# computed with eoforeststac.analytics (area-weighted; pixel areas on the WGS84 ellipsoid)');
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(blob), download: `eoforeststac_analysis_${new Date().toISOString().slice(0, 10)}.csv`,
  });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
