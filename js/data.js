/* Data layer: Supabase client, app state, filtering, smart search scoring. */

const { createClient } = window.supabase;

export const sb = createClient(
  'https://qrphiipxqvsrnenkphhr.supabase.co',
  'sb_publishable_SceOqu60uTDQpX_SM62gAQ_Rl5TgZig'
);

export const TYPES = ['Medical', 'Dermatology', 'Physical Therapy', 'Radiology', 'Office', 'Mall', 'Hotel', 'Education', 'Government', 'Residential', 'Library', 'Transit', 'Legal', 'Entertainment', 'Community', 'Financial'];

/* Consistent 24x24 stroke icon set (Lucide-style): one weight, one grid. */
const TYPE_PATHS = {
  Medical: '<path d="M11 2a2 2 0 0 0-2 2v5H4a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h5v5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2v-5h5a2 2 0 0 0 2-2v-2a2 2 0 0 0-2-2h-5V4a2 2 0 0 0-2-2z"/>',
  Dermatology: '<path d="M9.94 15.5a2 2 0 0 0-1.44-1.44l-6.13-1.58a.5.5 0 0 1 0-.96L8.5 9.94a2 2 0 0 0 1.44-1.44l1.58-6.13a.5.5 0 0 1 .96 0l1.58 6.13a2 2 0 0 0 1.44 1.44l6.13 1.58a.5.5 0 0 1 0 .96l-6.13 1.58a2 2 0 0 0-1.44 1.44l-1.58 6.13a.5.5 0 0 1-.96 0z"/>',
  'Physical Therapy': '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  Radiology: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/>',
  Office: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
  Mall: '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
  Hotel: '<path d="M2 20v-8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8"/><path d="M4 10V6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4"/><path d="M12 4v6"/><path d="M2 18h20"/>',
  Education: '<path d="M21.42 10.92a1 1 0 0 0-.02-1.84L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.83l8.57 3.91a2 2 0 0 0 1.66 0z"/><path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
  Government: '<path d="M3 22h18"/><path d="M6 18v-7"/><path d="M10 18v-7"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="m12 2 8 5H4z"/>',
  Residential: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
  Library: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
  Transit: '<rect x="4" y="3" width="16" height="16" rx="2"/><path d="M4 11h16"/><path d="M12 3v8"/><path d="m8 19-2 3"/><path d="m18 22-2-3"/><path d="M8 15h.01"/><path d="M16 15h.01"/>',
  Legal: '<path d="m16 11 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1"/><path d="m2 11 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
  Entertainment: '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2z"/><path d="M13 5v2"/><path d="M13 17v2"/><path d="M13 11v2"/>',
  Community: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  Financial: '<path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
};

export function typeIcon(t, size = 16) {
  const paths = TYPE_PATHS[t];
  if (!paths) return '';
  return `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

export const maxStories = () => BUILDINGS.reduce((m, b) => Math.max(m, b.stories ?? 0), 20);

export let BUILDINGS = [];

export const state = {
  q: '',
  types: new Set(),
  minStories: 0,
  exactStories: false,
  firstOnly: false,
  userLoc: null,
  activeId: null,
  searchMode: 'text',     // 'text' | 'smart' | 'location'
  locationCoords: null,
  locationLabel: '',
  radius: 5,
};

export const stars = n => {
  const r = Math.max(0, Math.min(5, Math.round(n)));
  return '★'.repeat(r) + '☆'.repeat(5 - r);
};

// A building is only "rated" once it has real reviews. Rating is recalculated
// from reviews on every post (see drawer.js); 0 means no reviews exist yet, so
// we never show a fabricated score.
export const rated = b => Number(b.rating) > 0;

// `verified` = confirmed against OpenStreetMap as a real building at this
// location (see migrations/003). It covers existence/location ONLY.
export const verified = b => b.verified === true;

// Floor count is a confirmed fact only where a name-matched OSM building
// polygon carries building:levels (migrations/008). A non-null unverified value
// comes from an unnamed OSM polygon at the point ("· est"); NULL means no
// source has the number and the UI shows "?" instead of a guess.
export const storiesVerified = b => b.stories_verified === true;

// Elevator counts have NO authoritative public source, so they are NULL until
// the community reports them — never a fabricated number.

// "Unfilmed" = our YouTube search (scripts/check_youtube.py) found no video of
// this building's elevators as of yt_checked. Absence can't be proven, so the
// UI always dates the claim ("none found as of ...") — never "never filmed".
// yt_videos NULL with yt_checked set = ambiguous near-miss matches pending
// human review: no claim in either direction, so no badge. Same for
// reddit_posts (migrations/012). A source that hasn't been checked yet (column
// absent from the row) doesn't block the badge — it just isn't claimed.
export const unfilmed = b => b.yt_checked != null && b.yt_videos === 0
  && (!('reddit_posts' in b) || b.reddit_posts === 0);
export const ytChecked = b => b.yt_checked != null;
// Footage actually found somewhere. Anything neither covered nor unfilmed is
// still unchecked or awaiting review, and the map says so instead of guessing.
export const covered = b => b.yt_videos > 0 || b.reddit_posts > 0;

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
  Mall: ['mall', 'shopping', 'retail', 'shopping center', 'shops'],
  Hotel: ['hotel', 'motel', 'inn', 'lodging', 'resort', 'suites'],
  Education: ['school', 'education', 'university', 'college', 'high school', 'academy', 'learning'],
  Library: ['library', 'books', 'reading', 'branch'],
  Government: ['government', 'city hall', 'village hall', 'dmv', 'municipal', 'town hall', 'federal'],
  Entertainment: ['entertainment', 'theater', 'theatre', 'museum', 'cinema', 'movie', 'gallery'],
  Community: ['community', 'ymca', 'jcc', 'recreation', 'arts council', 'cultural'],
  Financial: ['financial', 'bank', 'credit union', 'bancorp', 'savings'],
  Residential: ['residential', 'apartment', 'senior', 'assisted living', 'senior living', 'condo'],
  Legal: ['legal', 'law', 'courthouse', 'court'],
};

export function parseStoryCount(q) {
  const w = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, single: 1, double: 2, triple: 3 };
  const m = q.match(/(\d+)\s*-?\s*(?:floor|stor)/i); if (m) return +m[1];
  for (const [word, n] of Object.entries(w)) {
    if (new RegExp(`\\b${word}\\s+(?:floor|stor)`, 'i').test(q)) return n;
  }
  if (/\bground.?floor\b|\bone.?floor\b/i.test(q)) return 1;
  return null;
}

/* Where a query can point: a town/neighborhood we have buildings in, or a
   whole region. Queens and Brooklyn addresses always carry their borough. */
const inRegion = (b, r, guess) => (b.region ? b.region === r : guess(b));
const REGIONS = {
  brooklyn: b => inRegion(b, 'Brooklyn', x => /\bbrooklyn, ny\b/i.test(x.addr)),
  queens: b => inRegion(b, 'Queens', x => x.id >= 2000 && !/\bbrooklyn, ny\b/i.test(x.addr)),
  'long island': b => inRegion(b, 'Long Island', x => x.id < 2000),
};
const TOWN_ALIASES = { lic: 'long island city', 'bed stuy': 'bedford-stuyvesant', 'bed-stuy': 'bedford-stuyvesant', dumbo: 'dumbo' };
const STOP = new Set(['with', 'that', 'near', 'from', 'have', 'this', 'floor', 'story', 'stories', 'floors', 'building', 'buildings',
  'tall', 'tallest', 'high', 'rise', 'highrise', 'high-rise', 'skyscraper', 'skyscrapers', 'show', 'find', 'some', 'what', 'where', 'which', 'most', 'least', 'more', 'than', 'over', 'around']);

let townIndex = null;  // lowercase town -> canonical, rebuilt when data loads
function towns() {
  if (!townIndex || townIndex.size === 0) {
    townIndex = new Map(BUILDINGS.map(b => [b.town.toLowerCase(), b.town]));
  }
  return townIndex;
}

/* Turn a natural-language query into hard constraints + leftover keywords,
   so "tall residential in Long Island City" means Residential AND in LIC,
   tallest first, instead of anything mentioning "long" or "city". */
export function parseQuery(q) {
  let ql = ` ${q.toLowerCase().replace(/[?!.,]/g, ' ').replace(/\s+/g, ' ')} `;
  for (const [a, t] of Object.entries(TOWN_ALIASES)) ql = ql.replace(` ${a} `, ` ${t} `);
  const out = { types: new Set(), town: null, region: null, stories: parseStoryCount(ql), atLeast: false, tall: false, words: [] };
  // Longest town name first, so "Long Island City" beats "Long Beach" style overlaps.
  // Borough names are regions, never one "town", even where a row's town says "Brooklyn".
  const names = [...towns().keys()].filter(t => t.length > 2 && !(t in REGIONS)).sort((a, b) => b.length - a.length);
  for (const t of names) {
    if (ql.includes(` ${t} `)) { out.town = towns().get(t); ql = ql.replace(` ${t} `, ' '); break; }
  }
  if (!out.town) {
    for (const r of Object.keys(REGIONS)) if (ql.includes(` ${r} `)) { out.region = r; ql = ql.replace(` ${r} `, ' '); break; }
  }
  for (const [type, kws] of Object.entries(TYPE_KEYWORDS)) {
    if (kws.some(kw => ql.includes(` ${kw.trim()} `) || ql.includes(` ${kw.trim()}s `))) out.types.add(type);
  }
  // The specialty types have no buildings of their own; their keywords mean "medical".
  if (['Dermatology', 'Physical Therapy', 'Radiology'].some(t => out.types.has(t))) out.types.add('Medical');
  out.tall = /\b(tall|tallest|high.?rise|skyscrapers?|towers?)\b/.test(ql);
  out.atLeast = out.stories != null && /\b(at least|over|more than|plus|\d+\+)/.test(ql);
  out.words = ql.split(/\s+/).filter(w => w.length > 3 && !STOP.has(w)
    && !Object.values(TYPE_KEYWORDS).flat().includes(w) && !/^\d/.test(w));
  return out;
}

const hasConstraints = p => p.types.size || p.town || p.region || p.stories != null;

export function smartScore(b, q, p = parseQuery(q)) {
  if (p.town && b.town !== p.town) return 0;
  if (p.region && !REGIONS[p.region](b)) return 0;
  if (p.types.size && !p.types.has(b.type)) return 0;
  // An unknown floor count can't be ruled out, so it stays in, ranked below known matches.
  if (p.stories != null && b.stories != null) {
    if (p.atLeast ? b.stories < p.stories : Math.abs(b.stories - p.stories) > 1) return 0;
  }
  let score = hasConstraints(p) ? 10 : 0;
  if (p.stories != null && b.stories === p.stories) score += 4;
  if (p.tall) score += Math.min(b.stories ?? 0, 80) / 4;
  const bt = [b.name, b.type, b.town, b.addr].join(' ').toLowerCase();
  let hits = 0;
  p.words.forEach(w => { if (bt.includes(w)) { score += 3; hits++; } });
  // Free words with no constraint behind them must actually match something.
  if (!hasConstraints(p) && !hits) return 0;
  return score;
}

function applyChipFilters(arr) {
  if (state.types.size) arr = arr.filter(b => state.types.has(b.type));
  if (state.firstOnly) arr = arr.filter(unfilmed);
  if (state.minStories > 0) {
    // Buildings with an unknown floor count can't satisfy a stories filter.
    if (state.exactStories) arr = arr.filter(b => b.stories === state.minStories);
    else arr = arr.filter(b => b.stories != null && b.stories >= state.minStories);
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
    const p = parseQuery(state.q);
    return result
      .map(b => ({ ...b, _score: smartScore(b, state.q, p), _d: state.userLoc ? dist(state.userLoc, b) : null }))
      .filter(b => b._score > 0)
      .sort((a, b) => (b._score - a._score) || ((b.stories ?? -1) - (a.stories ?? -1)));
  }

  if (state.q) {
    const q = state.q.toLowerCase();
    result = result.filter(b => b.name.toLowerCase().includes(q) || b.town.toLowerCase().includes(q) || b.addr.toLowerCase().includes(q));
  }
  return result
    .map(b => ({ ...b, _d: state.userLoc ? dist(state.userLoc, b) : null }))
    .sort((a, b) => state.userLoc ? a._d - b._d
      // Reviews first, then the tallest buildings, then A to Z.
      : (b.rating - a.rating) || ((b.stories ?? -1) - (a.stories ?? -1)) || a.name.localeCompare(b.name));
}

/* True when a query reads as a request ("hospitals in Mineola") rather than a
   place name, so search filters the catalogue instead of geocoding. */
export const isSmartQuery = q => hasConstraints(parseQuery(q)) || parseQuery(q).tall;

/* A query that names one of our buildings outright ("Roosevelt Field"). */
export const namesBuilding = q => {
  const ql = q.trim().toLowerCase();
  return ql.length > 3 && BUILDINGS.some(b => b.name.toLowerCase().includes(ql));
};

/* Top matches for the search palette: smart score when multi-word,
   plus straightforward name/town prefix and substring weighting. */
export function topMatches(q, limit = 8) {
  if (!q.trim()) return [];
  const ql = q.toLowerCase();
  const p = parseQuery(q);
  return BUILDINGS
    .map(b => {
      let s = smartScore(b, q, p);
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
  if (!error) { BUILDINGS = data || []; townIndex = null; }
  return { data, error };
}
