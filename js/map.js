/* Map: MapLibre init, native clustering, button pins, hover/active sync.
   The basemap and marker colors follow the theme: a light basemap for the
   calm default, the dark "cab" basemap for full detail. Layers are rebuilt
   whenever the style changes, so switching themes never loses the pins.
   "Be the first" buildings (no coverage found anywhere) get amber pins so
   the hunt is visible on the map itself, not just in the list. */

import { unfilmed } from './data.js';

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
    pinFirst: '#b87d00',
  },
  full: {
    clusterFill: '#1d2b26', clusterStroke: '#c9ced0', clusterText: '#23a47f',
    pinFill: '#f5f6f4', pinActive: '#23a47f', pinStroke: '#16211d', halo: '#23a47f',
    pinFirst: '#e8a13a',
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
    center: [-73.55, 40.78],
    zoom: 9.6,
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'top-right');

  bindInteractions();
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
      'circle-radius': 14,
      'circle-color': c.halo,
      'circle-opacity': ['case', litState, 0.3, 0],
    },
  });
  map.addLayer({
    id: 'pins', type: 'circle', source: 'buildings',
    filter: ['!', ['has', 'point_count']],
    paint: {
      'circle-radius': 7,
      'circle-color': ['case', litState, c.pinActive,
        ['boolean', ['get', 'first'], false], c.pinFirst,
        c.pinFill],
      'circle-stroke-width': 2.5,
      'circle-stroke-color': c.pinStroke,
    },
  });

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
      properties: { id: b.id, first: unfilmed(b) },
    })),
  });
  if (activeId != null) trySetState(activeId, { active: true });
  if (hoveredId != null) trySetState(hoveredId, { hover: true });
}

/* Rebuild the basemap + markers for a new theme. */
export function setMapTheme(mode) {
  if (!map) return;
  map.setStyle(STYLES[mode === 'full' ? 'full' : 'calm']); // style.load re-runs addLayers
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

export function flyToBuilding(b) {
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
