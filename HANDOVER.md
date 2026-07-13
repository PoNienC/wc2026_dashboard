# HANDOVER — WC2026 dashboard + social asset

_Last updated: 13 July 2026. Single live state file — overwrite in place, keep ≤120 lines._

## Pending decisions / next steps
- [ ] Post the LinkedIn comment (draft below) together with `social/wc2026_final_four_hero.png` on Milan Janosov's post about World Cup travel.
- [ ] Optional: produce an **animated MP4** of the travel poster (flags flying each route, km ticking up) for a standalone LinkedIn post.
- [ ] Optional: produce a **2×2 small-multiples** variant (one clean mini-map per team).
- [ ] Numbers are live-derived at the semi-final stage (13 Jul 2026). Re-check before reusing once the semis are played.

## What this repo is
Interactive single-file dashboard for the 2026 FIFA World Cup (`index.html`): world map of the 48 qualified nations, live standings, knockout bracket, per-nation squad panel, and a **Travel tracker** (great-circle air miles per team). Data is fetched client-side from worldcup26.ir + api.fifa.com. Deployed via GitHub Pages from `main` → https://ponienc.github.io/wc2026_dashboard/

## Done this session (13 Jul 2026)
1. **Dashboard now defaults to the Travel tracker.** `index.html` (~line 2205): `setView('travel')` (was `'bracket'`). Deployed to Pages and verified live.
2. **Built a social poster** for a LinkedIn reply about the final four's air miles — see `social/`:
   - `poster_hero.html` — self-contained Leaflet poster (route data hardcoded). National-flag colours; thin routes offset per city-pair so repeat legs separate; **dashed = the upcoming semi-final leg**; flags sit at the semi venues (Dallas, Atlanta); ranking strip along the bottom. 1600×970 landscape, full-bleed map with text overlaid.
   - `capture.py` — Playwright headless renderer → PNG.
   - `wc2026_final_four_hero.png` — the final, comment-ready image.

## The final four — air miles to reach the semis (great-circle km, incl. the semi trip)
| Team | km | Semi-final |
|---|---:|---|
| Spain | 10,374 | v France — Dallas, Tue 14 Jul |
| England | 9,171 | v Argentina — Atlanta, Wed 15 Jul |
| Argentina | 5,644 | v England — Atlanta, Wed 15 Jul |
| France | 3,859 | v Spain — Dallas, Tue 14 Jul |

Spain & England lead all 48 nations for distance; Spain flew ~3× further than France to the *same* semi-final. Totals include each team's dashed upcoming trip to its semi venue; they exclude travel from the home country to North America before the tournament.

## Regenerate the poster (any machine)
```bash
pip install playwright pillow
python -m playwright install chromium
cd social && python capture.py poster_hero.html wc2026_final_four_hero.png 1600 970
```

## Draft LinkedIn comment (post manually — I don't auto-post on your behalf)
> Couldn't resist running the numbers on this 😄 I built a live WC2026 dashboard that tracks every team's mileage across the host cities. Just to reach this week's semis:
> 🇪🇸 Spain — 10,374 km · 🏴󠁧󠁢󠁥󠁮󠁧󠁿 England — 9,171 km · 🇦🇷 Argentina — 5,644 km · 🇫🇷 France — 3,859 km
> Spain has flown almost 3× further than France to reach the same semi-final. ✈️
> (Host-city legs only — excludes each team's flight from home to North America before the tournament. Dashed lines = this week's semi-final trip.)
> ponienc.github.io/wc2026_dashboard

## Notes / gotchas
- The poster uses flagcdn.com flag images; emoji regional-indicator flags do NOT render on Windows.
- LinkedIn comments accept a still image or a Tenor-library GIF only — not an uploaded video/GIF. Video works only as a top-level post.
- Pages deploys straight from `main`; there is also a scheduled Action (`.github/workflows/refresh_fifa_data.yml`) that refreshes cached data — leave it alone (the active token lacks `workflow` scope).
