#!/usr/bin/env python3
"""Regenerate SQUAD_LEAGUES — each nation's 26-man squad grouped by the
country/league of every player's club ("Where the squad plays" bar chart).

Sources:
  - Wikipedia "2026 FIFA World Cup squads" wikitext: every {{nat fs g player}}
    template carries `clubnat=XXX` (the club's country, a FIFA-style code).
  - Team identity (section name -> dashboard FIFA code) from worldcup26.ir /teams.

Output:
  - Writes ../squad_leagues.gen.js  (a `const SQUAD_LEAGUES = {...};` line).
  - Prints the same const to stdout — paste it into index.html, replacing the
    existing SQUAD_LEAGUES const (keyed by FIFA code; rows are {lg, c, n}).

Note: facts (player counts) are not copyrightable; we credit Wikipedia in the UI.

Usage:  python3 scripts/build_squad_leagues.py
"""
import json
import pathlib
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict

UA = {"User-Agent": "wc2026-dashboard/1.0 (regeneration script)"}

# Club-country FIFA code -> (league label, flag iso2). Long tail falls back to the code.
LG = {
    "ENG": ("Premier League", "gb-eng"), "GER": ("Bundesliga", "de"), "ESP": ("La Liga", "es"),
    "FRA": ("Ligue 1", "fr"), "ITA": ("Serie A", "it"), "KSA": ("Saudi Pro League", "sa"),
    "TUR": ("Süper Lig", "tr"), "USA": ("MLS", "us"), "NED": ("Eredivisie", "nl"),
    "BRA": ("Brazil Série A", "br"), "POR": ("Primeira Liga", "pt"), "BEL": ("Belgian Pro", "be"),
    "QAT": ("Qatar Stars", "qa"), "MEX": ("Liga MX", "mx"), "CZE": ("Czech Liga", "cz"),
    "IRN": ("Persian Gulf PL", "ir"), "SCO": ("Scottish Prem", "gb-sct"), "EGY": ("Egyptian PL", "eg"),
    "RSA": ("PSL (South Africa)", "za"), "ARG": ("Liga Argentina", "ar"), "UZB": ("Uzbek Super", "uz"),
    "UAE": ("UAE Pro League", "ae"), "IRQ": ("Iraq Stars", "iq"), "DEN": ("Danish Superliga", "dk"),
    "GRE": ("Super League Greece", "gr"), "RUS": ("Russian PL", "ru"), "SUI": ("Swiss Super", "ch"),
    "JOR": ("Jordan Pro", "jo"), "CYP": ("Cypriot First", "cy"), "NZL": ("New Zealand", "nz"),
    "KOR": ("K League", "kr"), "AUT": ("Austrian BL", "at"), "NOR": ("Eliteserien", "no"),
    "JPN": ("J1 League", "jp"), "AUS": ("A-League", "au"), "TUN": ("Tunisian L1", "tn"),
    "CRO": ("HNL (Croatia)", "hr"), "CAN": ("Canadian PL", "ca"), "WAL": ("Wales", "gb-wls"),
    "POL": ("Ekstraklasa", "pl"), "ECU": ("Ecuador Serie A", "ec"), "ISR": ("Israeli PL", "il"),
    "SWE": ("Allsvenskan", "se"), "HUN": ("Hungary NB I", "hu"), "MAR": ("Botola", "ma"),
    "PAR": ("Paraguay Primera", "py"), "MAS": ("Malaysia SL", "my"), "ALG": ("Algeria L1", "dz"),
    "SRB": ("Serbian SuperLiga", "rs"), "ROU": ("Romania Liga I", "ro"), "SVK": ("Slovak SL", "sk"),
    "SVN": ("Slovenian PL", "si"), "IRL": ("League of Ireland", "ie"), "BUL": ("Bulgaria First", "bg"),
    "CRC": ("Costa Rica Primera", "cr"), "VEN": ("Venezuela", "ve"), "PAN": ("Panama", "pa"),
    "CHI": ("Chile Primera", "cl"), "CHN": ("Chinese SL", "cn"), "BIH": ("Bosnia Premier", "ba"),
    "KAZ": ("Kazakhstan PL", "kz"), "HAI": ("Haiti", "ht"), "FIN": ("Veikkausliiga", "fi"),
    "THA": ("Thai League", "th"), "IDN": ("Liga 1 (IDN)", "id"), "COL": ("Colombia Primera", "co"),
    "ARM": ("Armenia", "am"), "GHA": ("Ghana PL", "gh"), "URU": ("Uruguay Primera", "uy"),
    "HON": ("Honduras", "hn"), "AZE": ("Azerbaijan PL", "az"),
}

SQUADS_WIKITEXT = ("https://en.wikipedia.org/w/api.php?action=parse"
                   "&page=2026_FIFA_World_Cup_squads&prop=wikitext&format=json&formatversion=2")


def get_json(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read())


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def main() -> None:
    # 1) team section name -> dashboard FIFA code
    teams = get_json("https://worldcup26.ir/get/teams")["teams"]
    name2fifa = {norm(t["name_en"]): t["fifa_code"] for t in teams}
    # Wikipedia section names that differ from the API's name_en.
    alias = {"drcongo": "democraticrepublicofthecongo"}

    def team_fifa(wikiname):
        k = norm(wikiname)
        if k in name2fifa:
            return name2fifa[k]
        if k in alias and alias[k] in name2fifa:
            return name2fifa[alias[k]]
        for nk, fc in name2fifa.items():
            if nk == k or nk in k or k in nk:
                return fc
        return None

    # 2) parse the squads wikitext into per-team club-country counts
    wt = get_json(SQUADS_WIKITEXT)["parse"]["wikitext"]
    teams_counts = defaultdict(Counter)
    cur = None
    for line in wt.splitlines():
        s = line.strip()
        h3 = re.match(r"^===([^=].*?[^=])===$", s)
        h2 = re.match(r"^==([^=].*?[^=])==$", s)
        if h3:
            nm = h3.group(1).strip()
            cur = None if nm.lower().startswith("group") else nm
            continue
        if h2:
            cur = None
            continue
        for code in re.findall(r"clubnat=([A-Za-z]{2,3})", line):
            if cur:
                teams_counts[cur][code.upper()] += 1

    # 3) build output keyed by FIFA code
    out, unmatched, unmapped = {}, [], set()
    for wikiname, cnt in teams_counts.items():
        fc = team_fifa(wikiname)
        if not fc:
            unmatched.append(wikiname)
            continue
        rows = []
        for code, n in cnt.most_common():
            if code not in LG:
                unmapped.add(code)
            lg, c = LG.get(code, (code, ""))
            rows.append({"lg": lg, "c": c, "n": n})
        out[fc] = rows

    if unmatched:
        print("WARN unmatched team sections:", unmatched, file=sys.stderr)
    if unmapped:
        print("WARN unmapped club-country codes (fell back to raw code):", sorted(unmapped), file=sys.stderr)

    js = "const SQUAD_LEAGUES = " + json.dumps(out, ensure_ascii=False) + ";"
    path = pathlib.Path(__file__).resolve().parent.parent / "squad_leagues.gen.js"
    path.write_text(js + "\n")
    print(f"// wrote {path} — {len(out)}/48 teams. Paste the const below into index.html:", file=sys.stderr)
    print(js)


if __name__ == "__main__":
    main()
