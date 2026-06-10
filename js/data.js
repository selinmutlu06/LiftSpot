/* Data layer: Supabase client, app state, filtering, smart search scoring. */

const { createClient } = window.supabase;

export const sb = createClient(
  'https://qrphiipxqvsrnenkphhr.supabase.co',
  'sb_publishable_SceOqu60uTDQpX_SM62gAQ_Rl5TgZig'
);

export const TYPES = ['Medical', 'Dermatology', 'Physical Therapy', 'Radiology', 'Office', 'Mall', 'Hotel', 'Education', 'Government', 'Residential', 'Library', 'Transit', 'Legal', 'Entertainment', 'Community', 'Financial'];

export const TYPE_ICON = { Medical: '✚', Dermatology: '◈', 'Physical Therapy': '⊕', Radiology: '◎', Office: '▣', Mall: '◫', Hotel: '⌂', Education: '✎', Government: '⚑', Residential: '⌂', Library: '▦', Transit: '⬡', Legal: '⚖', Entertainment: '♦', Community: '◉', Financial: '$' };

export const FLOOR_STOPS = [0, 1, 2, 3, 4, 5, 6, 8, 10, 15, 20];

export let BUILDINGS = [];

export const state = {
  q: '',
  types: new Set(),
  minStories: 0,
  exactStories: false,
  userLoc: null,
  activeId: null,
  searchMode: 'text',     // 'text' | 'smart' | 'location'
  locationCoords: null,
  locationLabel: '',
  radius: 5,
};

export const stars = n => '★'.repeat(Math.round(n)) + '☆'.repeat(5 - Math.round(n));

export const dist = (a, b) => {
  const R = 3959, dLat = (b.lat - a.lat) * Math.PI / 180, dLng = (b.lng - a.lng) * Math.PI / 180;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
};

const TYPE_KEYWORDS = {
  Medical: ['medical', 'hospital', 'doctor', 'clinic', 'health', 'urgent care', 'physician', 'surgery', 'orthopedic'],
  Dermatology: ['dermatology', 'dermatologist', 'skin', 'derm', 'acne', 'cosmetic'],
  'Physical Therapy': ['physical therapy', 'physical therapist', 'pt ', 'rehab', 'rehabilitation', 'sports medicine', 'occupational therapy'],
  Radiology: ['radiology', 'radiologist', 'xray', 'x-ray', 'imaging', 'mri', 'ct scan', 'ultrasound', 'mammography'],
  Office: ['office', 'professional', 'corporate', 'business', 'headquarters', 'hq', 'law firm', 'attorney'],
  Mall: ['mall', 'shopping', 'retail', 'plaza', 'shopping center', 'shops'],
  Hotel: ['hotel', 'motel', 'inn', 'stay', 'lodging', 'resort', 'suites'],
  Education: ['school', 'education', 'university', 'college', 'high school', 'academy', 'learning'],
  Library: ['library', 'books', 'reading', 'branch'],
  Government: ['government', 'city hall', 'village hall', 'dmv', 'municipal', 'county', 'town hall', 'federal'],
  Entertainment: ['entertainment', 'theater', 'theatre', 'museum', 'art', 'cinema', 'movie', 'gallery', 'park'],
  Community: ['community', 'ymca', 'jcc', 'recreation', 'center', 'arts council', 'cultural'],
  Financial: ['financial', 'bank', 'credit union', 'bancorp', 'savings'],
  Residential: ['residential', 'apartment', 'senior', 'assisted living', 'senior living', 'condo'],
  Legal: ['legal', 'law', 'courthouse', 'court'],
};

export function parseStoryCount(q) {
  const w = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, single: 1, double: 2, triple: 3 };
  const m = q.match(/(\d+)\s*(?:floor|stor)/i); if (m) return +m[1];
  for (const [word, n] of Object.entries(w)) {
    if (new RegExp(`\\b${word}\\s+(?:floor|stor)`, 'i').test(q)) return n;
  }
  if (/\bground.?floor\b|\bone.?floor\b/i.test(q)) return 1;
  return null;
}

export function smartScore(b, q) {
  const ql = q.toLowerCase();
  const bt = [b.name, b.type, b.town, b.addr].join(' ').toLowerCase();
  let score = 0;
  for (const [type, kws] of Object.entries(TYPE_KEYWORDS)) {
    if (kws.some(kw => ql.includes(kw))) {
      if (b.type === type) score += 10;
      else if (b.type === 'Medical' && ['Dermatology', 'Physical Therapy', 'Radiology'].includes(type)) score += 3;
    }
  }
  const want = parseStoryCount(ql);
  if (want !== null) {
    if (b.stories === want) score += 8;
    else if (Math.abs(b.stories - want) === 1) score += 2;
  }
  const words = ql.split(/\s+/).filter(w => w.length > 3 && !['with', 'that', 'near', 'from', 'have', 'this', 'floor', 'story', 'stories', 'floors', 'building', 'buildings'].includes(w));
  words.forEach(w => { if (bt.includes(w)) score += 2; });
  return score;
}

function applyChipFilters(arr) {
  if (state.types.size) arr = arr.filter(b => state.types.has(b.type));
  if (state.minStories > 0) {
    if (state.exactStories) arr = arr.filter(b => b.stories === state.minStories);
    else arr = arr.filter(b => b.stories >= state.minStories);
  }
  return arr;
}

export function filtered() {
  let result = applyChipFilters(BUILDINGS);

  if (state.searchMode === 'location' && state.locationCoords) {
    result = result.filter(b => dist(state.locationCoords, b) <= state.radius);
    return result.map(b => ({ ...b, _d: dist(state.locationCoords, b) })).sort((a, b) => a._d - b._d);
  }

  if (state.searchMode === 'smart' && state.q) {
    return result
      .map(b => ({ ...b, _score: smartScore(b, state.q), _d: state.userLoc ? dist(state.userLoc, b) : null }))
      .filter(b => b._score > 0)
      .sort((a, b) => b._score - a._score);
  }

  if (state.q) {
    const q = state.q.toLowerCase();
    result = result.filter(b => b.name.toLowerCase().includes(q) || b.town.toLowerCase().includes(q) || b.addr.toLowerCase().includes(q));
  }
  return result
    .map(b => ({ ...b, _d: state.userLoc ? dist(state.userLoc, b) : null }))
    .sort((a, b) => state.userLoc ? a._d - b._d : b.rating - a.rating);
}

/* Top matches for the search palette: smart score when multi-word,
   plus straightforward name/town prefix and substring weighting. */
export function topMatches(q, limit = 8) {
  if (!q.trim()) return [];
  const ql = q.toLowerCase();
  return BUILDINGS
    .map(b => {
      let s = smartScore(b, q);
      const name = b.name.toLowerCase(), town = b.town.toLowerCase();
      if (name.startsWith(ql)) s += 14;
      else if (name.includes(ql)) s += 8;
      if (town.startsWith(ql)) s += 6;
      else if (town.includes(ql)) s += 3;
      return { b, s };
    })
    .filter(x => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, limit)
    .map(x => x.b);
}

export async function loadBuildings() {
  const { data, error } = await sb.from('buildings').select('*');
  if (!error) BUILDINGS = data;
  return { data, error };
}
