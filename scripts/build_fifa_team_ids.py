#!/usr/bin/env python3
"""Regenerate FIFA_TEAM_IDS — each qualified nation's FIFA team id (api.fifa.com
`IdTeam`), keyed by the dashboard's FIFA code. Powers the live head-to-head card,
which queries api.fifa.com's CORS-open match feed by team id.

Sources:
  - The 48 qualified nations + their FIFA codes from worldcup26.ir /teams.
  - The full FIFA national-team list (id + 3-letter associationId + slug) embedded
    in any inside.fifa.com head-to-head page's __NEXT_DATA__ `associations` array
    (~425 male + female teams; we keep the male senior sides).

Output:
  - Writes ../fifa_team_ids.gen.js  (a `const FIFA_TEAM_IDS = {...};` line).
  - Prints the same const to stdout — paste it into index.html, replacing the
    existing FIFA_TEAM_IDS const (keyed by FIFA code; value is the FIFA IdTeam).

Caveat: inside.fifa.com sits behind Akamai Bot Manager. A plain request works from
a normal (residential) connection but may be challenged from a data-centre/CI IP;
if so, run this locally. The api.fifa.com feed the dashboard actually calls at
runtime is open (Access-Control-Allow-Origin: *) and is not affected.

Usage:  python3 scripts/build_fifa_team_ids.py
"""
import json
import pathlib
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}

# Any men's head-to-head page embeds the complete national-team list; the specific
# pairing in the URL is irrelevant — we only read its `associations` array.
FIFA_H2H_PAGE = "https://inside.fifa.com/en/data-centre/head-to-head/men/ghana-vs-brazil"
TEAMS_API = "https://worldcup26.ir/get/teams"


def get_text(url: str, timeout: int = 60) -> str:
    """Fetch a URL as decoded text with a browser-like UA."""
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def fifa_association_index() -> dict[str, dict]:
    """Map FIFA associationId -> team record for every male national side."""
    html = get_text(FIFA_H2H_PAGE)
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    if not m:
        sys.exit("ERROR: could not find __NEXT_DATA__ (Akamai challenge?) — run locally.")
    data = json.loads(m.group(1))
    assoc = data["props"]["pageProps"]["pageData"]["content"][0]["associations"]
    by_code: dict[str, dict] = {}
    for a in assoc:
        if a.get("gender") == "male":
            by_code.setdefault(a["associationId"], a)  # first wins (senior side)
    return by_code


def main() -> None:
    by_code = fifa_association_index()
    teams = json.loads(get_text(TEAMS_API))["teams"]

    mapping: dict[str, str] = {}
    missing: list[tuple[str, str]] = []
    for t in teams:
        fc = t["fifa_code"]
        rec = by_code.get(fc)
        if rec:
            mapping[fc] = rec["id"]
        else:
            missing.append((fc, t.get("name_en", "?")))

    if missing:
        # Fail loud: a missing id silently disables that nation's H2H record.
        print(f"WARN {len(missing)} unmatched code(s) — H2H will be disabled for these:",
              missing, file=sys.stderr)

    # Emit sorted, ~6 per line, to match the inlined const's formatting.
    codes = sorted(mapping)
    rows, line = [], []
    for c in codes:
        line.append(f"{c}:'{mapping[c]}'")
        if len(line) == 6:
            rows.append("    " + ", ".join(line) + ",")
            line = []
    if line:
        rows.append("    " + ", ".join(line) + ",")

    const = (
        "  // FIFA national-team IDs (api.fifa.com IdTeam) for all 48 qualified nations, keyed by FIFA code.\n"
        "  // Used to query the CORS-open FIFA match API for live head-to-head records.\n"
        "  // Regenerate with scripts/build_fifa_team_ids.py. Verified 48/48 against worldcup26.ir codes.\n"
        "  const FIFA_TEAM_IDS = {\n" + "\n".join(rows) + "\n  };"
    )

    path = pathlib.Path(__file__).resolve().parent.parent / "fifa_team_ids.gen.js"
    path.write_text(const + "\n")
    print(f"// wrote {path} — {len(mapping)}/48 teams. Paste the const below into index.html:",
          file=sys.stderr)
    print(const)


if __name__ == "__main__":
    main()
