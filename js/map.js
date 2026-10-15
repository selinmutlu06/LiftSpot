/* Map: MapLibre init, native clustering, button pins, hover/active sync.
   The basemap and marker colors follow the theme: a light basemap for the
   calm default, the dark "cab" basemap for full detail. Layers are rebuilt
   whenever the style changes, so switching themes never loses the pins.
   "Be the first" buildings (no coverage found anywhere) get amber pins so
   the hunt is visible on the map itself, not just in the list. */

import { unfilmed, covered } from './data.js';

export let map = null;

let onPinClick = null;
let onPinHover = null;
let locationMarker = null;
let userMarker = null;
let hoveredId = null;
let activeId = null;
let lastItems = [];

const STYLES = {
  calm: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  full: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
};
const currentMode = () => (document.documentElement.dataset.mode === 'full' ? 'full' : 'calm');

/* Marker palettes, mirrored from the CSS themes (MapLibre can't read CSS vars). */
const PAINT = {
  calm: {
    clusterFill: '#2f7d68', clusterStroke: '#ffffff', clusterText: '#ffffff',
    pinFill: '#2f7d68', pinActive: '#1f5a4a', pinStroke: '#ffffff', halo: '#2f7d68',
    pinFirst: '#b87d00', pinUnknown: '#9aa5a1',
  },
  full: {
    clusterFill: '#1d2b26', clusterStroke: '#c9ced0', clusterText: '#23a47f',
    pinFill: '#f5f6f4', pinActive: '#23a47f', pinStroke: '#16211d', halo: '#23a47f',
    pinFirst: '#e8a13a', pinUnknown: '#5d6a66',
  },
};

const litState = ['any',
  ['boolean', ['feature-state', 'hover'], false],
  ['boolean', ['feature-state', 'active'], false]];

export function initMap({ pinClick, pinHover }) {
  onPinClick = pinClick;
  onPinHover = pinHover;

  map = new maplibregl.Map({
    container: 'map',
    style: STYLES[currentMode()],
    // Every building from Brooklyn to the East End; refit to the data on load.
    bounds: [[-74.05, 40.55], [-71.9, 41.15]],
    fitBoundsOptions: { padding: 40 },
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'top-right');
  // Keep the canvas filling its box when the layout changes without a window
  // resize event (plugging into a projector, the rail opening on a phone).
  if ('ResizeObserver' in window) new ResizeObserver(() => map.resize()).observe(map.getContainer());

  bindInteractions();
  map.once('load', () => applyPitch(currentMode()));
  // Runs on the first style load and again after every setStyle (theme switch).
  map.on('style.load', addLayers);

  return map;
}

function addLayers() {
  if (!map || map.getSource('buildings')) return;
  const c = PAINT[currentMode()];

  map.addSource('buildings', {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
    promoteId: 'id',
    cluster: true,
    clusterRadius: 34,
    clusterMaxZoom: 11,
  });

  // Full detail: real building heights from the basemap tiles, drawn in 3D
  // under the pins, so the tall towers (the ones with the best elevators)
  // stand out.
  if (currentMode() === 'full' && map.getSource('carto')) {
    map.addLayer({
      id: 'buildings-3d', type: 'fill-extrusion', source: 'carto', 'source-layer': 'building',
      minzoom: 13,
      filter: ['!=', ['get', 'hide_3d'], true],
      paint: {
        'fill-extrusion-color': ['interpolate', ['linear'], ['get', 'render_height'], 0, '#202b27', 60, '#2b3a35', 200, '#3d524b'],
        'fill-extrusion-height': ['get', 'render_height'],
        'fill-extrusion-base': ['get', 'render_min_height'],
        'fill-extrusion-opacity': ['interpolate', ['linear'], ['zoom'], 13, 0, 14, 0.9],
      },
    });
  }

  map.addLayer({
    id: 'clusters', type: 'circle', source: 'buildings',
    filter: ['has', 'point_count'],
    paint: {
      'circle-color': c.clusterFill,
      'circle-radius': ['step', ['get', 'point_count'], 14, 10, 18, 50, 23, 150, 28],
      'circle-stroke-width': 2,
      'circle-stroke-color': c.clusterStroke,
    },
  });
  map.addLayer({
    id: 'cluster-count', type: 'symbol', source: 'buildings',
    filter: ['has', 'point_count'],
    layout: {
      'text-field': ['get', 'point_count_abbreviated'],
      'text-font': ['Open Sans Bold'],
      'text-size': 12,
      'text-allow-overlap': true,
    },
    paint: { 'text-color': c.clusterText },
  });
  map.addLayer({
    id: 'pin-halo', type: 'circle', source: 'buildings',
    filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-radius': currentMode() === 'full'
        ? ['interpolate', ['linear'], ['get', 'st'], 0, 13, 10, 14, 30, 17, 60, 20]
        : 14,
      'circle-color': c.halo,
      'circle-opacity': ['case', litState, 0.3, 0],
    },
  });
  map.addLayer({
    id: 'pins', type: 'circle', source: 'buildings',
    filter: ['!', ['has', 'point_count']],
    paint: {
      // Full detail sizes each pin by its floor count; calm keeps them uniform.
      'circle-radius': currentMode() === 'full'
        ? ['interpolate', ['linear'], ['get', 'st'], 0, 6, 10, 7, 30, 9.5, 60, 12]
        : 7,
      'circle-color': ['case', litState, c.pinActive,
        ['==', ['get', 'cov'], 'first'], c.pinFirst,
        ['==', ['get', 'cov'], 'covered'], c.pinFill,
        c.pinUnknown],
      'circle-stroke-width': 2.5,
      'circle-stroke-color': c.pinStroke,
    },
  });

  // Full detail adds what calm leaves off: each building's name and floor
  // count printed next to its pin once you zoom in to street level.
  if (currentMode() === 'full') {
    map.addLayer({
      id: 'pin-labels', type: 'symbol', source: 'buildings',
      filter: ['!', ['has', 'point_count']],
      minzoom: 13,
      layout: {
        'text-field': ['format',
          ['get', 'name'], { 'font-scale': 1 },
          ['case', ['==', ['get', 'floors'], ''], '', '\n'], {},
          ['get', 'floors'], { 'font-scale': 0.85, 'text-color': c.halo }],
        'text-font': ['Open Sans Bold'],
        'text-size': 11.5,
        'text-anchor': 'left',
        'text-offset': [1.1, 0],
        'text-justify': 'left',
        'text-max-width': 12,
        'text-optional': true,
      },
      paint: { 'text-color': '#e7ebe9', 'text-halo-color': '#0f1714', 'text-halo-width': 1.4 },
    });
  }

  applyData();
}

function bindInteractions() {
  /* One click handler with tolerance: a near-miss within 8px still hits a pin. */
  map.on('click', async e => {
    if (!map.getLayer('pins')) return;
    let f = map.queryRenderedFeatures(e.point, { layers: ['clusters', 'pins'] })[0];
    if (!f) {
      // Bigger forgiving hit area for finger taps than for a mouse cursor.
      const pad = matchMedia('(pointer: coarse)').matches ? 18 : 8;
      const near = map.queryRenderedFeatures(
        [[e.point.x - pad, e.point.y - pad], [e.point.x + pad, e.point.y + pad]],
        { layers: ['pins'] }
      );
      let bestD = Infinity;
      for (const n of near) {
        const p = map.project(n.geometry.coordinates);
        const d = (p.x - e.point.x) ** 2 + (p.y - e.point.y) ** 2;
        if (d < bestD) { bestD = d; f = n; }
      }
    }
    if (!f) return;
    if (f.properties.cluster) {
      const zoom = await map.getSource('buildings').getClusterExpansionZoom(f.properties.cluster_id);
      map.easeTo({ center: f.geometry.coordinates, zoom: zoom + 0.4 });
    } else {
      onPinClick?.(f.properties.id);
    }
  });

  map.on('mousemove', e => {
    if (!map.getLayer('pins')) return;
    const hits = map.queryRenderedFeatures(e.point, { layers: ['pins', 'clusters'] });
    map.getCanvas().style.cursor = hits.length ? 'pointer' : '';
    const pin = hits.find(h => h.layer.id === 'pins');
    const id = pin ? pin.properties.id : null;
    if (id !== hoveredId) { setHover(id); onPinHover?.(id); }
  });
  map.on('mouseout', () => {
    if (hoveredId != null) { setHover(null); onPinHover?.(null); }
  });
}

export function setMapData(items) {
  lastItems = items;
  applyData();
}

function applyData() {
  const src = map?.getSource('buildings');
  if (!src) return; // layers not ready yet — addLayers will apply lastItems
  src.setData({
    type: 'FeatureCollection',
    features: lastItems.map(b => ({
      type: 'Feature',
      id: b.id,
      geometry: { type: 'Point', coordinates: [b.lng, b.lat] },
      properties: {
        id: b.id, cov: covered(b) ? 'covered' : unfilmed(b) ? 'first' : 'unknown',
        name: b.name,
        st: b.stories ?? 0,
        floors: b.stories == null ? '' : `${b.stories} floor${b.stories === 1 ? '' : 's'}${b.stories_verified ? '' : ' · est'}`,
      },
    })),
  });
  if (activeId != null) trySetState(activeId, { active: true });
  if (hoveredId != null) trySetState(hoveredId, { hover: true });
}

/* Rebuild the basemap + markers for a new theme. */
export function setMapTheme(mode) {
  if (!map) return;
  // diff: false forces a full style load, so style.load fires and addLayers
  // rebuilds the pins. A diffed swap drops our layers without firing it.
  map.setStyle(STYLES[mode === 'full' ? 'full' : 'calm'], { diff: false });
  applyPitch(mode);
}

/* Full detail tilts the map so the 3D buildings read; calm stays flat. */
function applyPitch(mode) {
  const pitch = mode === 'full' ? 50 : 0;
  if (Math.round(map.getPitch()) === pitch) return;
  const instant = matchMedia('(prefers-reduced-motion: reduce)').matches;
  map.easeTo({ pitch, duration: instant ? 0 : 800 });
}

function trySetState(id, s) {
  // The source is briefly absent while a theme switch reloads the style.
  if (!map || !map.getSource('buildings')) return;
  try { map.setFeatureState({ source: 'buildings', id }, s); } catch { /* source not ready */ }
}

export function setHover(id) {
  if (hoveredId != null) trySetState(hoveredId, { hover: false });
  hoveredId = id;
  if (id != null) trySetState(id, { hover: true });
}

export function setActive(id) {
  if (activeId != null) trySetState(activeId, { active: false });
  activeId = id;
  if (id != null) trySetState(id, { active: true });
}

/* Frame a set of buildings (all of them on load, or a search's results). */
export function fitToBuildings(items, { maxZoom = 14 } = {}) {
  if (!map || !items.length) return;
  // Frame where the buildings actually cluster: trim the outer few percent so
  // a lone pin out in Montauk doesn't zoom everything else down to dots.
  const trim = items.length > 40 ? 0.03 : 0;
  const q = (arr, p) => arr[Math.min(arr.length - 1, Math.max(0, Math.round(p * (arr.length - 1))))];
  const lngs = items.map(b => b.lng).sort((a, b) => a - b);
  const lats = items.map(b => b.lat).sort((a, b) => a - b);
  const w = q(lngs, trim), e = q(lngs, 1 - trim), s = q(lats, trim), n = q(lats, 1 - trim);
  const narrow = matchMedia('(max-width: 860px)').matches;
  // A phone is too narrow to show Brooklyn to the East End at a useful zoom,
  // so the whole-catalogue view opens on the dense core (city + Nassau).
  const box = narrow && items.length > 200 ? [[-74.03, 40.58], [-73.55, 40.80]] : [[w, s], [e, n]];
  map.fitBounds(box, {
    padding: narrow ? { top: 70, bottom: 140, left: 24, right: 24 } : 60,
    maxZoom, duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 900,
  });
}

export function flyToBuilding(b) {
  if (!map) return;
  map.flyTo({ center: [b.lng, b.lat], zoom: Math.max(map.getZoom(), 14) });
}

function makeDot() {
  const el = document.createElement('div');
  el.className = 'loc-dot';
  el.setAttribute('role', 'img'); // MapLibre adds aria-label; a bare div may not carry one
  return el;
}

export function setLocationMarker(coords) {
  removeLocationMarker();
  locationMarker = new maplibregl.Marker({ element: makeDot() })
    .setLngLat([coords.lng, coords.lat]).addTo(map);
}
export function removeLocationMarker() {
  if (locationMarker) { locationMarker.remove(); locationMarker = null; }
}

export function setUserMarker(coords) {
  if (userMarker) userMarker.remove();
  userMarker = new maplibregl.Marker({ element: makeDot() })
    .setLngLat([coords.lng, coords.lat]).addTo(map);
}
export function removeUserMarker() {
  if (userMarker) { userMarker.remove(); userMarker = null; }
}
