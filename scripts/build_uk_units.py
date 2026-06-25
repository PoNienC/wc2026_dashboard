#!/usr/bin/env python3
"""Regenerate uk_units.geojson — the four UK home-nation polygons.

The dashboard replaces the single GBR (United Kingdom) polygon with England,
Scotland, Wales & Northern Ireland so England (ENG) and Scotland (SCT) can be
highlighted/zoomed independently. Source: Natural Earth 1:50m admin-0 *map
units*. Each output feature's ADM0_A3 is set to the home-nation code (ENG/SCT/
WLS/NIR) so the dashboard's getIso3() matches it, with per-nation CONTINENT and
POP_EST carried through.

Usage:  python3 scripts/build_uk_units.py      # writes ../uk_units.geojson
"""
import json
import pathlib
import urllib.request

URL = ("https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@master/"
       "geojson/ne_50m_admin_0_map_units.geojson")


def main() -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": "wc2026-dashboard/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=90).read())
    uk = [f for f in data["features"] if f["properties"].get("ADM0_A3") == "GBR"]
    out = {"type": "FeatureCollection", "features": []}
    for f in uk:
        p = f["properties"]
        out["features"].append({
            "type": "Feature",
            "properties": {"ADM0_A3": p["SU_A3"], "NAME": p["SUBUNIT"],
                           "CONTINENT": "Europe", "POP_EST": p["POP_EST"]},
            "geometry": f["geometry"],
        })
    path = pathlib.Path(__file__).resolve().parent.parent / "uk_units.geojson"
    path.write_text(json.dumps(out, separators=(",", ":")))
    codes = [ft["properties"]["ADM0_A3"] for ft in out["features"]]
    print(f"wrote {path} ({path.stat().st_size} bytes): {codes}")


if __name__ == "__main__":
    main()
