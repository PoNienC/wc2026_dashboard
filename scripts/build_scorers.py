#!/usr/bin/env python3
"""Regenerate scorers.json — every goal of WC2026, credited via FIFA's per-match feed.

Why: the worldcup26.ir /games feed hand-types scorer names and garbles many of them
("Hri Kin" for Harry Kane, "Jvd Blingham" for Jude Bellingham — ~29% of entries have
surnames matching no squad player). The dashboard aggregated goals by surname, so one
player split into several Golden Boot entries. FIFA's match details carry stable player
ids and clean names, so totals aggregate correctly no matter how names are spelt.

Source (both CORS-open, also used live by the app):
  - api.fifa.com .../calendar/matches?idCompetition=17&idSeason=285023 — match list;
    MatchStatus 0 = finished (only finished matches are baked).
  - api.fifa.com .../live/football/17/285023/{IdStage}/{IdMatch} — per-match detail:
    Home/AwayTeam.Goals[] ({Type, Period, IdPlayer, Minute}) + Players[] (id -> name).

Goal semantics (verified empirically against known matches):
  Type 1 = penalty · Type 2 = open play · Period 11 = penalty-shootout kick.
  Only Type 1/2 outside Period 11 count (shootout kicks and any other event types --
  e.g. own goals -- are excluded from scorer tallies, matching Golden Boot rules).

Output: ../scorers.json (committed — the app serves it, then tops up any matches that
finished after the bake straight from FIFA in the browser). Content is deterministic
(no timestamp) so the refresh Action only commits when the goals actually change:
  {"meta": {"matches": [<MatchNumber baked>...], "goals": N},
   "goals": [{"m": 22, "f": "ENG", "pid": "369419", "n": "Harry Kane", "pen": 1}, ...]}

Usage:  python3 scripts/build_scorers.py [--dry-run]
  --dry-run  list the matches that would be fetched; write nothing.
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept": "application/json"}

FIFA_API = "https://api.fifa.com/api/v3"
CALENDAR = (f"{FIFA_API}/calendar/matches"
            "?idCompetition=17&idSeason=285023&count=500&language=en")
DETAIL = f"{FIFA_API}/live/football/17/285023/{{stage}}/{{match}}?language=en"
GOAL_TYPES = {1, 2}       # 1 = penalty, 2 = open play
SHOOTOUT_PERIOD = 11      # shootout kicks never count as goals scored
THROTTLE_S = 0.15
RETRIES = 3

OUT = pathlib.Path(__file__).resolve().parent.parent / "scorers.json"


def fetch_json(url: str) -> dict:
    """GET a FIFA endpoint with a browser UA, retrying transient failures."""
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception as e:                                  # noqa: BLE001 — retried, then re-raised
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url} failed after {RETRIES} attempts: {last}")


def clean_name(raw: str) -> str:
    """FIFA capitalises surnames ("Harry KANE") — title-case the shouting tokens."""
    def fix(token: str) -> str:
        if len(token) > 1 and token == token.upper():
            return "".join(p if p in "-'" else p.capitalize()
                           for p in __import__("re").split(r"([-'])", token))
        return token
    return " ".join(fix(t) for t in str(raw or "").split())


def loc(name_arr: object, fallback: str = "") -> str:
    """First localised Description from a FIFA name array."""
    if isinstance(name_arr, list) and name_arr:
        return name_arr[0].get("Description") or fallback
    return fallback


def extract_goals(detail: dict, match_number: int) -> list[dict]:
    """Scorer-credited goals from one match detail, in file row shape."""
    rows: list[dict] = []
    for side in ("HomeTeam", "AwayTeam"):
        team = detail.get(side) or {}
        names = {p.get("IdPlayer"): loc(p.get("ShortName")) or loc(p.get("PlayerName"))
                 for p in (team.get("Players") or [])}
        for g in (team.get("Goals") or []):
            if g.get("Type") not in GOAL_TYPES or g.get("Period") == SHOOTOUT_PERIOD:
                continue
            rows.append({"m": match_number, "f": team.get("IdCountry"),
                         "pid": str(g.get("IdPlayer")),
                         "n": clean_name(names.get(g.get("IdPlayer"), "")),
                         "pen": 1 if g.get("Type") == 1 else 0})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="list matches; write nothing")
    args = ap.parse_args()

    matches = fetch_json(CALENDAR).get("Results") or []
    done = [m for m in matches
            if m.get("MatchNumber") and m.get("MatchStatus") == 0
            and m.get("IdStage") and m.get("IdMatch")]
    done.sort(key=lambda m: m["MatchNumber"])
    print(f"{len(done)} finished match(es) to bake")
    if args.dry_run:
        for m in done:
            print(f"  M{m['MatchNumber']}")
        return 0

    goals: list[dict] = []
    for i, m in enumerate(done, 1):
        num = m["MatchNumber"]
        detail = fetch_json(DETAIL.format(stage=m["IdStage"], match=m["IdMatch"]))
        rows = extract_goals(detail, num)
        goals.extend(rows)
        print(f"  [{i}/{len(done)}] M{num}: {len(rows)} goal(s)")
        time.sleep(THROTTLE_S)

    goals.sort(key=lambda g: (g["m"], g["f"], g["pid"]))
    out = {"meta": {"matches": [m["MatchNumber"] for m in done], "goals": len(goals)},
           "goals": goals}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT.name}: {len(goals)} goals across {len(done)} matches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
