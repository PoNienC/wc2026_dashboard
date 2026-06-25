#!/usr/bin/env python3
"""Regenerate h2h.json — head-to-head records for the knockout matchups that the
bracket has actually produced. Bracket-driven and incremental: it reads the same
live games feed the dashboard uses, finds the knockout ties where BOTH nations are
known, and bakes only those pairs. The full knockout is 32 matches, so this is at
most 32 FIFA calls (1 today, ~16 once the groups finish) — not the 1,128 of an
all-pairs bake.

Why pre-bake at all: FIFA's complete H2H lives behind inside.fifa.com's bot-walled,
non-CORS BFF, so a static site can't fetch it live. It works fine from a normal IP
(this script), so we bake it and the app loads the JSON. See HANDOVER.md.

Sources:
  - worldcup26.ir /get/{games,teams} — the live bracket + our 48 nations (FIFA codes).
  - inside.fifa.com/api/data-centre/head-to-head/head-to-head?teamA=&teamB=&language=en
    — FIFA's authoritative H2H: per-side aggregate (played, W/D/L, goals, clean sheets,
    counting shootout wins as wins) plus the full match list.

Records are keyed by sorted FIFA codes ("A|B", A < B) and oriented to that canonical A:
  {p, w:[winsA,draws,winsB], g:[gA,gB], cs:[csA,csB],
   wc:[wcWinsA,wcDraws,wcWinsB,wcPlayed], last:{...most recent meeting...}}

Output: ../h2h.json (committed — the app serves it). Existing pairs are preserved and
re-baked for freshness, so the file grows with the bracket.

Usage:  python3 scripts/build_h2h.py [--all] [--dry-run]
  --all      bake every pair among qualified nations (1,128) instead of bracket-only.
  --dry-run  list the pairs that would be baked; make no FIFA calls, write nothing.
"""
import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
from itertools import combinations

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept": "application/json"}

GAMES_API = "https://worldcup26.ir/get/games"
TEAMS_API = "https://worldcup26.ir/get/teams"
BFF = ("https://inside.fifa.com/api/data-centre/head-to-head/head-to-head"
       "?teamA={a}&teamB={b}&language=en")
THROTTLE_S = 0.4          # be gentle with the bot-walled endpoint
RETRIES = 4

# FIFA national-team IDs, keyed by FIFA code — regenerate with build_fifa_team_ids.py.
# Kept in sync with the FIFA_TEAM_IDS const in index.html (the BFF needs numeric ids).
FIFA_TEAM_IDS = {
    "ALG": "43843", "ARG": "43922", "AUS": "43976", "AUT": "43934", "BEL": "43935",
    "BIH": "44037", "BRA": "43924", "CAN": "43899", "CIV": "43854", "COD": "20014",
    "COL": "43926", "CPV": "43850", "CRO": "43938", "CUW": "1895293", "CZE": "43995",
    "ECU": "43927", "EGY": "43855", "ENG": "43942", "ESP": "43969", "FRA": "43946",
    "GER": "43948", "GHA": "43860", "HAI": "43908", "IRN": "43817", "IRQ": "43818",
    "JOR": "43820", "JPN": "43819", "KOR": "43822", "KSA": "43835", "MAR": "43872",
    "MEX": "43911", "NED": "43960", "NOR": "43961", "NZL": "43978", "PAN": "43914",
    "PAR": "43928", "POR": "43963", "QAT": "43834", "RSA": "43883", "SCO": "43967",
    "SEN": "43879", "SUI": "43971", "SWE": "43970", "TUN": "43888", "TUR": "43972",
    "URU": "43930", "USA": "43921", "UZB": "44005",
}


def get_json(url: str, timeout: int = 30) -> dict:
    """Fetch JSON with a browser-like UA, retrying transient/bot-wall failures."""
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))   # back off on 403 / timeout
    raise RuntimeError(f"failed after {RETRIES} attempts: {url} ({last})")


def _list(payload: dict, *keys: str) -> list:
    for k in keys:
        if isinstance(payload.get(k), list):
            return payload[k]
    return payload if isinstance(payload, list) else \
        next((v for v in payload.values() if isinstance(v, list)), [])


def determined_pairs() -> list[tuple[str, str]]:
    """Knockout ties (type != group) where both nations are currently known."""
    teams = _list(get_json(TEAMS_API), "teams", "data")
    by_id = {str(t["id"]): t["fifa_code"] for t in teams}
    games = _list(get_json(GAMES_API), "games", "data")
    pairs = set()
    for m in games:
        if str(m.get("type", "")).lower() == "group":
            continue
        h, a = str(m.get("home_team_id")), str(m.get("away_team_id"))
        if h in by_id and a in by_id:
            pairs.add(tuple(sorted((by_id[h], by_id[a]))))
    return sorted(pairs)


def is_world_cup(comp: str) -> bool:
    c = (comp or "").lower()
    return "world cup" in c and "qual" not in c   # finals only, not qualifiers


def compact_record(code_a: str, code_b: str, bff: dict) -> dict:
    """Build the canonical record (oriented to code_a, which is < code_b)."""
    ta, tb = bff["teamA"], bff["teamB"]
    # FIFA's teamA/teamB follow the request order; orient to our canonical A.
    if str(ta["idTeam"]) != FIFA_TEAM_IDS[code_a]:
        ta, tb = tb, ta
    id_a = str(ta["idTeam"])

    # World-Cup-only split, FIFA convention: the side that advances (shootout winner) wins.
    wc_a = wc_d = wc_b = wc_n = 0
    last = None
    for m in bff.get("matchesList", []):
        home, away = m["home"], m["away"]
        a_home = str(home["idTeam"]) == id_a
        sa = home["score"] if a_home else away["score"]
        sb = away["score"] if a_home else home["score"]
        if is_world_cup((m.get("competitionName") or {}).get("description", "")):
            wc_n += 1
            if m.get("hasPenalties"):
                pa = home["penaltyScore"] if a_home else away["penaltyScore"]
                pb = away["penaltyScore"] if a_home else home["penaltyScore"]
                win_a = pa > pb
                win_b = pb > pa
            else:
                win_a, win_b = sa > sb, sb > sa
            wc_a += win_a
            wc_b += win_b
            wc_d += not (win_a or win_b)
        d = m.get("date") or ""
        if not last or d > last["_d"]:
            hc = code_a if a_home else code_b
            ac = code_b if a_home else code_a
            pen = None
            if m.get("hasPenalties"):
                pen = {"hp": home["penaltyScore"], "ap": away["penaltyScore"],
                       "pw": (hc if home["penaltyScore"] > away["penaltyScore"] else ac)}
            last = {"_d": d, "date": d[:10], "h": hc, "a": ac,
                    "hs": home["score"], "as": away["score"],
                    "comp": (m.get("competitionName") or {}).get("description", ""),
                    "stage": (m.get("stageName") or {}).get("description", ""), "pen": pen}
    if last:
        last.pop("_d", None)

    return {
        "p": ta["matchesPlayed"],
        "w": [ta["wins"], ta["draws"], tb["wins"]],
        "g": [ta["goalsScored"], ta["goalsAgainst"]],
        "cs": [ta["cleanSheets"], tb["cleanSheets"]],
        "wc": [wc_a, wc_d, wc_b, wc_n],
        "last": last,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="bake all 1,128 pairs")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.all:
        pairs = sorted(combinations(sorted(FIFA_TEAM_IDS), 2))
    else:
        pairs = determined_pairs()
    print(f"// {len(pairs)} pair(s) to bake ({'all' if args.all else 'bracket-driven'})",
          file=sys.stderr)

    if args.dry_run:
        for a, b in pairs:
            print(f"   {a} vs {b}", file=sys.stderr)
        return

    out_path = pathlib.Path(__file__).resolve().parent.parent / "h2h.json"
    data = json.loads(out_path.read_text()) if out_path.exists() else {}

    ok = err = 0
    for i, (a, b) in enumerate(pairs, 1):
        url = BFF.format(a=FIFA_TEAM_IDS[a], b=FIFA_TEAM_IDS[b])
        try:
            rec = compact_record(a, b, get_json(url))
            data[f"{a}|{b}"] = rec
            ok += 1
            print(f"   [{i}/{len(pairs)}] {a}-{b}: played {rec['p']}", file=sys.stderr)
        except Exception as e:                              # noqa: BLE001 - log + continue
            err += 1
            print(f"   [{i}/{len(pairs)}] {a}-{b}: ERROR {e}", file=sys.stderr)
        time.sleep(THROTTLE_S)

    out_path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"// wrote {out_path} — {len(data)} pair(s) total ({ok} baked, {err} errored)",
          file=sys.stderr)
    if err:
        sys.exit(1)   # fail loud so the scheduled job surfaces problems


if __name__ == "__main__":
    main()
