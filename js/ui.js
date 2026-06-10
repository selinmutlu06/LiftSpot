/* Entry: filters (button plate + floor indicator), list, states, toasts, wiring. */

import { TYPES, TYPE_ICON, FLOOR_STOPS, state, BUILDINGS, filtered, stars, loadBuildings } from './data.js';
import { initMap, setMapData, setActive, setHover, flyToBuilding, map, setLocationMarker, removeLocationMarker, setUserMarker } from './map.js';
import { initSearch, closePalette, clearToTextMode } from './search.js';
import { initDrawer, openBuilding, showDrawer } from './drawer.js';

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
function modeCaption(n) {
  const word = `building${n !== 1 ? 's' : ''}`;
  if (state.searchMode === 'location') return `${word} within ${state.radius} mi`;
  if (state.searchMode === 'smart') return `${word} · best match first`;
  if (state.userLoc) return `${word} · nearest first`;
  return `${word} · top rated first`;
}

function skeletons(n = 5) {
  return Array.from({ length: n }, () => `
    <div class="skeleton-card" aria-hidden="true">
      <div class="skel skel-title"></div>
      <div class="skel skel-sub"></div>
      <div class="skel-row"><div class="skel skel-badge"></div><div class="skel skel-badge"></div></div>
    </div>`).join('');
}

function renderList() {
  const items = filtered();
  const list = $('list');
  $('countN').textContent = items.length;
  $('countCap').textContent = modeCaption(items.length);

  list.innerHTML = '';
  if (!items.length) {
    list.appendChild(emptyState());
    setMapData(items);
    return;
  }

  items.forEach(b => {
    if (b._d != null) {
      const real = BUILDINGS.find(x => x.id === b.id);
      if (real) real._dCached = b._d;
    }
    const el = document.createElement('div');
    el.className = 'card' + (b.id === state.activeId ? ' active' : '');
    el.dataset.id = b.id;
    el.setAttribute('role', 'listitem');
    el.setAttribute('tabindex', '0');
    el.setAttribute('aria-label', `${b.name}, ${b.type} in ${b.town}, ${b.stories} stories, ${b.elevators} elevators, rated ${b.rating} of 5`);
    el.innerHTML = `
      <div class="top">
        <div style="min-width:0">
          <h3>${esc(b.name)}</h3>
          <div class="type">${TYPE_ICON[b.type] || '◉'} ${esc(b.type)}</div>
        </div>
        <div class="stars" aria-hidden="true">${stars(b.rating)}<span class="n led">${Number(b.rating).toFixed(1)}</span></div>
      </div>
      <div class="addr">${esc(b.addr)}</div>
      <div class="meta">
        <span><span class="led">${b.stories}</span><span class="u">stories</span></span>
        <span><span class="led">${b.elevators}</span><span class="u">elev</span></span>
        ${b._d != null ? `<span><span class="led">${b._d.toFixed(1)}</span><span class="u">mi</span></span>` : ''}
      </div>`;
    const activate = () => { open(b.id); };
    el.addEventListener('click', activate);
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); }
      if (e.key === 'ArrowDown') { e.preventDefault(); el.nextElementSibling?.focus?.(); }
      if (e.key === 'ArrowUp') { e.preventDefault(); el.previousElementSibling?.focus?.(); }
    });
    el.addEventListener('mouseenter', () => setHover(b.id));
    el.addEventListener('mouseleave', () => setHover(null));
    list.appendChild(el);
  });
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
    btn.innerHTML = `<span class="ring" aria-hidden="true">${TYPE_ICON[t] || '◉'}</span><span class="lbl">${t}</span>`;
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

function buildFloors() {
  const strip = $('floorStrip');
  FLOOR_STOPS.forEach(n => {
    const btn = document.createElement('button');
    btn.className = 'fbtn led';
    btn.type = 'button';
    btn.setAttribute('role', 'radio');
    btn.setAttribute('aria-checked', String(n === state.minStories));
    btn.setAttribute('aria-label', n === 0 ? 'Any number of stories' : `${n} or more stories`);
    btn.dataset.n = n;
    btn.textContent = n === 0 ? 'ANY' : String(n);
    btn.addEventListener('click', () => {
      state.minStories = n;
      syncFloors();
      syncFab();
      renderList();
    });
    btn.addEventListener('keydown', e => {
      const idx = FLOOR_STOPS.indexOf(state.minStories);
      let next = null;
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') next = Math.min(FLOOR_STOPS.length - 1, idx + 1);
      if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') next = Math.max(0, idx - 1);
      if (next != null) {
        e.preventDefault();
        state.minStories = FLOOR_STOPS[next];
        syncFloors();
        renderList();
        $('floorStrip').querySelector(`[data-n="${state.minStories}"]`)?.focus();
      }
    });
    strip.appendChild(btn);
  });
}

function syncFloors() {
  document.querySelectorAll('.fbtn').forEach(b => {
    const checked = +b.dataset.n === state.minStories;
    b.setAttribute('aria-checked', String(checked));
    b.tabIndex = checked || (+b.dataset.n === 0 && state.minStories === 0) ? 0 : -1;
  });
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
      if (label === 'your location') setUserMarker(coords);
      else setLocationMarker(coords);
      map?.flyTo({ center: [coords.lng, coords.lat], zoom: 12 });
    }
  } else {
    radius.classList.remove('show');
    removeLocationMarker();
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
  $('filtersFab').addEventListener('click', () => {
    document.body.appendChild(cab);
    cab.classList.add('open');
    $('filtersFab').setAttribute('aria-expanded', 'true');
    $('cabClose').focus();
  });
  $('cabClose').addEventListener('click', () => {
    cab.classList.remove('open');
    cabHome.insertBefore(cab, cabHome.querySelector('.mode'));
    $('filtersFab').setAttribute('aria-expanded', 'false');
    $('filtersFab').focus();
  });
}

/* ── boot ── */
function boot() {
  buildPlate();
  buildFloors();
  initSheet();

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
    if (!navigator.geolocation) {
      toast('Your browser doesn’t support location. Search a town instead.', { error: true });
      return;
    }
    const btn = $('locBtn');
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
