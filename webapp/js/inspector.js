/* EOForestSTAC explorer: The pixel inspector (map clicks).
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   PIXEL INSPECTOR
══════════════════════════════════════════════════════════════════ */
async function onMapClick(e) {
  if (S.dl.drawing) return;
  const { lat, lng } = e.latlng;
  const lon = L.Util.wrapNum(lng, [-180, 180], true);
  el('inspector').hidden = false;
  el('ins-xy').textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;

  const shot = fpPick(e.latlng);
  const shotRow = shot ? `<div class="ins-row">
      <span class="ins-k" title="${esc(shot.layer.title)}">${esc(shot.layer.src.quantity)}</span>
      <span class="ins-v">${esc(fmtNum(shot.value))} ${esc(shot.layer.src.units)}</span>
    </div>` : '';
  if (shot) el('ins-xy').textContent = `${shot.lat.toFixed(5)}, ${shot.lon.toFixed(5)} · footprint ${shot.year}`;
  if (!S.layers.size) {
    el('ins-rows').innerHTML = shotRow || `<div class="ins-msg">${S.fp.size ? 'No footprint here; click on a point.' : 'No active layers.'}</div>`;
    return;
  }
  if (!S.tiOk)      { el('ins-rows').innerHTML = shotRow + '<div class="ins-msg">Tile server not connected.</div>'; return; }

  el('ins-rows').innerHTML = '<div class="ins-msg">Querying…</div>';

  const rows = await Promise.all([...S.layers.values()].map(async layer => {
    try {
      const p = new URLSearchParams({ url: layer.zarrUrl, variable: layer.activeVar });
      for (const s of selParams(layer)) p.append('sel', s);
      const r = await fetch(`${S.tiTiler}/point/${lon.toFixed(6)},${lat.toFixed(6)}?${p}`);
      if (!r.ok) return { layer, val: null };
      const d = await r.json();
      return { layer, val: Array.isArray(d.values) ? d.values[0] : d.value };
    } catch { return { layer, val: null }; }
  }));

  el('ins-rows').innerHTML = shotRow + rows.map(({ layer, val }) => {
    const nil = val == null || val === -9999;
    const shown = nil ? 'no data' : (typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(3)) : val);
    return `<div class="ins-row">
      <span class="ins-k" title="${esc(layer.title)}">${esc(layer.activeVar)}</span>
      <span class="ins-v ${nil ? 'nil' : ''}">${esc(shown)}</span>
    </div>`;
  }).join('');
}
