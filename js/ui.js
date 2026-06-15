/* Entry: filters (button plate + floor indicator), list, states, toasts, wiring. */

import { TYPES, typeIcon, maxStories, state, BUILDINGS, filtered, stars, loadBuildings } from './data.js';
import { initMap, setMapData, setActive, setHover, flyToBuilding, map, setLocationMarker, removeLocationMarker, setUserMarker, removeUserMarker, setMapTheme } from './map.js';
import { initSearch, closePalette, clearToTextMode } from './search.js';
import { initDrawer, openBuilding, showDrawer } from './drawer.js';
import { initResources } from './resources.js';
import { trapFocus } from './focus.js';

const $ = id => document.getElementById(id);

/* ── toasts ── */
function toast(msg, { error = false, action = null } = {}) {
  const t = document.createElement('div');
  t.className = 'toast' + (error ? ' err' : '');
  t.innerHTML = `${error ? '' : '<span class="tick" aria-hidden="true">✓</span>'}<span>${msg}</span>`;
  if (action) {
    const btn = document.createElement('button');
    btn.className = 't-act';
    btn.textContent = action.label;
    btn.onclick = () => { t.remove(); action.fn(); };
    t.appendChild(btn);
  }
  $('toasts').appendChild(t);
  setTimeout(() => t.remove(), action ? 6500 : 3500);
}

/* ── list ── */
function sortCaption() {
  if (state.searchMode === 'location') return `within ${state.radius} mi`;
  if (state.searchMode === 'smart') return 'best match first';
  if (state.userLoc) return 'nearest first';
  return 'top rated first';
}

function skeletons(n = 5) {
  return Array.from({ length: n }, () => `
    <div class="skeleton-card" aria-hidden="true">
      <div class="skel skel-title"></div>
      <div class="skel skel-sub"></div>
      <div class="skel-row"><div class="skel skel-badge"></div><div class="skel skel-badge"></div></div>
    </div>`).join('');
}

/* One set of delegated listeners for the whole list — attached once, so a
   600-card rebuild costs one innerHTML parse instead of thousands of nodes
   plus per-card listeners. */
let listWired = false;
function wireList() {
  if (listWired) return;
  listWired = true;
  const list = $('list');
  const cardOf = e => e.target.closest('.card');
  list.addEventListener('click', e => { const c = cardOf(e); if (c) open(+c.dataset.id); });
  list.addEventListener('keydown', e => {
    const c = cardOf(e);
    if (!c) return;
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(+c.dataset.id); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); c.nextElementSibling?.focus?.(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); c.previousElementSibling?.focus?.(); }
  });
  list.addEventListener('mouseover', e => { const c = cardOf(e); if (c) setHover(+c.dataset.id); });
  list.addEventListener('mouseout', e => {
    const c = cardOf(e);
    if (c && (!e.relatedTarget || !c.contains(e.relatedTarget))) setHover(null);
  });
}

function renderList() {
  wireList();
  const items = filtered();
  const list = $('list');
  $('countN').textContent = items.length;
  $('countCap').textContent = `building${items.length !== 1 ? 's' : ''}`;
  $('countSort').textContent = sortCaption();

  // Refresh cached distances for everything shown — clears stale values when a
  // distance-based mode is left (so the drawer never shows "mi away" for a
  // search you've already cleared).
  items.forEach(b => {
    const real = BUILDINGS.find(x => x.id === b.id);
    if (real) real._dCached = b._d ?? null;
  });

  if (!items.length) {
    list.innerHTML = '';
    list.appendChild(emptyState());
    setMapData(items);
    return;
  }

  list.innerHTML = items.map(b => `
    <div class="card${b.id === state.activeId ? ' active' : ''}" data-id="${b.id}" role="listitem" tabindex="0"
      aria-label="${esc(`${b.name}, ${b.type} in ${b.town}, ${b.stories} stories, ${b.elevators} elevators, rated ${b.rating} of 5`)}">
      <div class="top">
        <div style="min-width:0">
          <div class="bname">${esc(b.name)}</div>
          <div class="type"><span class="ticon" aria-hidden="true">${typeIcon(b.type, 11)}</span>${esc(b.type)}</div>
        </div>
        <div class="stars" aria-hidden="true">${stars(b.rating)}<span class="n led">${Number(b.rating).toFixed(1)}</span></div>
      </div>
      <div class="addr">${esc(b.addr)}</div>
      <div class="meta">
        <span><span class="led">${b.stories}</span><span class="u">stories</span></span>
        <span><span class="led">${b.elevators}</span><span class="u">elev</span></span>
        ${b._d != null ? `<span><span class="led">${b._d.toFixed(1)}</span><span class="u">mi</span></span>` : ''}
      </div>
    </div>`).join('');
  setMapData(items);
}

function emptyState() {
  const el = document.createElement('div');
  el.className = 'state';
  el.innerHTML = `<p>No buildings match.</p>`;
  const actions = document.createElement('div');
  actions.className = 'actions';
  if (state.searchMode === 'location' && state.radius < 25) {
    actions.appendChild(ghost(`Widen to ${Math.min(25, state.radius + 5)} mi`, () => {
      state.radius = Math.min(25, state.radius + 5);
      $('radiusRange').value = state.radius;
      $('radiusVal').textContent = `${state.radius} mi`;
      renderList();
    }));
  }
  if (state.types.size || state.minStories > 0) {
    actions.appendChild(ghost('Clear filters', () => {
      state.types.clear();
      state.minStories = 0;
      syncPlate();
      syncFloors();
      renderList();
    }));
  }
  if (state.q) {
    actions.appendChild(ghost('Clear search', () => $('clearSearch').click()));
  }
  if (actions.children.length) el.appendChild(actions);
  return el;
}

function ghost(label, fn) {
  const b = document.createElement('button');
  b.className = 'ghost-btn';
  b.textContent = label;
  b.onclick = fn;
  return b;
}

function open(id) {
  setActive(id);
  openBuilding(id);
  const b = BUILDINGS.find(x => x.id === id);
  if (b) flyToBuilding(b);
  markActiveCard(id);
}

function markActiveCard(id) {
  document.querySelectorAll('.card.active').forEach(c => c.classList.remove('active'));
  const card = document.querySelector(`.card[data-id="${id}"]`);
  card?.classList.add('active');
}

function scrollCardIntoView(id) {
  const card = document.querySelector(`.card[data-id="${id}"]`);
  if (card) {
    card.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }
}

/* ── signature filters ── */
function buildPlate() {
  const plate = $('typePlate');
  TYPES.forEach(t => {
    const btn = document.createElement('button');
    btn.className = 'pbtn';
    btn.type = 'button';
    btn.setAttribute('aria-pressed', 'false');
    btn.setAttribute('aria-label', `Filter: ${t}`);
    btn.title = t;
    btn.dataset.type = t;
    btn.innerHTML = `<span class="ring" aria-hidden="true">${typeIcon(t, 16)}</span><span class="lbl">${t}</span>`;
    btn.addEventListener('click', () => {
      const on = !state.types.has(t);
      on ? state.types.add(t) : state.types.delete(t);
      btn.setAttribute('aria-pressed', String(on));
      syncFab();
      renderList();
    });
    plate.appendChild(btn);
  });
}

function syncPlate() {
  document.querySelectorAll('.pbtn').forEach(b => {
    b.setAttribute('aria-pressed', String(state.types.has(b.dataset.type)));
  });
  syncFab();
}

/* Stories dropdown: Any + every floor 1..max. Rebuilt once data arrives. */
function buildFloors() {
  const sel = $('storySelect');
  const current = state.minStories;
  sel.innerHTML = '';
  const stops = [0, ...Array.from({ length: maxStories() }, (_, i) => i + 1)];
  for (const n of stops) {
    const opt = document.createElement('option');
    opt.value = n;
    opt.textContent = n === 0 ? 'Any' : String(n);
    sel.appendChild(opt);
  }
  sel.value = stops.includes(current) ? current : 0;
  syncFloors();
}

function syncFloors() {
  const sel = $('storySelect');
  sel.value = state.minStories;
  sel.setAttribute('aria-label', state.exactStories ? 'Exact stories' : 'Minimum stories');
  $('modeMin').setAttribute('aria-checked', String(!state.exactStories));
  $('modeExact').setAttribute('aria-checked', String(state.exactStories));
}

function initFloorMode() {
  $('storySelect').addEventListener('change', e => {
    state.minStories = +e.target.value;
    syncFab();
    renderList();
  });
  const set = exact => {
    state.exactStories = exact;
    syncFloors();
    renderList();
  };
  $('modeMin').addEventListener('click', () => set(false));
  $('modeExact').addEventListener('click', () => set(true));
}

function syncFab() {
  $('filtersFab').classList.toggle('active', state.types.size > 0 || state.minStories > 0);
}

/* ── mode chip + radius ── */
function onModeChange(mode, label, coords) {
  const chip = $('modeChip');
  const radius = $('radiusRow');
  const nearBtn = $('locBtn');
  if (mode === 'location') {
    radius.classList.add('show');
    chip.classList.add('show');
    $('modeText').textContent = label === 'your location' ? `Near you · within ${state.radius} mi` : `Near ${label}`;
    if (coords) {
      if (label === 'your location') { setUserMarker(coords); removeLocationMarker(); }
      else { setLocationMarker(coords); removeUserMarker(); }
      map?.flyTo({ center: [coords.lng, coords.lat], zoom: 12 });
    }
  } else {
    radius.classList.remove('show');
    removeLocationMarker();
    removeUserMarker();
    nearBtn.classList.remove('on');
    nearBtn.setAttribute('aria-pressed', 'false');
    if (mode === 'smart') {
      chip.classList.add('show');
      $('modeText').textContent = 'Best matches for your search';
    } else {
      chip.classList.remove('show');
    }
  }
}

/* ── load ── */
async function load() {
  $('list').innerHTML = skeletons();
  $('countN').textContent = '—';
  $('countCap').textContent = 'loading';
  const { error } = await loadBuildings();
  $('mapShimmer').classList.add('done');
  if (error) {
    const el = document.createElement('div');
    el.className = 'state error';
    el.innerHTML = `<p>Couldn’t load buildings.</p>`;
    const actions = document.createElement('div');
    actions.className = 'actions';
    actions.appendChild(ghost('Retry', load));
    el.appendChild(actions);
    $('list').innerHTML = '';
    $('list').appendChild(el);
    $('countN').textContent = '!';
    $('countCap').textContent = 'connection error';
    return;
  }
  buildFloors();
  renderList();
}

/* ── mobile sheet ── */
function initSheet() {
  const rail = $('rail');
  const handle = $('sheetHandle');
  const order = ['peek', 'half', 'full'];
  let pos = 'peek';
  const apply = () => {
    rail.classList.toggle('half', pos === 'half');
    rail.classList.toggle('full', pos === 'full');
    handle.setAttribute('aria-label', pos === 'full' ? 'Collapse results list' : 'Expand results list');
  };
  handle.addEventListener('click', () => {
    pos = order[(order.indexOf(pos) + 1) % order.length];
    apply();
  });

  let startY = null, startPos = null;
  handle.addEventListener('pointerdown', e => { startY = e.clientY; startPos = pos; });
  window.addEventListener('pointermove', e => {
    if (startY == null) return;
    const dy = e.clientY - startY;
    if (Math.abs(dy) < 40) return;
    const idx = order.indexOf(startPos);
    pos = dy < 0 ? order[Math.min(2, idx + 1)] : order[Math.max(0, idx - 1)];
    apply();
    startY = null;
  });
  window.addEventListener('pointerup', () => { startY = null; });

  /* The rail is CSS-transformed on mobile, so a fixed-position cab inside it
     would anchor to the rail, not the viewport. Move it to <body> while open. */
  const cab = $('cab');
  const cabHome = cab.parentElement;
  trapFocus(cab);
  $('filtersFab').addEventListener('click', () => {
    document.body.appendChild(cab);
    cab.classList.add('open');
    cab.setAttribute('role', 'dialog');
    cab.setAttribute('aria-modal', 'true');
    cab.setAttribute('aria-label', 'Filters');
    $('filtersFab').setAttribute('aria-expanded', 'true');
    $('cabClose').focus();
  });
  const closeCab = () => {
    cab.classList.remove('open');
    cab.removeAttribute('role');
    cab.removeAttribute('aria-modal');
    cab.removeAttribute('aria-label');
    cabHome.insertBefore(cab, cabHome.querySelector('.mode'));
    $('filtersFab').setAttribute('aria-expanded', 'false');
    $('filtersFab').focus();
  };
  $('cabClose').addEventListener('click', closeCab);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && cab.classList.contains('open')) {
      e.stopPropagation();
      closeCab();
    }
  }, true);
}

/* ── calm / full detail theme toggle ── */
function initModeToggle() {
  const btn = $('modeBtn');
  const sync = () => {
    const full = document.documentElement.dataset.mode === 'full';
    btn.classList.toggle('on', full);
    btn.setAttribute('aria-pressed', String(full));
    btn.setAttribute('aria-label', full ? 'Turn off full detail view' : 'Turn on full detail view');
  };
  sync();
  btn.addEventListener('click', () => {
    const next = document.documentElement.dataset.mode === 'full' ? 'calm' : 'full';
    document.documentElement.dataset.mode = next;
    try { localStorage.setItem('liftspot_mode', next); } catch { /* storage unavailable */ }
    sync();
    setMapTheme(next);
  });
}

/* ── boot ── */
function boot() {
  buildPlate();
  buildFloors();   // default 1–20; rebuilt with the real max once data loads
  initFloorMode();
  initSheet();
  initModeToggle();

  try {
    initMap({
      pinClick: id => {
        open(id);
        scrollCardIntoView(id);
      },
      pinHover: id => {
        document.querySelectorAll('.card.hover').forEach(c => c.classList.remove('hover'));
        if (id != null) document.querySelector(`.card[data-id="${id}"]`)?.classList.add('hover');
      },
    });
  } catch {
    // Map can't start (usually WebGL unavailable) — the list still works.
    $('mapShimmer').classList.add('done');
    const err = document.createElement('div');
    err.className = 'state error map-error';
    err.innerHTML = '<p>The map couldn’t start on this device.</p>';
    const actions = document.createElement('div');
    actions.className = 'actions';
    actions.appendChild(ghost('Reload', () => location.reload()));
    err.appendChild(actions);
    document.querySelector('.mapwrap').appendChild(err);
  }

  initSearch(
    { input: $('q'), wrap: $('searchWrap'), palette: $('palette'), clearBtn: $('clearSearch') },
    {
      onModeChange,
      onQueryChange: renderList,
      onPick: b => {
        open(b.id);
        scrollCardIntoView(b.id);
      },
      onGeocodeError: () => toast('Couldn’t search that place. Check your connection and try again.', { error: true }),
    }
  );

  initDrawer(
    {
      drawer: $('drawer'), scrim: $('scrim'), title: $('drawerTitle'), type: $('dType'),
      addr: $('dAddr'), dataStrip: $('dataStrip'), body: $('dBody'), closeBtn: $('closeDrawer'),
    },
    {
      onClose: () => { setActive(null); markActiveCard(-1); },
      onRatingChange: renderList,
      toast,
    }
  );

  initResources({
    btn: $('resBtn'), modal: $('resModal'), scrim: $('resScrim'),
    closeBtn: $('resClose'), body: $('resBody'),
  });

  $('radiusRange').addEventListener('input', e => {
    state.radius = +e.target.value;
    $('radiusVal').textContent = `${state.radius} mi`;
    if (state.searchMode === 'location' && state.locationLabel === 'your location') {
      $('modeText').textContent = `Near you · within ${state.radius} mi`;
    }
    renderList();
  });

  $('modeClear').addEventListener('click', () => {
    $('q').value = '';
    state.q = '';
    $('searchWrap').classList.remove('has-value');
    clearToTextMode();
    renderList();
  });

  $('locBtn').addEventListener('click', () => {
    const btn = $('locBtn');
    // Already on → toggle off: drop the location filter and the "you are here" dot.
    if (btn.getAttribute('aria-pressed') === 'true') {
      state.userLoc = null;
      clearToTextMode();   // resets mode, removes markers, unpresses the button
      renderList();
      return;
    }
    if (!navigator.geolocation) {
      toast('Your browser doesn’t support location. Search a town instead.', { error: true });
      return;
    }
    btn.classList.add('on');
    navigator.geolocation.getCurrentPosition(p => {
      state.userLoc = { lat: p.coords.latitude, lng: p.coords.longitude };
      state.locationCoords = state.userLoc;
      state.searchMode = 'location';
      state.locationLabel = 'your location';
      btn.setAttribute('aria-pressed', 'true');
      onModeChange('location', 'your location', state.userLoc);
      renderList();
      toast('Location found.');
    }, () => {
      btn.classList.remove('on');
      toast('Couldn’t get your location. Allow location access and try again.', { error: true });
    });
  });

  load();
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

boot();
