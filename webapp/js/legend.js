/* EOForestSTAC explorer: The legend box with its Legend and Analysis tabs.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   LEGEND
══════════════════════════════════════════════════════════════════ */
const fmtNum = v => {
  if (!Number.isFinite(v)) return '—';
  const a = Math.abs(v);
  if (a !== 0 && (a >= 1e5 || a < 1e-3)) return v.toExponential(1);
  return Number.isInteger(v) ? String(v) : v.toFixed(a < 10 ? 2 : 1);
};

/* The legend box holds two tabs, Legend and Analysis, built once. Each body
   renders on its own: the legend skips rebuilds while one of its dropdowns
   has focus, and that guard must not hold back analysis progress. */
function ensureLegendShell() {
  const leg = el('legend');
  if (el('leg-items')) return syncLegendTabs();
  leg.innerHTML =
    `<div class="leg-head leg-tabs" role="tablist" aria-label="Legend and analysis">
       <button class="leg-tab" role="tab" data-tab="legend">Legend</button>
       <button class="leg-tab" role="tab" data-tab="analysis">Analysis</button>
       <button class="ghost-btn" id="leg-toggle" title="Collapse">
         <svg class="ico-sm" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>
       </button>
     </div>
     <div id="leg-items" role="tabpanel"></div>
     <div id="an-body" role="tabpanel" hidden></div>`;
  leg.querySelectorAll('.leg-tab').forEach(b => b.addEventListener('click', () => {
    S.legTab = b.dataset.tab;
    S.legendOpen = true;
    b.blur();
    renderLegend();
  }));
  el('leg-toggle').addEventListener('click', () => {
    S.legendOpen = !S.legendOpen;
    syncLegendTabs();
  });
  syncLegendTabs();
}

function syncLegendTabs() {
  const leg = el('legend');
  const an = S.legTab === 'analysis';
  leg.classList.toggle('an-open', an && S.legendOpen);
  leg.querySelectorAll('.leg-tab').forEach(b => {
    const on = b.dataset.tab === S.legTab;
    b.classList.toggle('on', on);
    b.setAttribute('aria-selected', String(on));
  });
  el('leg-items').hidden = an || !S.legendOpen;
  el('an-body').hidden = !an || !S.legendOpen;
  el('leg-toggle').style.transform = S.legendOpen ? '' : 'rotate(180deg)';
}

function renderLegend() {
  const leg = el('legend');
  if (!S.layers.size && !S.fp.size) { leg.hidden = true; return; }
  leg.hidden = false;
  ensureLegendShell();
  if (S.legTab === 'analysis') { renderAnalysis(); return; }
  const items = el('leg-items');
  /* Don't rebuild under an open dropdown — zoomend fires while it's in use. */
  if (items.contains(document.activeElement)) return;
  const zoom = S.map?.getZoom() ?? 0;

  items.innerHTML =
    [...S.layers.values()].map(layer => {
      const lvl = getPyramidLevel(layer, zoom);
      const pills = [];
      if (zoom < layer.minZoom)          pills.push(`no tiles below z${layer.minZoom}`);
      else if (layer.pyramidUrl && lvl > 0) pills.push(`overview L${lvl}`);
      for (const d of layer.extraDims || []) pills.push(`${d.name} ${dimLabel(d.values[d.index], d.values)}`);
      if (layer.dimInfo && layer.dimInfo.length > 1)
        pills.push(`${layer.dimInfo.name} ${layer.dimInfo.values[layer.dimValue] != null ? dimLabel(layer.dimInfo.values[layer.dimValue], layer.dimInfo.values) : layer.dimValue}`);

      const body = layer.classes
        ? `<div class="leg-classes">
             ${layer.classes.map(c => `
               <div class="leg-class">
                 <span class="leg-chip" style="background:${c.color}"></span>
                 <span class="leg-class-lbl">${esc(c.label)}</span>
                 <span class="leg-class-val">${fmtNum(Number(c.value))}</span>
               </div>`).join('')}
           </div>`
        : `<div class="leg-ramp" style="background:${gradientFor(layer.colormap)}"></div>
           <div class="leg-ticks">
             ${Array.from({ length: 5 }, (_, i) =>
               `<span>${fmtNum(layer.rMin + (layer.rMax - layer.rMin) * i / 4)}</span>`).join('')}
           </div>`;

      const RANGE_NOTE = {
        measured: 'range measured from data (p2–p98)',
        data:     'range from data statistics (p2–p98)',
        'measured-view': 'range measured in current view (p2–p98)',
        declared: 'range from valid_min / valid_max',
        stac:     'range from STAC statistics',
        tilejson: 'range reported by tile server',
        classes:  'classes from dataset metadata',
        manual:   'range set manually',
      };

      const varPicker = layer.variables.length > 1
        ? `<select class="leg-var" data-id="${esc(layer.id)}" data-prop="activeVar" title="Switch variable">
             ${layer.variables.map(v => `<option value="${esc(v)}" ${v === layer.activeVar ? 'selected' : ''}>${esc(v)}</option>`).join('')}
           </select>`
        : '';

      return `<div class="leg-item">
        <div class="leg-vn">
          <span class="leg-key" style="background:${layer.color}"></span>
          ${esc(layer.label || layer.activeVar)}
        </div>
        <div class="leg-ds">${esc(layer.title)}${layer.resolution ? ` · ${esc(layer.resolution)}` : ''}${layer.units ? ` · ${esc(layer.units)}` : ''}</div>
        ${varPicker}
        ${body}
        <div class="leg-nodata">
          <span class="leg-chip leg-chip-nil"></span>
          <span class="leg-class-lbl">no data</span>
        </div>
        <div class="leg-prov">${esc(RANGE_NOTE[layer.rangeSource] || RANGE_NOTE.manual)}</div>
        ${pills.length ? `<div class="leg-pills">${pills.map(p => `<span class="leg-lvl">${esc(p)}</span>`).join('')}</div>` : ''}
        <div class="leg-pills" data-loading="${esc(layer.id)}" ${layer.loading ? '' : 'hidden'}><span class="leg-lvl">loading tiles…</span></div>
      </div>`;
    }).join('') + footprintLegendItems();

  items.querySelectorAll('.leg-var').forEach(sel => {
    sel.addEventListener('change', () => {
      /* The dropdown has closed by now. Release focus, or the guard above
         keeps skipping every rebuild and the legend stays on the old
         variable (title, ramp and range). */
      sel.blur();
      onLayerControl(sel);
    });
  });
}
