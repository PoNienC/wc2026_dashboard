#!/usr/bin/env python3
"""Regenerate squads.json — each nation's 26-man squad (player · position · club) and head
coach, parsed from the Wikipedia "2026 FIFA World Cup squads" page. Shown in the nation
detail panel (right-hand side) when a country is selected.

Sources:
  - Wikipedia "2026 FIFA World Cup squads" wikitext: each {{nat fs g/r player}} template
    carries no / pos / name / club / clubnat; each section starts with "Coach: [[Name]]".
  - Team section name -> dashboard FIFA code via worldcup26.ir /teams.

Output: ../squads.json keyed by FIFA code: {coach, players:[{no,n,p,c,cn}]}.
  n=name, p=position (GK/DF/MF/FW), c=club, cn=club country (FIFA-style code).

Facts (names / clubs) aren't copyrightable; Wikipedia is credited in the UI.

Usage:  python3 scripts/build_squads.py
"""
import json
import pathlib
import re
import sys
import unicodedata
import urllib.request

UA = {"User-Agent": "wc2026-dashboard/1.0 (regeneration script)"}
SQUADS_WT = ("https://en.wikipedia.org/w/api.php?action=parse"
             "&page=2026_FIFA_World_Cup_squads&prop=wikitext&format=json&formatversion=2")
TEAMS_API = "https://worldcup26.ir/get/teams"
POS_ORDER = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}


def get_json(url: str) -> dict:
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read())


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def wikilink(s: str) -> str:
    """[[Target|Display]] -> Display; [[Name]] -> Name; strip refs / flag invokes."""
    m = re.search(r"\[\[(.*?)\]\]", s or "")
    text = m.group(1).split("|")[-1] if m else (s or "")
    text = re.sub(r"<ref.*", "", text)            # drop trailing <ref> noise
    return text.strip()


def main() -> None:
    teams = get_json(TEAMS_API)["teams"]
    name2fifa = {norm(t["name_en"]): t["fifa_code"] for t in teams}
    alias = {"drcongo": "democraticrepublicofthecongo", "ivorycoast": "cotedivoire"}

    def team_fifa(nm: str):
        k = norm(nm)
        if k in name2fifa:
            return name2fifa[k]
        if k in alias and alias[k] in name2fifa:
            return name2fifa[alias[k]]
        for nk, fc in name2fifa.items():
            if nk == k or nk in k or k in nk:
                return fc
        return None

    wt = get_json(SQUADS_WT)["parse"]["wikitext"]
    # split into h3 sections: [pre, name1, body1, name2, body2, ...]
    parts = re.split(r"\n===([^=][^\n]*?)===\n", wt)

    out, unmatched = {}, []
    for i in range(1, len(parts), 2):
        name, body = parts[i].strip(), parts[i + 1]
        fc = team_fifa(name)
        if not fc:
            unmatched.append(name)
            continue
        cm = re.search(r"(?:head\s+coach|manager|coach)\s*:\s*([^\n]+)", body, re.I)
        coach = wikilink(cm.group(1)) if cm else ""

        players = []
        for blk in re.split(r"\{\{nat fs [gr] player", body)[1:]:
            nm = re.search(r"\bname=\s*(\[\[.*?\]\]|[^|\n]+)", blk)
            if not nm:
                continue
            pos = re.search(r"\bpos=\s*([A-Za-z]{2})", blk)
            club = re.search(r"\bclub=\s*(\[\[.*?\]\]|[^|\n}]+)", blk)
            no = re.search(r"\bno=\s*(\d+)", blk)
            cn = re.search(r"\bclubnat=\s*([A-Za-z]{2,3})", blk)
            players.append({
                "no": int(no.group(1)) if no else 0,
                "n": wikilink(nm.group(1)),
                "p": pos.group(1).upper() if pos else "",
                "c": wikilink(club.group(1)) if club else "",
                "cn": cn.group(1).upper() if cn else "",
            })
        players.sort(key=lambda p: (POS_ORDER.get(p["p"], 9), p["no"] or 99))
        out[fc] = {"coach": coach, "players": players}

    if unmatched:
        print("WARN unmatched sections:", unmatched, file=sys.stderr)
    short = {fc: len(s["players"]) for fc, s in out.items() if len(s["players"]) < 20}
    if short:
        print("WARN squads with <20 players (check parsing):", short, file=sys.stderr)

    path = pathlib.Path(__file__).resolve().parent.parent / "squads.json"
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
    total = sum(len(s["players"]) for s in out.values())
    print(f"// wrote {path} — {len(out)}/48 nations, {total} players, "
          f"{sum(1 for s in out.values() if s['coach'])} coaches.", file=sys.stderr)


if __name__ == "__main__":
    main()
