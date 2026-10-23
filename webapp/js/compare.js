/* EOForestSTAC explorer: side-by-side comparison. With two raster layers on,
   the first is shown left of a draggable divider and the second right of
   it (e.g. CCI vs Saatchi biomass, or two GAMI years as two layers).
   Each layer's tile container is clipped at the divider, in layer-pane
   coordinates, and re-clipped whenever the map moves.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

const CMP = { on: false, x: 0.5, clipped: false };   // x: divider position as a share of the map width

function compareLayers() {
  return [...S.layers.values()].filter(l => l.leafletLayer).slice(0, 2);
}

function setCompare(on) {
  CMP.on = on && compareLayers().length === 2;
  el('compare').hidden = !CMP.on;
  const btn = el('t-compare');
  btn.classList.toggle('on', CMP.on);
  btn.setAttribute('aria-pressed', String(CMP.on));
  updateCompare();
}

/* Clip both layers at the divider; without comparison, clear the clips. */
function updateCompare() {
  const btn = el('t-compare');
  if (btn) btn.disabled = compareLayers().length < 2;
  // Runs on every map move: without a comparison there is nothing to do,
  // except clearing the clips once when one ends
  if (!CMP.on && !CMP.clipped) return;
  for (const layer of S.layers.values()) {
    const c = layer.leafletLayer?.getContainer();
    if (c) c.style.clip = '';
  }
  CMP.clipped = false;
  if (CMP.on && compareLayers().length < 2) { setCompare(false); return; }
  if (!CMP.on) return;
  CMP.clipped = true;

  const [left, right] = compareLayers();
  const size = S.map.getSize();
  const nw = S.map.containerPointToLayerPoint([0, 0]);
  const se = S.map.containerPointToLayerPoint(size);
  const cut = nw.x + size.x * CMP.x;
  left.leafletLayer.getContainer().style.clip = `rect(${nw.y}px, ${cut}px, ${se.y}px, ${nw.x}px)`;
  right.leafletLayer.getContainer().style.clip = `rect(${nw.y}px, ${se.x}px, ${se.y}px, ${cut}px)`;

  const bar = el('compare');
  bar.style.left = `${CMP.x * 100}%`;
  el('compare-left').textContent = `◀ ${shortTitle(left.title)}`;
  el('compare-right').textContent = `${shortTitle(right.title)} ▶`;
}

function initCompare() {
  const bar = el('compare'), handle = el('compare-handle');
  let dragging = false;
  const moveTo = clientX => {
    const r = el('map').getBoundingClientRect();
    CMP.x = Math.min(0.95, Math.max(0.05, (clientX - r.left) / r.width));
    updateCompare();
  };
  handle.addEventListener('pointerdown', e => {
    dragging = true; handle.setPointerCapture(e.pointerId); e.preventDefault(); e.stopPropagation();
  });
  handle.addEventListener('pointermove', e => { if (dragging) moveTo(e.clientX); });
  handle.addEventListener('pointerup', () => { dragging = false; });
  // Keyboard: arrows move the divider
  handle.addEventListener('keydown', e => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    CMP.x = Math.min(0.95, Math.max(0.05, CMP.x + (e.key === 'ArrowLeft' ? -0.02 : 0.02)));
    updateCompare();
  });
  // Clicks on the divider must not reach the map (pixel inspector)
  L.DomEvent.disableClickPropagation(bar);
  S.map.on('move zoomend resize', updateCompare);
  el('t-compare').addEventListener('click', e => { e.currentTarget.blur(); setCompare(!CMP.on); });
}
