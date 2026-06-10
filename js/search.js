/* Search: command palette dropdown, debounced geocode with cache + rate limit,
   mode switching (text / smart / location). */

import { state, topMatches } from './data.js';

const LI_VIEWBOX = '-74.05,40.45,-71.75,41.15';
const geocodeCache = new Map();          // query -> result | null
let lastNominatimAt = 0;                 // respect 1 req/sec

async function nominatim(url) {
  const wait = Math.max(0, lastNominatimAt + 1050 - Date.now());
  if (wait) await new Promise(r => setTimeout(r, wait));
  lastNominatimAt = Date.now();
  const res = await fetch(url, { headers: { 'Accept-Language': 'en' } });
  return res.json();
}

/* Returns {lat,lng,name} | null on no match. Throws on network failure. */
export async function geocodeQuery(q) {
  const key = q.trim().toLowerCase();
  if (geocodeCache.has(key)) return geocodeCache.get(key);
  const base = `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=us&viewbox=${LI_VIEWBOX}&bounded=1`;
  let data = await nominatim(`${base}&q=${encodeURIComponent(q)}`);
  if (!data.length) data = await nominatim(`${base}&q=${encodeURIComponent(q + ', NY')}`);
  const result = data.length
    ? { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon), name: data[0].display_name.split(',')[0] }
    : null;
  geocodeCache.set(key, result);
  return result;
}

/* ── command palette ── */

let els = null;
let hooks = null;
let palItems = [];
let palIndex = -1;
let debounceTimer = null;
let geocodeSeq = 0;

export function initSearch(domEls, callbacks) {
  els = domEls;       // { input, wrap, palette, clearBtn }
  hooks = callbacks;  // { onModeChange(mode, label, coords), onQueryChange(), onPick(building), onGeocodeError() }

  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      els.input.focus();
      els.input.select();
    }
  });

  els.input.addEventListener('input', onInput);
  els.input.addEventListener('keydown', onKeydown);
  els.input.addEventListener('blur', () => setTimeout(closePalette, 120));
  els.input.addEventListener('focus', () => { if (state.q) renderPalette(); });

  els.clearBtn.addEventListener('click', () => {
    els.input.value = '';
    state.q = '';
    els.wrap.classList.remove('has-value');
    closePalette();
    setMode('text');
    els.input.focus();
    hooks.onQueryChange();
  });
}

function setMode(mode, label = '', coords = null) {
  state.searchMode = mode;
  state.locationLabel = label;
  if (mode === 'location') {
    state.locationCoords = coords;
  } else if (mode === 'text') {
    state.locationCoords = null;
  }
  hooks.onModeChange(mode, label, coords);
}

function onInput(e) {
  state.q = e.target.value;
  els.wrap.classList.toggle('has-value', !!state.q);
  clearTimeout(debounceTimer);
  geocodeSeq++;

  if (!state.q) {
    closePalette();
    setMode('text');
    hooks.onQueryChange();
    return;
  }
  renderPalette();
  hooks.onQueryChange();
  debounceTimer = setTimeout(runGeocode, 300);
}

async function runGeocode() {
  if (!state.q) return;
  const seq = ++geocodeSeq;
  let coords = null;
  try {
    coords = await geocodeQuery(state.q);
  } catch {
    if (seq === geocodeSeq) hooks.onGeocodeError();
    return;
  }
  if (seq !== geocodeSeq || !state.q) return; // stale response
  if (coords) {
    setMode('location', coords.name || state.q, coords);
  } else if (state.q.trim().split(/\s+/).length >= 2) {
    setMode('smart');
  } else {
    setMode('text');
  }
  hooks.onQueryChange();
}

function onKeydown(e) {
  const open = els.palette.classList.contains('open');
  if (e.key === 'ArrowDown' && open) {
    e.preventDefault();
    movePal(1);
  } else if (e.key === 'ArrowUp' && open) {
    e.preventDefault();
    movePal(-1);
  } else if (e.key === 'Enter') {
    if (open && palIndex >= 0 && palItems[palIndex]) {
      e.preventDefault();
      pick(palItems[palIndex]);
    } else {
      clearTimeout(debounceTimer);
      closePalette();
      runGeocode();
    }
  } else if (e.key === 'Escape' && open) {
    e.stopPropagation();
    closePalette();
  }
}

function movePal(dir) {
  if (!palItems.length) return;
  palIndex = (palIndex + dir + palItems.length) % palItems.length;
  renderPaletteRows();
}

function pick(b) {
  closePalette();
  hooks.onPick(b);
}

function renderPalette() {
  palItems = topMatches(state.q, 8);
  palIndex = palItems.length ? 0 : -1;
  if (!palItems.length) { closePalette(); return; }
  els.palette.classList.add('open');
  els.input.setAttribute('aria-expanded', 'true');
  renderPaletteRows();
}

function renderPaletteRows() {
  els.palette.innerHTML = palItems.map((b, i) => `
    <button class="p-row" role="option" id="pal-${b.id}" aria-selected="${i === palIndex}" data-i="${i}">
      <span class="p-main">
        <span class="p-name">${esc(b.name)}</span>
        <span class="p-sub">${esc(b.town)} · ${esc(b.type)}</span>
      </span>
      <span class="p-data led led-lit">${b.stories}F·${b.elevators}E</span>
    </button>`).join('')
    + `<div class="p-hint">↑↓ to browse · <span class="led">↵</span> opens · or finish typing to search places</div>`;
  els.input.setAttribute('aria-activedescendant', palIndex >= 0 ? `pal-${palItems[palIndex].id}` : '');
  els.palette.querySelectorAll('.p-row').forEach(row => {
    row.addEventListener('mousedown', e => e.preventDefault()); // keep input focus
    row.addEventListener('click', () => pick(palItems[+row.dataset.i]));
  });
}

export function closePalette() {
  els.palette.classList.remove('open');
  els.input.setAttribute('aria-expanded', 'false');
  els.input.removeAttribute('aria-activedescendant');
  palIndex = -1;
}

export function clearToTextMode() {
  setMode('text');
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
