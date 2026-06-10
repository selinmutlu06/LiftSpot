# LiftSpot redesign — "Modern cab interior"

## Behavior inventory (must not regress)

1. Initial load fetches all `buildings` from Supabase; skeletons while loading; visible error on failure.
2. Search modes: **text** (substring on name/town/addr) → debounced 300ms geocode via Nominatim (LI viewbox, `bounded=1`, retry with ", NY") → **location** mode (radius filter, distance sort, dropped marker, flyTo, radius slider visible) → else if ≥2 words, **smart** mode (TYPE_KEYWORDS scoring + story-count phrase parsing + word match; filter score>0, sort desc). Enter = immediate geocode. Clear resets to text and removes marker.
3. 16 type filters, multi-select, filter list + pins.
4. Min-stories filter, values Any/1/2/3/4/5/6/8/10/15/20, `stories >= n`.
5. "Near me": geolocation → distance sort + distances shown, marker, flyTo. (Upgraded: now also enters location mode so the radius slider applies — this matches the brief's framing of "near-me mode with radius slider".)
6. List rows: name, type, rating, address, stories/elevators, distance when known; click/Enter/Space opens drawer + flyTo; active row highlighted.
7. Map pins clickable, hover cursor; active pin distinct.
8. Drawer: name, type · town, stories/elevators/rating, address, private note (localStorage key `liftspot_note_${id}` — preserved so existing notes survive), star picker (keyboard accessible), review insert to Supabase, reviews newest-first, **live rating recalc written back to `buildings.rating`**.
9. Drawer closes via X, scrim, Escape; focus management; aria-modal.
10. prefers-reduced-motion kills animation globally.

## Tokens

```
--ink-900 #16211d   dark surfaces / text on light
--ink-800 #1d2b26   raised dark surface
--ink-600 #44524c   muted text on light (AA on paper)
--steel-400 #aab2b3 steel detail on dark
--steel-300 #c9ced0 borders, rails
--steel-150 #e4e7e7 hairlines on light
--paper #f5f6f4     app surface
--card #ffffff      cards
--green-700 #1f6f5c brand on light (5.5:1 on paper)
--led #23a47f       illuminated states (on dark only)
--led-glow rgba(35,164,127,.45)
--amber #e8a13a     stars (glyphs); numeric ratings set in ink
--red-600 #b3402f   errors only (AA on paper)
```

Type: **Space Grotesk** (display: wordmark, drawer titles, section heads) · **Plus Jakarta Sans** (body) · **JetBrains Mono** (LED numerals only: counts, stories, elevators, distances, ratings, floor strip, cluster badges). 4px spacing grid.

## Layout

Desktop 1440:
```
┌──────────────────────────────────────────────────────────────┐
│ TOPBAR (ink, brushed) ⬢ LIFTSPOT │ [⌘K search………] │ ◉ Near me│
├───────────────┬──────────────────────────────────────────────┤
│ CAB PANEL(ink)│                                              │
│ ┌─┬─┬─┬─┐  ┌─┐│                 MAP                          │
│ │○│○│○│○│  │5││         clusters + button-pins              │
│ │○│○│○│○│  │4││                                              │
│ │ button │  │3││                          ┌─────────────────┐│
│ │ plate  │  │2││                          │ DRAWER          ││
│ └─┴─┴─┴─┘  └─┘│                          │ (door reveal)   ││
│ floors → strip│                          └─────────────────┘│
├───────────────┤                                              │
│ LED count row │                                              │
│ RESULTS LIST  │                                              │
│ (paper cards) │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

Mobile 390: topbar (brand+search) → map (~46vh) → filter row (Buttons sheet trigger + horizontal floor strip) → results bottom sheet (peek/half/full). Drawer = full-width overlay with the same door reveal.

## Signature elements

1. **Button-plate type filters**: 4-col grid of 44px round buttons on the ink cab panel, 10px uppercase labels beneath. Inactive: steel ring, dark fill. Active: `--led` ring + soft halo + lit label. Press: scale(.96) 120ms. ARIA `aria-pressed` preserved.
2. **Floor-indicator story filter**: vertical strip beside the plate, JetBrains Mono numerals, selected value lit LED-green with glow; radiogroup semantics, arrow-key navigable. Horizontal variant under 860px.
3. **Door-reveal drawer**: drawer slides in instantly; two ink door panels part horizontally 220ms ease-out, once per open. Fully disabled under prefers-reduced-motion.

LED numerals (sanctioned identity element, not part of the 3-animation budget): result count readout above the list ("BLDGS 612" style), data row in drawer, cluster counts, floor strip.

## Self-critique (one pass, per process)

*What would look the same in a generic map app?* (a) The original plan's pushpins — replaced with round "elevator button" markers: steel-ringed circles, green-lit when active, cluster badges as larger ink buttons with LED counts. (b) A plain results header — replaced with the LED count readout. (c) Topbar risked generic dark-navbar; it gets a brushed-steel hairline treatment and an inset readout, no logo gradient, no pill buttons. (d) Toasts default-blue — ours are ink with steel border, LED-green check for success. Removed one decoration after the pass: dropped a planned subtle noise texture on the cab panel (busy, served nothing).

## File structure

```
index.html      markup + font/CDN links, entry <script type="module" src="js/ui.js">
css/tokens.css  custom properties, font stacks, spacing grid
css/app.css     all component styles
js/data.js      supabase client, state, filtering, smart score, distance
js/map.js       map init, cluster source/layers, marker sync, map events
js/search.js    palette dropdown, geocode (cache + 1 req/s), debounce, modes
js/drawer.js    drawer render, door animation, notes, reviews, rating recalc
js/ui.js        entry: filters, list, toasts, states, wiring
```

ES modules, zero build step. Local dev now needs any static server (`python3 -m http.server`) because modules don't run from `file://` — Netlify/Pages unaffected.
