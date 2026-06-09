<p align="center">
  <svg xmlns="http://www.w3.org/2000/svg" width="52" height="70" viewBox="0 0 120 160"><path d="M60 0C33.49 0 12 21.49 12 48C12 76.5 60 140 60 140C60 140 108 76.5 108 48C108 21.49 86.51 0 60 0Z" fill="#1f6f5c"/><circle cx="60" cy="42" r="24" fill="white"/><rect x="44" y="30" width="14" height="24" rx="1" fill="#1f6f5c"/><rect x="62" y="30" width="14" height="24" rx="1" fill="#1f6f5c"/><path d="M60 34L54 40L66 40Z" fill="white"/><path d="M60 50L66 44L54 44Z" fill="white"/></svg>
</p>

<h1 align="center">LiftSpot</h1>

<p align="center">
  <strong>Find and rate elevators in buildings across Long Island.</strong><br />
  Search 600+ buildings, read reviews, and explore on an interactive map.
</p>

<p align="center">
  <a href="https://selinmutlu06.github.io/liftspot"><img src="https://img.shields.io/badge/Live_App-Open_LiftSpot-1f6f5c?style=for-the-badge" alt="Live App" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vanilla_JS-ES2020-F7DF1E?logo=javascript&logoColor=black" alt="JavaScript" />
  <img src="https://img.shields.io/badge/MapLibre_GL-4.7-4A90D9" alt="MapLibre" />
  <img src="https://img.shields.io/badge/Supabase-PostgreSQL-3FCF8E?logo=supabase&logoColor=white" alt="Supabase" />
  <img src="https://img.shields.io/badge/OpenStreetMap-Nominatim-7EBC6F?logo=openstreetmap&logoColor=white" alt="Nominatim" />
</p>

<p align="center">
  <img src="docs/images/elevator.gif" alt="Pressing the elevator button" width="320" />
</p>

---

My younger brother has been obsessed with elevators for over a decade.

He spends hours every day tracking down new buildings, riding every elevator he can find, and cataloguing the details most people walk straight past: the cab manufacturer, the speed, the sound of the doors. He runs **[@elevatorzboy20](https://www.youtube.com/@elevatorzboy20)** on YouTube and Instagram, where he reviews elevators with a level of care I've only ever seen from the best critics.

The problem: there was no tool built for someone like him. No map of where to go. No way to filter by building type or floor count. No place to leave a review that actually mattered.

So I built one.

**LiftSpot** is a Long Island elevator finder, built for him and for anyone else who knows that not all elevators are created equal.

---

## What it does

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>Interactive Map</h3>
      <p>Every building pinned on a live MapLibre map. Click any pin to open the full detail drawer.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Smart Search</h3>
      <p>Search by name, town, or natural language ("5-story hospital in Mineola"). Geocodes addresses and switches to radius mode automatically.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Filter by Everything</h3>
      <p>Filter by building type (Medical, Hotel, Mall, Office, and more), minimum story count, or distance from your location.</p>
    </td>
  </tr>
  <tr>
    <td width="33%" valign="top">
      <h3>Elevator Reviews</h3>
      <p>Star ratings and written reviews stored in Supabase. Live rating updates as reviews come in.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Private Notes</h3>
      <p>Save personal notes per building: cab brand, access quirks, anything. Stored locally on your device.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Near Me Mode</h3>
      <p>Grant location access and get buildings sorted by distance with a radius slider (1–25 mi).</p>
    </td>
  </tr>
</table>

---

## Screenshots

<p align="center">
  <img src="docs/images/app-main.png" alt="LiftSpot full app view with sidebar and map" width="100%" />
</p>

<p align="center">
  <img src="docs/images/app-drawer.png" alt="LiftSpot building detail drawer with reviews" width="100%" />
</p>

---

## How it works

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif", "fontSize": "14px"}}}%%
flowchart LR
    A[Search or Location] --> B{Mode}
    B -- address/place --> C[Nominatim Geocode]
    C --> D[Radius Filter]
    B -- natural language --> E[Smart Score]
    B -- text --> F[Name/Town/Addr Match]
    D & E & F --> G[Building List + Map Pins]
    G --> H[Open Building Drawer]
    H --> I[(Supabase Reviews)]
    I --> H
```

| Step | What happens |
|------|--------------|
| **Load** | All 600+ buildings fetched from Supabase on page load |
| **Search** | Query geocoded via Nominatim; if a place is found, switches to radius mode; if multi-word, runs smart keyword scoring |
| **Filter** | Type chips and story count filter applied client-side in real time |
| **Detail** | Opening a building fetches its reviews from Supabase and shows specs, notes, and a star picker |
| **Review** | New reviews inserted into Supabase; building rating recalculated live |

---

## Tech stack

| Layer | Tools |
|-------|-------|
| **Frontend** | Vanilla HTML, CSS, JavaScript (zero build step) |
| **Map** | MapLibre GL 4.7, CartoDB Voyager tiles |
| **Geocoding** | Nominatim (OpenStreetMap) |
| **Database** | Supabase (PostgreSQL) |
| **Fonts** | Plus Jakarta Sans (Google Fonts) |
| **Hosting** | GitHub Pages |

---

## Data model

```sql
buildings (id, name, type, town, addr, lat, lng, stories, elevators, rating)
reviews   (id, building_id, who, stars, body, created_at)
```

16 building types: Medical, Dermatology, Physical Therapy, Radiology, Office, Mall, Hotel, Education, Government, Residential, Library, Transit, Legal, Entertainment, Community, Financial.

---

## Running it locally

No install, no build step. Just open the file:

```bash
git clone https://github.com/selinmutlu06/liftspot.git
cd liftspot
open index.html   # or serve with any static server
```

The Supabase project is public-read, so the map and buildings load immediately.

---

## Project structure

```
index.html          # Entire app, HTML + CSS + JS in one file
schema.sql          # Supabase table definitions and RLS policies
seed_more*.sql      # Building seed data
docs/images/        # README assets
```

---

<p align="center">
  <a href="https://www.youtube.com/@elevatorzboy20">YouTube</a> · <a href="https://www.instagram.com/elevatorzboy20">Instagram</a>
</p>

<p align="center">
  <sub>MIT License</sub>
</p>
