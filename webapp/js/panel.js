/* EOForestSTAC explorer: The active-layers panel (layer cards).
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   ACTIVE LAYERS PANEL
══════════════════════════════════════════════════════════════════ */
function renderLayerPanel() {
  const host = el('view-layers');
  if (!S.layers.size && !S.fp.size) {
    host.innerHTML = '<div class="state">No active layers.<br>Turn one on from <b>Datasets</b>.</div>';
    return;
  }

  host.innerHTML = '<div id="fp-cards"></div>' + [...S.layers.values()].map(layer => {
    const di = layer.dimInfo;
    let dimFld = '';
    if (di && di.length > 1) {
      if (di.type === 'categorical') {
        dimFld = `<div class="fld">
          <div class="fld-lbl"><span>${esc(di.name)}</span></div>
          <select data-id="${esc(layer.id)}" data-prop="dimValue">
            ${di.values.map((v, i) => `<option value="${i}" ${i === layer.dimValue ? 'selected' : ''}>${esc(dimLabel(v, di.values))}</option>`).join('')}
          </select>
        </div>`;
      } else {
        dimFld = `<div class="fld">
          <div class="fld-lbl">
            <span>${esc(di.name)}</span>
            <span class="fld-val" data-role="dimlabel">${esc(di.values[layer.dimValue] != null ? dimLabel(di.values[layer.dimValue], di.values) : `[${layer.dimValue}]`)}</span>
          </div>
          <input type="range" min="0" max="${di.length - 1}" step="1" value="${layer.dimValue}"
                 data-id="${esc(layer.id)}" data-prop="dimValue"
                 data-labels='${esc(JSON.stringify(di.values.map(v => dimLabel(v, di.values))))}'>
        </div>`;
      }
    }

    const extraFld = (layer.extraDims || []).map((d, i) => `<div class="fld">
        <div class="fld-lbl"><span>${esc(d.name)}</span></div>
        <select data-id="${esc(layer.id)}" data-prop="extra:${i}">
          ${d.values.map((v, j) => `<option value="${j}" ${j === d.index ? 'selected' : ''}>${esc(dimLabel(v, d.values))}</option>`).join('')}
        </select>
      </div>`).join('');
    dimFld = extraFld + dimFld;

    const varFld = `<div class="fld">
        <div class="fld-lbl">
          <span>Variable</span>
          <span class="fld-val">${layer.variables.length} available</span>
        </div>
        ${layer.variables.length > 1
          ? `<select data-id="${esc(layer.id)}" data-prop="activeVar">
               ${layer.variables.map(v => `<option value="${esc(v)}" ${v === layer.activeVar ? 'selected' : ''}>${esc(v)}</option>`).join('')}
             </select>`
          : `<div class="fld-static">${esc(layer.activeVar)}</div>`}
        ${layer.label && layer.label !== layer.activeVar
          ? `<div class="fld-hint">${esc(layer.label)}${layer.units ? ` · ${esc(layer.units)}` : ''}</div>` : ''}
      </div>`;

    const zarrs = findCollection(layer.id)?.zarrs || [];
    const resFld = zarrs.length > 1 ? `<div class="fld">
        <div class="fld-lbl"><span>Resolution</span><span class="fld-val">${zarrs.length} available</span></div>
        <select data-id="${esc(layer.id)}" data-prop="resolution">
          ${zarrs.map((z, i) => `<option value="${i}" ${i === layer.zarrIndex ? 'selected' : ''}>${esc(z.resLabel)}${i === 0 ? ' · finest' : ''}</option>`).join('')}
        </select>
      </div>` : '';

    return `<div class="lc" data-card="${esc(layer.id)}">
      <div class="lc-top">
        <span class="lc-swatch" style="background:${layer.color}"></span>
        <span class="lc-name" title="${esc(layer.id)}">${esc(layer.title)}</span>
        <button class="ghost-btn" data-act="zoom" data-id="${esc(layer.id)}" title="Zoom to extent">
          <svg class="ico-sm" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16" y2="16"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
        </button>
        <button class="ghost-btn danger" data-act="remove" data-id="${esc(layer.id)}" title="Remove layer">
          <svg class="ico-sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      ${resFld}
      ${varFld}
      ${dimFld}

      <div class="fld">
        <div class="fld-lbl"><span>Colour ramp</span></div>
        <select data-id="${esc(layer.id)}" data-prop="colormap">
          ${colormapOptions(layer.colormap)}
        </select>
        <div class="cmap-bar" data-role="ramp" style="background:${gradientFor(layer.colormap)}"></div>
        ${!layer.classes && layer.rMin === 0 ? `<label class="fld-check">
          <input type="checkbox" data-id="${esc(layer.id)}" data-prop="showZeros" ${layer.showZeros ? 'checked' : ''}>
          <span>Show zero values</span></label>` : ''}
      </div>

      <div class="fld">
        <div class="fld-lbl">
          <span>Value range${layer.units ? ` (${esc(layer.units)})` : ''}</span>
          <span class="fld-val" data-role="rsrc">${esc(layer.rangeSource || 'manual')}</span>
        </div>
        <div class="two-up">
          <input type="number" step="any" value="${layer.rMin}" data-id="${esc(layer.id)}" data-prop="rMin" aria-label="minimum">
          <input type="number" step="any" value="${layer.rMax}" data-id="${esc(layer.id)}" data-prop="rMax" aria-label="maximum">
        </div>
        ${layer.dataRange
          ? `<button class="range-reset" data-act="reset-range" data-id="${esc(layer.id)}" ${layer.rangeSource === 'manual' ? '' : 'hidden'}>Reset to data range (${fmtNum(layer.dataRange.lo)} – ${fmtNum(layer.dataRange.hi)})</button>`
          : ''}
      </div>

      <div class="fld">
        <div class="fld-lbl">
          <span>Opacity</span>
          <span class="fld-val" data-role="op">${Math.round(layer.opacity * 100)}%</span>
        </div>
        <input type="range" min="0" max="1" step="0.05" value="${layer.opacity}"
               data-id="${esc(layer.id)}" data-prop="opacity">
      </div>

      ${layer.pyramidUrl
        ? `<div class="pyr-note">
             <svg class="ico-sm" viewBox="0 0 24 24"><polygon points="12 3 22 20 2 20 12 3"/></svg>
             overview pyramid · <b>${layer.numPyramidLevels} levels</b>
           </div>`
        : `<div class="pyr-note">
             <svg class="ico-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="13"/><line x1="12" y1="16" x2="12" y2="16"/></svg>
             native only · tiles from z${layer.minZoom}
           </div>
           ${layer.zoomFloor > 3 ? `<div class="fld-hint">
             ${esc(layer.width)}×${esc(layer.height)} px at ${esc(layer.dtype || 'unknown dtype')} exceeds the tile server's
             1&nbsp;GB array limit below z${layer.zoomFloor}. Build overviews to see it globally:
             <code class="hint-code">eoforeststac-pyramids</code>
           </div>` : ''}`}
    </div>`;
  }).join('');
  renderFootprintCards();

  host.querySelectorAll('select[data-prop],input[data-prop]').forEach(ctrl => {
    ctrl.addEventListener(ctrl.type === 'range' ? 'input' : 'change', () => onLayerControl(ctrl));
  });
  host.querySelectorAll('[data-act]').forEach(btn => {
    btn.addEventListener('click', () => {
      const layer = S.layers.get(btn.dataset.id);
      if (!layer) return;
      if (btn.dataset.act === 'zoom') zoomToLayer(layer);
      else if (btn.dataset.act === 'reset-range') {
        if (!layer.dataRange) return;
        layer.rMin = layer.dataRange.lo; layer.rMax = layer.dataRange.hi;
        layer.rangeSource = layer.dataRange.source;
        layer.classes = buildClasses(layer);
        updateLeafletLayer(layer.id); renderLayerPanel(); renderLegend();
      } else {
        removeLayer(layer.id);
        el(`ds-${layer.id}`)?.classList.remove('on');
        const sw = document.querySelector(`.sw input[data-id="${CSS.escape(layer.id)}"]`);
        if (sw) sw.checked = false;
        renderLayerPanel(); renderLegend(); syncLayerCount();
      }
    });
  });
}

let _debounce;
function onLayerControl(ctrl) {
  const { id, prop } = ctrl.dataset;
  const layer = S.layers.get(id);
  if (!layer) return;

  if (prop === 'resolution') { switchResolution(layer, parseInt(ctrl.value, 10)); return; }
  if (prop === 'showZeros') {
    layer.showZeros = ctrl.checked;
    updateLeafletLayer(id);
    renderLegend();
    return;
  }

  if (prop.startsWith('extra:')) {
    const dim = layer.extraDims?.[parseInt(prop.slice(6), 10)];
    if (!dim) return;
    dim.index = parseInt(ctrl.value, 10);
    clearTimeout(_debounce);
    _debounce = setTimeout(() => { updateLeafletLayer(id); renderLegend(); }, 180);
    return;
  }

  let val = ctrl.value;
  if (prop === 'rMin' || prop === 'rMax' || prop === 'opacity') val = parseFloat(val);
  if (prop === 'dimValue') val = parseInt(val, 10);
  if (Number.isNaN(val)) return;
  layer[prop] = val;
  if (prop === 'colormap') layer.colormapManual = true;
  if (prop === 'rMin' || prop === 'rMax') layer.rangeSource = 'manual';
  if (prop === 'activeVar') { layer.colormapManual = false; layer.extraDims = null; }

  /* Null when the control lives in the legend rather than a layer card. */
  const card = ctrl.closest('.lc');
  if (card) {
    if (prop === 'opacity') card.querySelector('[data-role="op"]').textContent = Math.round(val * 100) + '%';
    if (prop === 'rMin' || prop === 'rMax') {
      card.querySelector('[data-role="rsrc"]').textContent = 'manual';
      const reset = card.querySelector('[data-act="reset-range"]');
      if (reset) reset.hidden = false;
    }
    if (prop === 'colormap') {
      /* Class swatches are sampled from the LUT, so rebuild them once it lands. */
      loadLUT(val).then(() => { layer.classes = buildClasses(layer); renderLayerPanel(); renderLegend(); });
      card.querySelector('[data-role="ramp"]').style.background = gradientFor(val);
    }
    if (prop === 'dimValue' && ctrl.type === 'range') {
      const labels = JSON.parse(ctrl.dataset.labels || '[]');
      const out = card.querySelector('[data-role="dimlabel"]');
      if (out) out.textContent = labels[val] ?? `[${val}]`;
    }
  }

  if (prop === 'opacity') { layer.leafletLayer?.setOpacity(val); renderLegend(); return; }

  /* A new variable has its own dims, range and zoom floor — refetch them. */
  const refreshMeta = prop === 'activeVar';
  clearTimeout(_debounce);
  _debounce = setTimeout(() => { updateLeafletLayer(id, { refreshMeta }); renderLegend(); }, refreshMeta ? 0 : 180);
}
