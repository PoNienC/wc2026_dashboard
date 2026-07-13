# social — LinkedIn assets

Poster for a LinkedIn reply about the WC2026 final four's air miles to reach the semi-finals.

- `poster_hero.html` — self-contained Leaflet poster. Route data and per-team km are **hardcoded** here (taken from the dashboard's Travel tracker on 13 Jul 2026). Edit this to change the design.
- `capture.py` — Playwright headless renderer → PNG.
- `wc2026_final_four_hero.png` — the rendered image, 1600×970 (landscape, @2×).

## Regenerate
```bash
pip install playwright pillow
python -m playwright install chromium
python capture.py poster_hero.html wc2026_final_four_hero.png 1600 970
```

## Design notes
- National-flag colours; routes are thin and offset per city-pair (via a canonical bow orientation) so a leg flown both ways separates instead of overlapping.
- Dashed line = the upcoming semi-final trip. Flags sit at the semi venues (Spain + France → Dallas; England + Argentina → Atlanta).
- Uses flagcdn.com images for flags (emoji flags don't render on Windows).
