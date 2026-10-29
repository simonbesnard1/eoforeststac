/* EOForestSTAC explorer: Reading the STAC catalog and the datasets panel.
   Classic script sharing globals with the others; index.html loads them in order. */
'use strict';

/* ══════════════════════════════════════════════════════════════════
   STAC CATALOG
══════════════════════════════════════════════════════════════════ */
async function loadCatalog() {
  const host = el('catalog');
  try {
    const root = await fetchJSON(CFG.catalog, { viaTiTiler: true });
    const themes = await Promise.all(
      root.links.filter(l => l.rel === 'child').map(tl => loadTheme(tl, CFG.catalog))
    );
    // Published in one step, footprints included, so nothing sees a
    // catalog without them
    const fpTheme = await loadFootprintSources();
    S.catalog = { themes: [...themes.filter(t => t && t.collections.length), ...(fpTheme ? [fpTheme] : [])] };
    if (!S.catalog.themes.some(t => t.id === S.cat)) S.cat = firstThemeId();
    renderRailCats();
    renderCatalog();
  } catch (e) {
    host.innerHTML = `<div class="state">
      <div style="color:var(--danger);font-weight:500;margin-bottom:6px">Catalog failed to load</div>
      <div style="font-family:var(--mono);font-size:11px">${esc(e.message)}</div>
      ${S.tiOk ? '' : '<div style="margin-top:10px">Start the tile server first — it proxies the S3 request past the browser’s CORS check.</div>'}
    </div>`;
  }
}

async function loadTheme(link, base) {
  try {
    const url = resolveUrl(base, link.href);
    const theme = await fetchJSON(url, { viaTiTiler: true });
    const cols = await Promise.all(
      theme.links.filter(l => l.rel === 'child').map(cl => loadCollection(cl, url))
    );
    return { id: theme.id, title: link.title || theme.title, collections: cols.flat().filter(Boolean) };
  } catch { return null; }
}

/* The newest version's item: item links carry the item's version (older
   catalogs only name it, ..._v<version>.json); versions compare part by part
   (3.10 > 3.9). Older versions stay in the catalog. */
function latestItemLink(links) {
  const ver = l => String(l.version || String(l.href).match(/_v(\d[\d.]*)(?:\/|\.json|$)/)?.[1] || '').split('.').filter(Boolean).map(Number);
  const cmp = (a, b) => {
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      const d = (a[i] ?? -1) - (b[i] ?? -1);
      if (d) return d;
    }
    return 0;
  };
  return links.reduce((best, l) => (cmp(ver(l), ver(best)) > 0 ? l : best), links[links.length - 1]);
}

// Returns one dataset, or for a multi-site product (ALS, ULS, …) an array with
// one dataset per site collection, each tagged with its parent product.
async function loadCollection(link, base) {
  try {
    const url = resolveUrl(base, link.href);
    const col = await fetchJSON(url, { viaTiTiler: true });
    const childLinks = col.links.filter(l => l.rel === 'child');
    if (childLinks.length) {
      const sites = await Promise.all(childLinks.map(cl => loadCollection(cl, url)));
      return sites.flat().filter(Boolean).map(s => ({
        ...s, parent: { id: col.id, title: col.title || col.id },
      }));
    }
    const itemLinks = col.links.filter(l => l.rel === 'item');
    if (!itemLinks.length) return null;
    const latest = latestItemLink(itemLinks);
    const item = await fetchJSON(resolveUrl(url, latest.href), { viaTiTiler: true });
    const assets = item.assets || {};
    const zarrs = Object.entries(assets)
      .filter(([key, a]) => a.href?.endsWith('.zarr') && !(a.roles || []).includes('overview'))
      .map(([key, a]) => {
        const overview = assets[`${key}_overview`];
        return {
          key,
          href: a.href,
          title: a.title || key,
          gsd: Number(a.gsd) || null,
          overview: overview?.href || null,
          overviewLevels: Number(overview?.['overview:levels']) || 0,
          rasterBands: Array.isArray(a['raster:bands']) ? a['raster:bands'] : [],
        };
      });
    if (!zarrs.length) return null;
    // Several stores per item are resolutions of the same data: finest first,
    // so the layer opens at full detail; the layer card offers the others
    zarrs.forEach(z => Object.assign(z, zarrResolution(z)));
    zarrs.sort((a, b) => (a.metres ?? Infinity) - (b.metres ?? Infinity));
    return {
      id: col.id,
      title: col.title || col.id,
      siteLabel: col.site?.label || '',
      version: item.properties?.version || '',
      variables: item.properties?.variables || [],
      summaries: col.summaries || {},
      bbox: Array.isArray(item.bbox) && item.bbox.length >= 4 ? item.bbox.slice(0, 4).map(Number) : null,
      description: col.description || '',
      license: col.license || '',
      providers: Array.isArray(col.providers) ? col.providers : [],
      keywords: Array.isArray(col.keywords) ? col.keywords : [],
      links: col.links || [],
      facts: collectionFacts(col),
      analytics: col['eoforeststac:analytics'] || null,
      startYear: String(col.extent?.temporal?.interval?.[0]?.[0] || '').slice(0, 4),
      zarrs,
    };
  } catch { return null; }
}

/* Resolution of a store: the asset's gsd (metres) when the catalog gives it,
   and its title or key ("0.0833deg", "10m") for the label. */
function zarrResolution(z) {
  const m = String(`${z.title} ${z.key}`).match(/(\d+(?:\.\d+)?)\s*(deg|km|m)\b/i);
  if (!m) return { metres: z.gsd, resLabel: z.title };
  const v = Number(m[1]), unit = m[2].toLowerCase();
  const metres = z.gsd || (unit === 'deg' ? v * 111320 : unit === 'km' ? v * 1000 : v);
  const resLabel = unit === 'deg'
    ? `${v}° (~${metres >= 1000 ? `${Math.round(metres / 1000)} km` : `${Math.round(metres)} m`})`
    : `${v} ${unit}`;
  return { metres, resLabel };
}

/* The one-line "annual 2005–2024 · 100 m · global · ESA CCI" summary, built
   from standard STAC fields so new collections need no UI changes. */
function collectionFacts(col) {
  const s = col.summaries || {};
  const [t0, t1] = (col.extent?.temporal?.interval?.[0] || []).map(d => d ? String(d).slice(0, 4) : '');
  const span = !t0 ? '' : (!t1 || t1 === t0) ? t0 : t1 === '9999' ? `since ${t0}` : `${t0}–${t1}`;
  const cadence = String(s.temporal_resolution?.[0] || '').split(' (')[0];
  return {
    time: !cadence || /^static/i.test(cadence) ? span : [cadence, span].filter(Boolean).join(' '),
    gsd: formatGsd(Number(s['eo:gsd']?.[0])),
    region: regionLabel(col.extent?.spatial?.bbox?.[0]),
    provider: shortProvider(col.providers?.[0]?.name),
  };
}

function formatGsd(m) {
  if (!m) return '';
  if (m >= 100000) return `${+(m / 111320).toFixed(2)}°`;
  if (m >= 1000) return `${+(m / 1000).toFixed(1)} km`;
  return `${+m.toFixed(1)} m`;
}

function regionLabel(b) {
  if (!Array.isArray(b) || b.length < 4) return '';
  const [w, s, e, n] = b.map(Number);
  if (e - w >= 350 && n - s >= 140) return 'global';
  if (e - w >= 350 && Math.max(Math.abs(s), Math.abs(n)) <= 35) return 'pan-tropical';
  if (w >= -40 && e <= 50 && s >= 30 && n <= 75) return 'Europe';
  if (w >= -90 && e <= -30 && s >= -60 && n <= 15) return 'South America';
  return 'regional';
}

/* "ESA Climate Change Initiative (CCI)" → "ESA CCI", "University of Maryland
   (GLAD), …" → "GLAD", "GFZ Helmholtz Centre Potsdam" → "GFZ". */
function shortProvider(name) {
  if (!name) return '';
  const lead = name.match(/^[A-Z]{2,}(?:-[A-Z]{2,})?(?=\s|$)/)?.[0];
  const acro = name.match(/\(([A-Z]{2,8})\)/)?.[1];
  if (lead && acro) return `${lead} ${acro}`;
  return acro || lead || name.split(/\s[–—-]\s|,|\s\(/)[0].trim();
}

/* Resolution already shows in the facts line, so drop a trailing "(30 m)". */
function shortTitle(title) {
  return title.replace(/\s*\((?:[\d.]+\s?(?:m|km|deg|°)|multi-resolution)\)\s*$/i, '');
}

/* ══════════════════════════════════════════════════════════════════
   CATALOG UI
══════════════════════════════════════════════════════════════════ */
function themeInfo(theme) {
  const label = theme?.title || theme?.id || '';
  return CFG.themeInfo[theme?.id] || { label, short: label, cls: 'bc', icon: CFG.themeIconFallback };
}

function firstThemeId() {
  return S.catalog?.themes[0]?.id ?? Object.keys(CFG.themeInfo)[0];
}

function themeOf(colId) {
  return S.catalog?.themes.find(t => t.collections.some(c => c.id === colId)) || null;
}

/* Before the catalog arrives the rail shows the configured themes, so the
   layout doesn't jump; afterwards it follows the catalog's own order. */
function renderRailCats() {
  const themes = S.catalog?.themes?.length ? S.catalog.themes : Object.keys(CFG.themeInfo).map(id => ({ id }));
  const host = el('rail-cats');
  host.innerHTML = themes.map(t => {
    const info = themeInfo(t);
    return `<button class="rail-btn" data-view="data" data-cat="${esc(t.id)}" data-tip="${esc(info.label)}" aria-label="${esc(info.label)}" aria-pressed="false">
      <svg class="ico" viewBox="0 0 24 24">${info.icon}</svg><span class="rail-label">${esc(info.short)}</span>
      <span class="rail-badge" hidden>0</span>
    </button>`;
  }).join('');
  host.querySelectorAll('.rail-btn').forEach(b => {
    b.addEventListener('click', () => showView('data', b.dataset.cat));
  });
  syncRail();
}

function syncRail() {
  document.querySelectorAll('.rail-btn[data-view]').forEach(b => {
    const active = b.dataset.view === S.view && (!b.dataset.cat || b.dataset.cat === S.cat);
    b.classList.toggle('active', active);
    b.setAttribute('aria-pressed', String(active));
  });
  document.querySelectorAll('#rail-cats .rail-btn').forEach(b => {
    const theme = S.catalog?.themes.find(t => t.id === b.dataset.cat);
    const n = theme ? theme.collections.filter(c => S.layers.has(c.id) || S.fp.has(c.id)).length : 0;
    const badge = b.querySelector('.rail-badge');
    badge.textContent = n;
    badge.hidden = n === 0;
  });
}

function renderCatalog() {
  const host = el('catalog');
  if (!S.catalog?.themes?.length) {
    host.innerHTML = '<div class="state">No zarr datasets found in this catalog.</div>';
    return;
  }

  host.innerHTML = S.catalog.themes.map(theme => {
    const info = themeInfo(theme);
    return `<div class="grp" data-grp="${esc(theme.id)}">
      <div class="grp-h"><span class="grp-dot" style="background:var(--${info.cls})"></span>${esc(info.label)}</div>
      <div class="grp-list">${theme.collections.map((col, i) => {
        const prev = theme.collections[i - 1];
        const sub = col.parent && col.parent.id !== prev?.parent?.id
          ? `<div class="ds-sub" data-parent="${esc(col.parent.id)}">${esc(shortTitle(col.parent.title))}</div>`
          : '';
        return sub + renderDatasetRow(col);
      }).join('')}</div>
    </div>`;
  }).join('');

  host.querySelectorAll('.sw input').forEach(inp => {
    inp.addEventListener('change', () => toggleDataset(inp.dataset.id, inp.checked));
  });
  host.querySelectorAll('.ds-zoom').forEach(btn => {
    btn.addEventListener('click', () => {
      const col = findCollection(btn.dataset.id);
      const live = S.layers.get(btn.dataset.id);
      const bounds = live?.bounds || col?.bbox;
      if (bounds) zoomToLayer({ bounds });
    });
  });
  host.querySelectorAll('.ds-cfg').forEach(btn => {
    btn.addEventListener('click', () => {
      openView('layers');
      const card = document.querySelector(`.lc[data-card="${CSS.escape(btn.dataset.id)}"]`);
      card?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      card?.animate(
        [{ background: 'var(--accent-w)' }, { background: 'transparent' }],
        { duration: 900, easing: 'ease-out' }
      );
    });
  });
  host.querySelectorAll('.ds-info').forEach(btn => {
    btn.addEventListener('click', () => openDatasetInfo(btn.dataset.id));
  });
  applyCatalogFilter();
}

function renderDatasetRow(col) {
  const on = S.layers.has(col.id) || S.fp.has(col.id);
  const f = col.facts;
  const facts = col.rowFacts ?? [f.time, f.gsd, f.region, f.provider].filter(Boolean).join(' · ');
  const search = [col.title, col.id, col.parent?.title || '', ...col.providers.map(p => p.name), ...col.keywords].join(' ').toLowerCase();
  const site = col.parent ? `data-parent="${esc(col.parent.id)}"` : '';
  return `<div class="ds ${on ? 'on' : ''} ${col.parent ? 'ds-site' : ''}" id="ds-${esc(col.id)}" data-search="${esc(search)}" ${site}>
    <label class="sw"><input type="checkbox" data-id="${esc(col.id)}" aria-label="Show ${esc(col.title)}" ${on ? 'checked' : ''}><span class="sw-t"></span></label>
    <div class="ds-main">
      <div class="ds-name" title="${esc(col.title)}">${esc(col.siteLabel || shortTitle(col.title))}</div>
      ${facts ? `<div class="ds-facts" title="${esc(facts)}">${esc(facts)}</div>` : ''}
    </div>
    ${col.footprint ? '' : `<button class="ds-zoom" data-id="${esc(col.id)}" title="Zoom to extent" aria-label="Zoom to ${esc(col.title)} extent">
      <svg class="ico-sm" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16" y2="16"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
    </button>`}
    <button class="ds-cfg" data-id="${esc(col.id)}" title="Variable & display settings" aria-label="Display settings for ${esc(col.title)}">
      <svg class="ico-sm" viewBox="0 0 24 24"><line x1="4" y1="8" x2="20" y2="8"/><line x1="4" y1="16" x2="20" y2="16"/><circle cx="9" cy="8" r="2.4"/><circle cx="16" cy="16" r="2.4"/></svg>
    </button>
    <button class="ds-info" data-id="${esc(col.id)}" title="About this dataset" aria-label="About ${esc(col.title)}">
      <svg class="ico-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9.5"/><line x1="12" y1="11" x2="12" y2="16.5"/><line x1="12" y1="7.5" x2="12" y2="7.6"/></svg>
    </button>
  </div>`;
}

function findCollection(id) {
  for (const t of S.catalog?.themes || [])
    for (const c of t.collections)
      if (c.id === id) return c;
  return null;
}

/* Without a query only the selected category is shown (its name is the panel
   title); a query searches every category and labels each group of hits. */
function applyCatalogFilter() {
  const host = el('catalog');
  const q = el('ds-search').value.trim().toLowerCase();
  host.classList.toggle('searching', q !== '');
  let hits = 0;
  host.querySelectorAll('.grp').forEach(grp => {
    let shown = 0;
    grp.querySelectorAll('.ds').forEach(row => {
      const hit = !q || row.dataset.search.includes(q);
      row.hidden = !hit;
      if (hit) shown++;
    });
    grp.querySelectorAll('.ds-sub').forEach(sub => {
      sub.hidden = ![...grp.querySelectorAll('.ds-site')]
        .some(row => row.dataset.parent === sub.dataset.parent && !row.hidden);
    });
    grp.hidden = q ? shown === 0 : grp.dataset.grp !== S.cat;
    if (!grp.hidden) hits += shown;
  });
  host.querySelector('.cat-empty')?.remove();
  if (q && S.catalog?.themes.length && !hits) {
    host.insertAdjacentHTML('beforeend', `<div class="state cat-empty">No datasets match “${esc(q)}”.</div>`);
  }
  syncPanelHead(hits);
}

const LINK_LABELS = { 'cite-as': 'Cite / DOI', about: 'Source', license: 'License terms', describedby: 'Documentation' };

function openDatasetInfo(id) {
  const col = findCollection(id);
  if (!col) return;
  const info = themeInfo(themeOf(id));
  const s = col.summaries;
  const units = s.units_by_variable || {};
  const vars = (Array.isArray(s.variables) && s.variables.length ? s.variables : col.variables)
    .map(v => typeof v === 'string' ? v : v?.name).filter(Boolean)
    .map(v => units[v] ? `${v} (${units[v]})` : v);
  const rows = [
    ['Time', col.facts.time],
    ['Resolution', col.facts.gsd],
    ['Extent', col.facts.region],
    ['Variables', vars.join(', ')],
    ['Provider', col.providers.map(p => p.name).filter(Boolean).join('; ')],
    ['License', col.license],
    ['Version', col.version],
  ].filter(([, v]) => v);
  const links = col.links.filter(l => LINK_LABELS[l.rel] && /^https?:\/\//i.test(l.href || ''));

  el('dlg-eyebrow').innerHTML = `<span class="grp-dot" style="background:var(--${info.cls})"></span>${esc(info.label)}`;
  el('dlg-title').textContent = col.title;
  el('dlg-body').innerHTML =
    (col.description ? `<p>${esc(col.description.trim())}</p>` : '') +
    `<dl class="dlg-facts">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>` +
    (links.length ? `<div class="dlg-links">${links.map(l =>
      `<a href="${esc(l.href)}" target="_blank" rel="noopener noreferrer" title="${esc(l.title || l.href)}">${esc(LINK_LABELS[l.rel])} ↗</a>`
    ).join('')}</div>` : '');
  el('dlg-body').scrollTop = 0;
  el('ds-info-dlg').showModal();
}
