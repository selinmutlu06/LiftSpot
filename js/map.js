/* Map: MapLibre init, native clustering, elevator-button pins, hover/active sync. */

export let map = null;

let onPinClick = null;
let onPinHover = null;
let locationMarker = null;
let userMarker = null;
let hoveredId = null;
let activeId = null;
let pendingItems = null;

export function initMap({ pinClick, pinHover }) {
  onPinClick = pinClick;
  onPinHover = pinHover;

  map = new maplibregl.Map({
    container: 'map',
    style: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
    center: [-73.55, 40.78],
    zoom: 9.6,
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'top-right');

  map.on('load', () => {
    map.addSource('buildings', {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
      promoteId: 'id',
      cluster: true,
      clusterRadius: 46,
      clusterMaxZoom: 13,
    });

    /* Clusters: ink discs with a steel ring — big elevator buttons. */
    map.addLayer({
      id: 'clusters', type: 'circle', source: 'buildings',
      filter: ['has', 'point_count'],
      paint: {
        'circle-color': '#16211d',
        'circle-radius': ['step', ['get', 'point_count'], 14, 10, 18, 50, 23, 150, 28],
        'circle-stroke-width': 2,
        'circle-stroke-color': '#c9ced0',
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
      paint: { 'text-color': '#23a47f' },
    });

    /* Single pins: small round buttons. Halo ring lights when hovered/active. */
    map.addLayer({
      id: 'pin-halo', type: 'circle', source: 'buildings',
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-radius': 13,
        'circle-color': '#23a47f',
        'circle-opacity': [
          'case',
          ['any',
            ['boolean', ['feature-state', 'hover'], false],
            ['boolean', ['feature-state', 'active'], false]],
          0.35, 0,
        ],
      },
    });
    map.addLayer({
      id: 'pins', type: 'circle', source: 'buildings',
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-radius': 7,
        'circle-color': [
          'case',
          ['any',
            ['boolean', ['feature-state', 'hover'], false],
            ['boolean', ['feature-state', 'active'], false]],
          '#23a47f', '#f5f6f4',
        ],
        'circle-stroke-width': 2,
        'circle-stroke-color': '#16211d',
      },
    });

    map.on('click', 'clusters', async e => {
      const f = map.queryRenderedFeatures(e.point, { layers: ['clusters'] })[0];
      const zoom = await map.getSource('buildings').getClusterExpansionZoom(f.properties.cluster_id);
      map.easeTo({ center: f.geometry.coordinates, zoom: zoom + 0.4 });
    });

    map.on('click', 'pins', e => {
      if (!e.features.length) return;
      onPinClick?.(e.features[0].properties.id);
    });

    map.on('mousemove', 'pins', e => {
      if (!e.features.length) return;
      const id = e.features[0].properties.id;
      if (id !== hoveredId) {
        setHover(id);
        onPinHover?.(id);
      }
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'pins', () => {
      setHover(null);
      onPinHover?.(null);
      map.getCanvas().style.cursor = '';
    });
    ['clusters'].forEach(l => {
      map.on('mouseenter', l, () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', l, () => { map.getCanvas().style.cursor = ''; });
    });

    if (pendingItems) { setMapData(pendingItems); pendingItems = null; }
  });

  return map;
}

export function setMapData(items) {
  const src = map?.getSource('buildings');
  if (!src) { pendingItems = items; return; }
  src.setData({
    type: 'FeatureCollection',
    features: items.map(b => ({
      type: 'Feature',
      id: b.id,
      geometry: { type: 'Point', coordinates: [b.lng, b.lat] },
      properties: { id: b.id },
    })),
  });
  if (activeId != null) trySetState(activeId, { active: true });
}

function trySetState(id, s) {
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
