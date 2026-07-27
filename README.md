# LiftSpot

Data pipeline is validated and cleaned using [liftspot-data-tool](https://github.com/selinmutlu06/liftspot-data-tool).

Data pipeline is validated and cleaned using [liftspot-data-tool](https://github.com/selinmutlu06/liftspot-data-tool).

Find and rate elevators in buildings across Long Island. 572 buildings, searchable, filterable, reviewable, live at [liftspot.netlify.app](https://liftspot.netlify.app).

<img src="docs/images/elevator.gif" alt="Pressing the elevator button" width="320" />

My younger brother has been obsessed with elevators for over a decade. He spends hours every day tracking down new buildings, riding every elevator he can find, and cataloguing the details most people walk straight past: the cab manufacturer, the speed, the sound of the doors. He runs [@elevatorzboy20](https://www.youtube.com/@elevatorzboy20) on YouTube and Instagram, where he reviews elevators with a level of care I've only ever seen from the best critics.

The problem: there was no tool built for someone like him. No map of where to go. No way to filter by building type or floor count. No place to leave a review that actually mattered.

So I built one.

<br>

## What it does

Every building sits pinned on a live MapLibre map, and clicking any pin opens the full detail drawer. Search takes names, towns, or natural language ("5-story hospital in Mineola"), geocodes addresses, and switches to radius mode automatically. Filters cover building type (Medical, Hotel, Mall, Office, and more), minimum story count, and distance from your location, with a near-me mode that sorts by distance on a 1-25 mile slider.

Ratings come from real submitted reviews only, never a seeded number. A building shows "No reviews yet" until someone actually rates it, then the score recalculates live. Private notes let you save anything per building (cab brand, access quirks), stored locally on your device.

**Fig. 1. The main view.** Filter sidebar and building list beside a live Long Island map with clustered pins.

<img src="docs/images/app-main.png" alt="liftspot main view: sidebar of filters and building list beside a live long island map with clustered pins" width="100%" />

**Fig. 2. The building drawer.** Specs, a real elevator review, and private notes.

<img src="docs/images/app-drawer.png" alt="liftspot building detail drawer showing specs, a real elevator review, and private notes" width="100%" />

**Fig. 3. Mobile.** Map-first layout with a draggable bottom sheet of buildings.

<img src="docs/images/app-mobile.png" alt="liftspot on mobile: map-first layout with a draggable bottom sheet" width="320" />

<br>

## The design

LiftSpot opens in a calm default. A quiet "modern cab interior" palette, low motion, only the essentials on screen. A full-detail toggle reveals the denser specs view for power users. The whole interface was designed with an autism-friendly default in mind: readable, low-stimulation, axe-clean across every state, honouring prefers-reduced-motion, and map-first on mobile with a draggable sheet.

<br>

## How it works

| Step | What happens |
|------|--------------|
| Load | All 572 buildings fetched from Supabase on page load |
| Search | Query geocoded via Nominatim; a found place switches to radius mode, multi-word queries run smart keyword scoring |
| Filter | Type chips and story count applied client-side in real time |
| Detail | Opening a building fetches its reviews and shows specs, notes, and a star picker |
| Review | New reviews inserted into Supabase; rating recalculated live from real reviews only |

| Layer | Tools |
|-------|-------|
| Frontend | Vanilla HTML, CSS, JavaScript, zero build step |
| Map | MapLibre GL 4.7, CartoDB Voyager tiles |
| Geocoding | Nominatim (OpenStreetMap) |
| Database | Supabase (PostgreSQL) |
| Hosting | Netlify |

```sql
buildings (id, name, type, town, addr, lat, lng, stories, elevators, rating)
reviews   (id, building_id, who, stars, body, created_at)
```

16 building types: Medical, Dermatology, Physical Therapy, Radiology, Office, Mall, Hotel, Education, Government, Residential, Library, Transit, Legal, Entertainment, Community, Financial.

<br>

## The data honesty rules

The building catalogue was originally seeded, and seeded data lies. Invented floor counts, guessed elevator counts, a fake default rating on every row. That's being corrected under one rule: don't present a guess as a fact.

**Ratings** are derived from real reviews only. The fabricated default scores were stripped (`migrations/001_unfake_ratings.sql`), and buildings with no reviews say so.

**Existence and location** are audited against four independent sources: OpenStreetMap, Wikidata, the US Census geocoder, and the Foursquare Places API (`scripts/verify_sources.py`). The audit is precision-first. A building is flagged verified only when a source confirms it by name near the pin, and guards reject town-name matches, street-name matches, wrong house numbers, and category mismatches, so a fabricated "Elmont Medical Center" can't ride on a neighbouring optometrist. Of 572 buildings, 175 clear that bar. Per-building evidence lives in `scripts/sources_evidence.csv`.

**Wrong coordinates** get corrected. The audit found 59 buildings whose seed pin was off and snapped them to the confirmed feature.

**Unverified buildings** carry a badge, not a deletion. Most have real street addresses but simply aren't named in any free dataset.

**Floor counts** show as fact only where OpenStreetMap's building:levels backs them. Everything else renders as an estimate, even on otherwise-verified buildings.

**Elevator counts** have no authoritative public source anywhere, so they always show as a community estimate. Reviews can confirm real counts over time.

**Writes are locked down.** The public can update exactly one column, the review-derived rating, so no anonymous visitor can flip verified, move a pin, or edit specs.

The goal is a catalogue where every shown number is either verified or honestly marked as not.

<br>

## Running it locally

No install, no build step. Serve the folder with any static server (ES modules need http, not file://):

```bash
git clone https://github.com/selinmutlu06/liftspot.git
cd liftspot
python3 -m http.server 8000   # then open http://localhost:8000
```

The Supabase project is public-read, so the map and buildings load immediately.

```
index.html          markup + CDN links
css/tokens.css      design tokens, the "modern cab interior" palette
css/app.css         all component styles
js/data.js          Supabase client, state, filtering, smart search scoring
js/map.js           MapLibre init, clustering, elevator-button pins
js/search.js        command palette (Cmd-K), geocode cache + rate limit
js/drawer.js        building detail, door-reveal animation, reviews, notes
js/ui.js            entry module: filters, list, toasts, wiring
schema.sql          table definitions and RLS policies
migrations/         incremental SQL changes
scripts/            multi-source verification audit
docs/               README assets + redesign plan
```

<br>

<sub>Built for one very specific critic. Find him at [YouTube](https://www.youtube.com/@elevatorzboy20) and [Instagram](https://www.instagram.com/elevatorzboy20). MIT License.</sub>
