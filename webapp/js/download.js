/* EOForestSTAC explorer: Area downloads.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   AREA DOWNLOAD
   Draw or upload an area, size every active layer server-side, then run
   a background job that zips native-resolution cut-outs (POST /download,
   poll GET /download/{id}, fetch /download/{id}/file).
══════════════════════════════════════════════════════════════════ */
const fmtBytes = b => b >= 1e9 ? `${(b / 1e9).toFixed(2)} GB`
  : b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1e3))} kB`;

/* Leaflet longitudes keep counting past ±180 once the map has wrapped. */
function normalizeRing(latlngs) {
  const mean = latlngs.reduce((a, p) => a + p.lng, 0) / latlngs.length;
  const shift = Math.round(mean / 360) * 360;
  const ring = latlngs.map(p => [
    +Math.max(-180, Math.min(180, p.lng - shift)).toFixed(6),
    +Math.max(-90, Math.min(90, p.lat)).toFixed(6),
  ]);
  ring.push([...ring[0]]);
  return ring;
}

function cancelDraw() {
  const d = S.dl.drawing;
  if (!d) return;
  d.off.forEach(([ev, fn]) => S.map.off(ev, fn));
  d.preview?.remove();
  S.map.dragging.enable();
  S.map.doubleClickZoom.enable();
  el('map').classList.remove('dl-drawing');
  document.querySelectorAll('.dl-tool[data-draw]').forEach(b => b.classList.remove('on'));
  /* Let the click that ended the drawing finish before the inspector listens again. */
  setTimeout(() => { S.dl.drawing = null; }, 0);
}

function startDraw(kind) {
  cancelDraw();
  setTimeout(() => {
    const d = { kind, off: [], preview: null, points: [] };
    S.dl.drawing = d;
    el('map').classList.add('dl-drawing');
    document.querySelectorAll(`.dl-tool[data-draw="${kind}"]`).forEach(b => b.classList.add('on'));
    S.map.doubleClickZoom.disable();
    const on = (ev, fn) => { S.map.on(ev, fn); d.off.push([ev, fn]); };

    if (kind === 'rect') {
      S.map.dragging.disable();
      let start = null;
      on('mousedown', e => {
        start = e.latlng;
        d.preview = L.rectangle([start, start], { className: 'dl-shape', interactive: false }).addTo(S.map);
      });
      on('mousemove', e => { if (start) d.preview.setBounds(L.latLngBounds(start, e.latlng)); });
      on('mouseup', e => {
        if (!start) return;
        const b = L.latLngBounds(start, e.latlng);
        cancelDraw();
        if (S.map.latLngToContainerPoint(b.getNorthWest()).distanceTo(S.map.latLngToContainerPoint(b.getSouthEast())) < 6) return;
        setArea({ type: 'Polygon', coordinates: [normalizeRing([b.getSouthWest(), b.getSouthEast(), b.getNorthEast(), b.getNorthWest()])] });
      });
    } else {
      const redraw = cursor => {
        const pts = cursor ? [...d.points, cursor] : d.points;
        if (!d.preview) d.preview = L.polyline(pts, { className: 'dl-shape', interactive: false }).addTo(S.map);
        else d.preview.setLatLngs(pts);
      };
      const finish = () => {
        const pts = d.points;
        cancelDraw();
        if (pts.length >= 3) setArea({ type: 'Polygon', coordinates: [normalizeRing(pts)] });
      };
      on('click', e => {
        const px = S.map.latLngToContainerPoint(e.latlng);
        const near = p => S.map.latLngToContainerPoint(p).distanceTo(px) < 8;
        if (d.points.length >= 3 && near(d.points[0])) return finish();
        if (d.points.length && near(d.points[d.points.length - 1])) return;   // dblclick's 2nd click
        d.points.push(e.latlng);
        redraw();
      });
      on('mousemove', e => { if (d.points.length) redraw(e.latlng); });
      on('dblclick', finish);
    }
  }, 0);
}

function collectPolygons(obj, out = []) {
  if (!obj || typeof obj !== 'object') return out;
  if (obj.type === 'FeatureCollection') (obj.features || []).forEach(f => collectPolygons(f, out));
  else if (obj.type === 'Feature') collectPolygons(obj.geometry, out);
  else if (obj.type === 'GeometryCollection') (obj.geometries || []).forEach(g => collectPolygons(g, out));
  else if (obj.type === 'Polygon') out.push(obj.coordinates);
  else if (obj.type === 'MultiPolygon') out.push(...obj.coordinates);
  return out;
}

async function loadAreaFile(file) {
  try {
    const polygons = collectPolygons(JSON.parse(await file.text()))
      .map(rings => rings.map(ring => ring.map(p => [+p[0], +p[1]])));
    if (!polygons.length) throw new Error('no Polygon or MultiPolygon found');
    setArea(polygons.length === 1
      ? { type: 'Polygon', coordinates: polygons[0] }
      : { type: 'MultiPolygon', coordinates: polygons }, { fit: true });
  } catch (err) {
    el('dl-area-note').textContent = `Could not read ${file.name}: ${err.message}`;
  }
}

function setArea(geometry, { fit = false } = {}) {
  S.dl.shape?.remove();
  S.dl.geometry = geometry;
  S.dl.shape = geometry
    ? L.geoJSON(geometry, { style: () => ({ className: 'dl-shape' }), interactive: false }).addTo(S.map)
    : null;
  if (fit) zoomToArea();
  refreshDownload();
  renderAnalysis();
}

function zoomToArea() {
  if (S.dl.shape) S.map.flyToBounds(S.dl.shape.getBounds(), { padding: [56, 56], maxZoom: 14, duration: 0.9 });
}

function areaLabel(geometry) {
  const b = L.geoJSON(geometry).getBounds();
  const kmPerDeg = 111.32;
  const w = (b.getEast() - b.getWest()) * kmPerDeg * Math.cos(b.getCenter().lat * Math.PI / 180);
  const h = (b.getNorth() - b.getSouth()) * kmPerDeg;
  const kind = geometry.type === 'MultiPolygon' ? `${geometry.coordinates.length} polygons` : 'Area';
  return `${kind} · ${w.toFixed(w < 10 ? 1 : 0)} × ${h.toFixed(h < 10 ? 1 : 0)} km`;
}

function dlLayers() {
  return [...S.layers.values()].filter(l => !S.dl.excluded.has(l.id));
}

function dlPayload(layer) {
  const col = findCollection(layer.id);
  const allTimes = el('dl-alltime').checked;
  const sel = allTimes ? extraSels(layer) : selParams(layer);
  const shown = !allTimes && selParam(layer) ? dimLabel(layer.dimInfo.values[layer.dimValue], layer.dimInfo.values) : '';
  const cite = (col?.links || []).find(l => l.rel === 'cite-as' && /^https?:\/\//i.test(l.href || ''))?.href || '';
  return {
    url: layer.zarrUrl,
    variable: layer.activeVar,
    sel,
    name: [layer.id, layer.activeVar, shown].filter(Boolean).join('_'),
    title: layer.title,
    license: col?.license || '',
    citation: cite,
    providers: (col?.providers || []).map(p => p.name).filter(Boolean).join('; '),
  };
}

async function postJSON(path, body) {
  const r = await fetch(`${S.tiTiler}${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${r.status}`);
  return data;
}

let _dlEstimateTimer, _dlEstimateSeq = 0;
/* What a download would request right now. An estimate is only valid for
   the exact request it sized: layers finish activating, get switched on or
   off, and change time step or variable after the area is drawn. */
function dlSignature() {
  if (!S.dl.geometry) return null;
  return JSON.stringify({ geometry: S.dl.geometry, layers: dlLayers().map(dlPayload) });
}

function refreshDownload({ estimate = true } = {}) {
  const g = S.dl.geometry;
  if (S.dl.estimate && S.dl.estimate.sig !== dlSignature()) S.dl.estimate.stale = true;
  el('dl-area-note').innerHTML = g
    ? `<div class="dl-area"><span>${esc(areaLabel(g))}</span>
         <button class="dl-zoom" id="dl-zoom" title="Zoom the map to the download area">
           <svg class="ico-sm" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16" y2="16"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>Zoom to area
         </button>
         <a class="dl-link" id="dl-clear">clear</a></div>`
    : 'Draw an area on the map or upload a GeoJSON polygon.';
  el('dl-clear')?.addEventListener('click', () => setArea(null));
  el('dl-zoom')?.addEventListener('click', zoomToArea);

  const layers = [...S.layers.values()];
  const est = S.dl.estimate;
  el('dl-layers').innerHTML = layers.length
    ? layers.map(l => {
        const e = est?.byName?.[dlPayload(l).name];
        const meta = !g ? '' : !e ? 'sizing…'
          : e.error ? `<span class="err">${esc(e.error)}</span>`
          : `${fmtBytes(e.bytes)} · ${e.format} · ${Object.values(e.dims).join('×')}`;
        return `<label class="dl-row">
          <input type="checkbox" data-dl="${esc(l.id)}" ${S.dl.excluded.has(l.id) ? '' : 'checked'}>
          <div class="dl-row-main">
            <div class="dl-row-name">${esc(l.title)}</div>
            <div class="dl-row-meta${e?.error ? ' err' : ''}">${esc(l.label || l.activeVar)}${meta ? ` · ${meta}` : ''}</div>
          </div>
        </label>`;
      }).join('')
    : '<div class="set-note" style="margin-top:0">No active layers. Switch datasets on to include them.</div>';
  el('dl-layers').querySelectorAll('input[data-dl]').forEach(inp => inp.addEventListener('change', () => {
    if (inp.checked) S.dl.excluded.delete(inp.dataset.dl); else S.dl.excluded.add(inp.dataset.dl);
    scheduleEstimate();
  }));

  const ok = est && g && est.total > 0 && est.total <= est.max && !est.stale;
  el('dl-go').disabled = !ok || !!S.dl.polling;
  el('dl-code').disabled = !(est && g && est.layers.some(x => !x.error));
  if (g && est && !est.stale) {
    el('dl-summary').textContent = est.total > est.max
      ? `${fmtBytes(est.total)} selected — over the ${fmtBytes(est.max)} limit. Shrink the area, untick layers, or use the Python code.`
      : `${fmtBytes(est.total)} uncompressed (limit ${fmtBytes(est.max)}).`;
  }
  if (estimate && (!est || est.stale)) scheduleEstimate();
}

function scheduleEstimate() {
  if (S.dl.estimate) S.dl.estimate.stale = true;
  clearTimeout(_dlEstimateTimer);
  _dlEstimateTimer = setTimeout(runEstimate, 350);
}

async function runEstimate() {
  const seq = ++_dlEstimateSeq;
  const layers = dlLayers();
  if (!S.dl.geometry || !layers.length) { S.dl.estimate = null; refreshDownload({ estimate: false }); return; }
  const payload = layers.map(dlPayload);
  const sig = dlSignature();
  try {
    const res = await postJSON('/download/estimate', { geometry: S.dl.geometry, layers: payload });
    if (seq !== _dlEstimateSeq) return;
    const byName = Object.fromEntries(res.layers.map(x => [x.name, x]));
    S.dl.estimate = { layers: res.layers, byName, payload, sig, total: res.total_bytes, max: res.max_bytes, stale: false };
  } catch (err) {
    if (seq !== _dlEstimateSeq) return;
    S.dl.estimate = null;
    el('dl-summary').textContent = `Could not size the request: ${err.message}`;
  }
  refreshDownload({ estimate: false });
}

async function startDownload() {
  const est = S.dl.estimate;
  if (!est || est.sig !== dlSignature()) { refreshDownload(); return; }
  const layers = est.payload.filter(p => !est.byName[p.name]?.error);
  el('dl-progress').hidden = false;
  el('dl-bar').style.width = '0%';
  el('dl-status').textContent = 'Starting…';
  try {
    const { id } = await postJSON('/download', { geometry: S.dl.geometry, layers });
    S.dl.polling = id;
    refreshDownload({ estimate: false });
    for (;;) {
      await new Promise(r => setTimeout(r, 1500));
      const st = await fetchJSON(`${S.tiTiler}/download/${id}`, { noStore: true });
      el('dl-bar').style.width = `${Math.round(st.progress * 100)}%`;
      el('dl-status').textContent = `${st.message} · ${Math.round(st.progress * 100)}%`;
      if (st.status === 'error') throw new Error(st.message);
      if (st.status === 'done') {
        /* A synthetic link click seconds after the user's own click is not a
           user gesture, and Firefox silently drops it. Navigating to the
           attachment starts the download without leaving the page; the link
           is the manual fallback. */
        const url = `${S.tiTiler}/download/${id}/file`;
        el('dl-status').innerHTML = `Ready · ${fmtBytes(st.size)} zip. ` +
          `If the download did not start, <a href="${esc(url)}" download>save the zip</a> (kept for 2 hours).`;
        window.location.assign(url);
        break;
      }
    }
  } catch (err) {
    el('dl-status').textContent = `Download failed: ${err.message}`;
  } finally {
    S.dl.polling = null;
    refreshDownload({ estimate: false });
  }
}

const pyStr = v => JSON.stringify(String(v));
const pyVal = v => /^-?\d+(\.\d+)?$/.test(String(v)) ? String(v) : pyStr(v);

function pythonSnippet() {
  const est = S.dl.estimate;
  const lines = [
    '# EOForestSTAC area subset: bounding box of the drawn area, native grid.',
    '# pip install xarray zarr fsspec aiohttp   (rioxarray + shapely for the polygon mask)',
    'import xarray as xr',
    '',
    `area = ${JSON.stringify(S.dl.geometry)}  # EPSG:4326`,
    '',
  ];
  for (const p of est.payload) {
    const e = est.byName[p.name];
    if (!e || e.error) continue;
    lines.push(`# ${p.title}${p.license ? ` (license: ${p.license})` : ''}`);
    if (p.citation) lines.push(`# cite: ${p.citation}`);
    lines.push(`ds = xr.open_zarr(${pyStr(p.url)}, chunks={})`);
    lines.push(`da = ds[${pyStr(p.variable)}]`);
    for (const s of p.sel) {
      const [dim, raw] = [s.slice(0, s.indexOf('=')), s.slice(s.indexOf('=') + 1)];
      const nearest = raw.startsWith('nearest::');
      const value = nearest ? raw.slice(9) : raw;
      lines.push(`da = da.sel(${dim}=${pyVal(value)}${nearest ? ', method="nearest"' : ''})`);
    }
    const [y0, y1] = e.y_range, [x0, x1] = e.x_range;
    lines.push(`da = da.sel(${e.y_dim}=slice(${y0}, ${y1}), ${e.x_dim}=slice(${x0}, ${x1}))  # ${e.crs}`);
    lines.push(`# da = da.rio.write_crs(${pyStr(e.crs)}).rio.clip([area], crs="EPSG:4326")  # polygon mask`);
    lines.push(`da.to_netcdf(${pyStr(`${p.name}.nc`)})`, '');
  }
  return lines.join('\n');
}

/* The page is served over plain http on the intranet, where the async
   clipboard API is unavailable, so show the code with a select-and-copy box. */
function showPythonSnippet() {
  el('dlg-eyebrow').textContent = 'Download';
  el('dlg-title').textContent = 'Python code for this area';
  el('dlg-body').innerHTML = `<p>Reads the same native data straight from the Zarr stores, with no size limit.</p>
    <textarea class="dlg-code" id="dl-snippet" readonly spellcheck="false"></textarea>
    <div class="dl-actions"><button class="btn" id="dl-copy">Copy</button></div>`;
  el('dl-snippet').value = pythonSnippet();
  el('dl-copy').addEventListener('click', async () => {
    const ta = el('dl-snippet');
    ta.select();
    try { await navigator.clipboard.writeText(ta.value); } catch { document.execCommand('copy'); }
    el('dl-copy').textContent = 'Copied';
  });
  el('ds-info-dlg').showModal();
}

function initDownload() {
  document.querySelectorAll('.dl-tool[data-draw]').forEach(b => b.addEventListener('click', () => {
    if (S.dl.drawing?.kind === b.dataset.draw) cancelDraw(); else startDraw(b.dataset.draw);
  }));
  el('dl-file').addEventListener('change', e => { if (e.target.files[0]) loadAreaFile(e.target.files[0]); e.target.value = ''; });
  el('dl-alltime').addEventListener('change', scheduleEstimate);
  el('dl-go').addEventListener('click', startDownload);
  el('dl-code').addEventListener('click', showPythonSnippet);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') cancelDraw(); });
}
