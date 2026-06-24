# FIFA World Cup 2026 — Qualified Nations Dashboard

An interactive, **single-file** web dashboard for the 2026 FIFA World Cup: a world map highlighting all 48 qualified nations, live group standings, a knockout bracket, and a per-nation panel with squad-league breakdown, fixtures and population.

**Live demo:** https://ponienc.github.io/wc2026_dashboard/

## Features

- **Map of the 48 qualified nations**, coloured by **continent** (Europe / S. America / N. America / Africa / Asia / Oceania), with a "Qualified" single-colour toggle.
- **Click a nation → fly-to-zoom** (zooms to a country's *mainland* largest landmass, e.g. the contiguous US, not Alaska/Hawaii).
- **Live group standings** grouped A–L (P / GD / Pts + form dots), updated from the API.
- **Knockout bracket** (Round of 32 → Final + third place) with elbow connectors; placed teams fill in live as group winners are confirmed.
- **Detail panel** on zoom-in: live stats, **population**, a **bar chart of where the 26-man squad plays** (by club country), and live group fixtures.
- **Auto-refresh** every 60 s — an open tab stays current on its own.

## Data sources

| Layer | Source |
|---|---|
| Teams, groups, standings, fixtures, bracket | [worldcup26.ir](https://worldcup26.ir) (open REST API, CORS-enabled — fetched client-side, no key) — from [rezarahiminia/worldcup2026](https://github.com/rezarahiminia/worldcup2026) |
| Country boundaries, continent, population | [Natural Earth 1:50m](https://github.com/nvkelso/natural-earth-vector) (`ADM0_A3` / `CONTINENT` / `POP_EST`) |
| Squad → club-league distribution | Parsed from [Wikipedia: 2026 FIFA World Cup squads](https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads) (each player's club country) |
| Basemap tiles | © OpenStreetMap, © CARTO (Positron) · Map library: [Leaflet](https://leafletjs.com) |
| Flags | [flagcdn.com](https://flagcdn.com) |

Because all data is fetched **client-side** from a CORS-open API, the page is fully static — "live updates" happen on every load (and via the 60 s auto-refresh), with no backend.

## Run locally

It's one file. Either open `index.html` directly, or serve it:

```bash
python3 -m http.server 4173
# then open http://localhost:4173
```

## Notes

- England & Scotland share the UK (`GBR`) polygon (no separate home-nation boundaries at this resolution) but stay distinct in the panel and squad chart.
- Squad-league data is a snapshot of the 1 June 2026 squad lists; re-parse Wikipedia to refresh.

CRS: EPSG:3857 (tiles) / EPSG:4326 (data).

## Disclaimer

This is an **unofficial, non-commercial fan project**. It is **not affiliated with, endorsed by, or sponsored by FIFA**. "FIFA" and "FIFA World Cup" are trademarks of FIFA and are used here for identification purposes only. All match data is consumed from third-party sources (see above); country flags and boundaries are public-domain/free assets.

## Licence

Code is released under the [MIT License](LICENSE) © 2026 PoNienC. Third-party data and assets remain under their own licences (Natural Earth — public domain; OpenStreetMap — ODbL; Leaflet — BSD-2-Clause; worldcup26.ir — ISC).

