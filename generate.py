#!/usr/bin/env python3
"""
WK 2026 overzicht-generator.
Haalt uitslagen en standen op via football-data.org en schrijft index.html.

Vereist env var: FOOTBALL_DATA_TOKEN (gratis account op football-data.org)
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

API = "https://api.football-data.org/v4/competitions/2000"  # FIFA World Cup
TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "")
TZ = ZoneInfo("Europe/Amsterdam")
MAANDEN = ["jan", "feb", "mrt", "apr", "mei", "jun",
           "jul", "aug", "sep", "okt", "nov", "dec"]

# Engelse API-namen -> Nederlandse namen
NL = {
    "South Africa": "Zuid-Afrika", "Korea Republic": "Zuid-Korea",
    "South Korea": "Zuid-Korea", "Czechia": "Tsjechië",
    "Czech Republic": "Tsjechië", "Bosnia and Herzegovina": "Bosnië-Herzegovina",
    "Bosnia-Herzegovina": "Bosnië-Herzegovina", "Switzerland": "Zwitserland",
    "Brazil": "Brazilië", "Morocco": "Marokko", "Haiti": "Haïti",
    "Scotland": "Schotland", "United States": "Verenigde Staten",
    "USA": "Verenigde Staten", "Australia": "Australië",
    "Türkiye": "Turkije", "Turkey": "Turkije", "Germany": "Duitsland",
    "Curacao": "Curaçao", "Ivory Coast": "Ivoorkust",
    "Côte d'Ivoire": "Ivoorkust", "Netherlands": "Nederland",
    "Sweden": "Zweden", "Tunisia": "Tunesië", "Belgium": "België",
    "Egypt": "Egypte", "IR Iran": "Iran", "New Zealand": "Nieuw-Zeeland",
    "Spain": "Spanje", "Cape Verde": "Kaapverdië", "Cabo Verde": "Kaapverdië",
    "Cape Verde Islands": "Kaapverdië", "Saudi Arabia": "Saoedi-Arabië",
    "France": "Frankrijk", "Norway": "Noorwegen", "Iraq": "Irak",
    "Argentina": "Argentinië", "Algeria": "Algerije",
    "Austria": "Oostenrijk", "Jordan": "Jordanië",
    "Uzbekistan": "Oezbekistan", "DR Congo": "DR Congo",
    "Congo DR": "DR Congo", "England": "Engeland", "Croatia": "Kroatië",
}

FLAGS = {
    "Mexico": "🇲🇽", "Zuid-Afrika": "🇿🇦", "Zuid-Korea": "🇰🇷", "Tsjechië": "🇨🇿",
    "Canada": "🇨🇦", "Bosnië-Herzegovina": "🇧🇦", "Qatar": "🇶🇦", "Zwitserland": "🇨🇭",
    "Brazilië": "🇧🇷", "Marokko": "🇲🇦", "Haïti": "🇭🇹", "Schotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Verenigde Staten": "🇺🇸", "Paraguay": "🇵🇾", "Australië": "🇦🇺", "Turkije": "🇹🇷",
    "Duitsland": "🇩🇪", "Curaçao": "🇨🇼", "Ivoorkust": "🇨🇮", "Ecuador": "🇪🇨",
    "Nederland": "🇳🇱", "Japan": "🇯🇵", "Zweden": "🇸🇪", "Tunesië": "🇹🇳",
    "België": "🇧🇪", "Egypte": "🇪🇬", "Iran": "🇮🇷", "Nieuw-Zeeland": "🇳🇿",
    "Spanje": "🇪🇸", "Kaapverdië": "🇨🇻", "Saoedi-Arabië": "🇸🇦", "Uruguay": "🇺🇾",
    "Frankrijk": "🇫🇷", "Senegal": "🇸🇳", "Noorwegen": "🇳🇴", "Irak": "🇮🇶",
    "Argentinië": "🇦🇷", "Algerije": "🇩🇿", "Oostenrijk": "🇦🇹", "Jordanië": "🇯🇴",
    "Portugal": "🇵🇹", "Oezbekistan": "🇺🇿", "Colombia": "🇨🇴", "DR Congo": "🇨🇩",
    "Engeland": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Kroatië": "🇭🇷", "Ghana": "🇬🇭", "Panama": "🇵🇦",
}

STAGES = [
    ("LAST_32", "Zestiende finales"),
    ("LAST_16", "Achtste finales"),
    ("QUARTER_FINALS", "Kwartfinales"),
    ("SEMI_FINALS", "Halve finales"),
    ("THIRD_PLACE", "Troostfinale"),
    ("FINAL", "Finale"),
]


def nl_name(team):
    if not team:
        return None
    raw = team.get("name") or team.get("shortName")
    if not raw:
        return None
    return NL.get(raw, raw)


def flag(name):
    return FLAGS.get(name, "")


def fetch(path):
    r = requests.get(API + path, headers={"X-Auth-Token": TOKEN}, timeout=30)
    r.raise_for_status()
    return r.json()


def fmt_when(utc_date):
    dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00")).astimezone(TZ)
    return f"{dt.day} {MAANDEN[dt.month - 1]}", dt.strftime("%H:%M")


def match_row(m, highlight_nl=True):
    home, away = nl_name(m["homeTeam"]), nl_name(m["awayTeam"])
    home_lbl = home or "Nog te bepalen"
    away_lbl = away or "Nog te bepalen"
    datum, tijd = fmt_when(m["utcDate"])
    status = m["status"]
    ft = m.get("score", {}).get("fullTime", {})
    played = status == "FINISHED" and ft.get("home") is not None
    live = status in ("IN_PLAY", "PAUSED")

    if played:
        score = f'<div class="m-score">{ft["home"]}–{ft["away"]}</div>'
    elif live and ft.get("home") is not None:
        score = f'<div class="m-score live">{ft["home"]}–{ft["away"]}</div>'
    else:
        score = '<div class="m-score tbd">— : —</div>'

    def nm(n):
        if highlight_nl and n == "Nederland":
            return f'<span class="nl-name">{n}</span>'
        return n

    return f'''<div class="match {"played" if played else ""}">
      <div class="m-when"><b>{datum}</b>{tijd}</div>
      <div class="m-teams">{flag(home)} {nm(home_lbl)}<br>{flag(away)} {nm(away_lbl)}</div>
      {score}
    </div>'''


def build_groups(matches, standings):
    # standen per groep uit de API
    tables = {}
    for s in standings.get("standings", []):
        if s.get("type") == "TOTAL" and s.get("group"):
            tables[s["group"]] = s["table"]

    group_matches = {}
    for m in matches:
        g = m.get("group")
        if g:
            group_matches.setdefault(g, []).append(m)

    html, played_count = [], 0
    for g in sorted(group_matches):
        letter = g.replace("GROUP_", "")
        ms = sorted(group_matches[g], key=lambda x: x["utcDate"])
        played_count += sum(
            1 for m in ms
            if m["status"] == "FINISHED"
            and m.get("score", {}).get("fullTime", {}).get("home") is not None
        )

        rows = []
        for e in tables.get(g, []):
            name = nl_name(e["team"]) or "?"
            ds = e.get("goalDifference", 0)
            cls = "nl-team" if name == "Nederland" else ""
            rows.append(
                f'<tr class="{cls}"><td class="team"><span class="flag">'
                f'{flag(name)}</span>{name}</td><td>{e.get("playedGames", 0)}</td>'
                f'<td>{"+" if ds > 0 else ""}{ds}</td>'
                f'<td class="pts">{e.get("points", 0)}</td></tr>'
            )

        is_nl = any('nl-team' in r for r in rows)
        html.append(f'''
    <div class="group-card {"nl" if is_nl else ""}">
      <div class="group-head">
        <div class="group-letter">{letter}</div>
        <div class="group-label">Groep {letter}</div>
      </div>
      <table class="stand">
        <tr><th>Land</th><th>G</th><th>DS</th><th>Ptn</th></tr>
        {"".join(rows)}
      </table>
      <div class="matches">{"".join(match_row(m) for m in ms)}</div>
    </div>''')
    return "".join(html), played_count


def build_knockout(matches):
    by_stage = {}
    for m in matches:
        if m.get("stage") and m["stage"] != "GROUP_STAGE":
            by_stage.setdefault(m["stage"], []).append(m)

    html, ko_played = [], 0
    for key, title in STAGES:
        ms = sorted(by_stage.get(key, []), key=lambda x: x["utcDate"])
        if not ms:
            continue
        ko_played += sum(1 for m in ms if m["status"] == "FINISHED")
        rows = "".join(match_row(m) for m in ms)
        cls = "ko-final" if key == "FINAL" else ""
        html.append(
            f'<div class="ko-card {cls}"><h3>{title}</h3>'
            f'<div class="matches">{rows}</div></div>'
        )
    return "".join(html), ko_played


TEMPLATE = """<!DOCTYPE html>
<html lang="nl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WK 2026 · Speelschema & Uitslagen</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Archivo:wght@400;500;600;700&family=Caveat:wght@600;700&display=swap" rel="stylesheet">
<style>
  :root{--paper:#F4F6F2;--card:#FFF;--ink:#14201A;--ink-soft:#5C6A61;--line:#DDE3DA;--oranje:#F05A1A;--pen:#2244C8;--groen:#1E7A4C;}
  *{margin:0;padding:0;box-sizing:border-box;}
  body{background:var(--paper);color:var(--ink);font-family:'Archivo',sans-serif;-webkit-font-smoothing:antialiased;}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 18px 60px;}
  header{border-bottom:3px solid var(--ink);padding-bottom:18px;margin-bottom:10px;}
  .eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--ink-soft);font-weight:600;margin-bottom:6px;}
  h1{font-family:'Anton',sans-serif;font-size:clamp(38px,7vw,72px);line-height:.95;text-transform:uppercase;}
  h1 .accent{color:var(--oranje);}
  .statusline{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:14px;font-size:13.5px;color:var(--ink-soft);}
  .statusline b{color:var(--ink);font-weight:600;}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--groen);margin-right:6px;vertical-align:1px;}
  .legend{display:flex;flex-wrap:wrap;gap:8px 20px;font-size:12.5px;color:var(--ink-soft);padding:12px 0 26px;}
  .legend .pen-demo{font-family:'Caveat',cursive;font-size:19px;font-weight:700;color:var(--pen);}
  .legend .nl-demo{color:var(--oranje);font-weight:700;}
  .groups,.ko-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:18px;}
  .group-card,.ko-card{background:var(--card);border:1.5px solid var(--line);border-radius:10px;padding:18px 18px 14px;position:relative;}
  .group-card.nl{border:2px solid var(--oranje);box-shadow:0 4px 18px rgba(240,90,26,.13);}
  .group-card.nl::after{content:"ORANJE";position:absolute;top:-1px;right:14px;background:var(--oranje);color:#fff;font-size:10px;font-weight:700;letter-spacing:.14em;padding:4px 9px 3px;border-radius:0 0 6px 6px;}
  .group-head{display:flex;align-items:baseline;gap:10px;border-bottom:1.5px solid var(--ink);padding-bottom:8px;margin-bottom:10px;}
  .group-letter{font-family:'Anton',sans-serif;font-size:30px;line-height:1;}
  .group-card.nl .group-letter{color:var(--oranje);}
  .group-label{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-soft);font-weight:600;}
  table.stand{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:12px;}
  table.stand th{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);font-weight:600;text-align:right;padding:2px 0 5px;}
  table.stand th:first-child{text-align:left;}
  table.stand td{padding:3.5px 0;border-top:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums;}
  table.stand td.team{text-align:left;font-weight:500;}
  table.stand td.pts{font-weight:700;}
  table.stand tr.nl-team td.team{color:var(--oranje);font-weight:700;}
  .flag{margin-right:6px;}
  .matches{font-size:13.5px;}
  .match{display:grid;grid-template-columns:74px 1fr 56px;align-items:center;gap:6px;padding:6px 0;border-top:1px dashed var(--line);}
  .match:first-child{border-top:none;}
  .m-when{font-size:11.5px;color:var(--ink-soft);line-height:1.3;}
  .m-when b{color:var(--ink);font-weight:600;display:block;}
  .m-teams{line-height:1.35;}
  .m-teams .nl-name{color:var(--oranje);font-weight:700;}
  .m-score{text-align:center;font-family:'Caveat',cursive;font-size:23px;font-weight:700;color:var(--pen);transform:rotate(-3deg);}
  .m-score.tbd{font-family:'Archivo',sans-serif;font-size:12px;color:#B6BFB6;transform:none;letter-spacing:.05em;}
  .m-score.live{color:var(--groen);}
  .match.played{background:linear-gradient(90deg,transparent,rgba(34,68,200,.045) 45%,transparent);}
  .section-title{font-family:'Anton',sans-serif;font-size:clamp(26px,4vw,38px);text-transform:uppercase;margin:54px 0 6px;}
  .section-sub{font-size:13.5px;color:var(--ink-soft);margin-bottom:20px;max-width:720px;}
  .ko-card h3{font-size:12px;letter-spacing:.16em;text-transform:uppercase;border-bottom:1.5px solid var(--ink);padding-bottom:7px;margin-bottom:8px;}
  .ko-final{border:2px solid var(--ink);}
  .ko-final h3{color:var(--oranje);border-color:var(--oranje);}
  footer{margin-top:50px;padding-top:16px;border-top:1.5px solid var(--line);font-size:12px;color:var(--ink-soft);}
  @media (max-width:420px){.match{grid-template-columns:64px 1fr 48px;}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">FIFA World Cup · Verenigde Staten — Canada — Mexico</div>
    <h1>WK 2026<span class="accent">.</span> Speelschema &amp; uitslagen</h1>
    <div class="statusline">
      <span><span class="dot"></span><b>Toernooi loopt</b> · 11 juni — 19 juli</span>
      <span>Bijgewerkt: <b>__UPDATED__</b></span>
      <span>Gespeeld: <b>__PLAYED__</b> van 104 wedstrijden</span>
    </div>
  </header>
  <div class="legend">
    <span><span class="pen-demo">2–0</span>&nbsp; uitslag (gespeeld)</span>
    <span><b style="color:#B6BFB6;font-weight:600;">— : —</b>&nbsp; nog te spelen</span>
    <span><span class="nl-demo">Nederland</span>&nbsp; wedstrijden van Oranje</span>
    <span>Alle tijden zijn Nederlandse tijd</span>
  </div>
  <div class="groups">__GROUPS__</div>
  <h2 class="section-title">Knock-outfase</h2>
  <p class="section-sub">Vanaf 28 juni. De nummers 1 en 2 van elke groep plaatsen zich, plus de acht beste nummers 3 — in totaal 32 landen.</p>
  <div class="ko-grid">__KO__</div>
  <footer>Automatisch bijgewerkt via GitHub Actions · Data: football-data.org · Tijden in Nederlandse tijd</footer>
</div>
</body>
</html>
"""


def main():
    if not TOKEN:
        print("FOUT: zet FOOTBALL_DATA_TOKEN als environment variable / repo secret.")
        sys.exit(1)

    matches = fetch("/matches")["matches"]
    standings = fetch("/standings")

    groups_html, played = build_groups(matches, standings)
    ko_html, ko_played = build_knockout(matches)

    updated = datetime.now(TZ).strftime("%d-%m-%Y %H:%M")
    html = (TEMPLATE
            .replace("__GROUPS__", groups_html)
            .replace("__KO__", ko_html)
            .replace("__UPDATED__", updated)
            .replace("__PLAYED__", str(played + ko_played)))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html geschreven · {played + ko_played} gespeelde wedstrijden")


if __name__ == "__main__":
    main()
