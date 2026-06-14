#!/usr/bin/env python3
"""
WK 2026 overzicht-generator.
Haalt uitslagen en standen op via football-data.org en schrijft index.html.

Vereist env var: FOOTBALL_DATA_TOKEN (gratis account op football-data.org)
"""


import json
import os
import sys
from datetime import datetime, timedelta
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


# ── WK-poule ──────────────────────────────────────────────
PUNTEN_EXACT = 10   # uitslag precies goed
PUNTEN_TOTO = 5     # winnaar/gelijkspel goed

PLAYERS = []  # [{naam, kleur, voorspellingen{...}}]
PLAYER_COLORS = ["#F05A1A", "#2244C8", "#1E7A4C", "#8E44AD", "#C0392B"]
SUPABASE_URL = ""
SUPABASE_KEY = ""
SPELERS = ["Rick", "Rean", "Tung"]

def ai_bets_block(today_matches, datum):
    """Live AI-bets: per type een zoek-knop die de Supabase Edge Function aanroept."""
    if not (SUPABASE_URL and SUPABASE_KEY) or not today_matches:
        return ""
    cfg = {
        "url": SUPABASE_URL + "/functions/v1/ai-bet",
        "key": SUPABASE_KEY,
        "datum": datum,
        "wedstrijden": today_matches,
    }
    data = json.dumps(cfg, ensure_ascii=False).replace('"', "&quot;")
    return f'''
    <div class="ai-bets" data-aicfg="{data}">
      <div class="ai-bets-head">🤖 AI-bets <span class="ai-bets-sub">· live analyse op aanvraag</span></div>
      <div class="ai-bets-menu">
        <button class="ai-chip" type="button" data-bt="banker">🛡️ Veilige tip</button>
        <button class="ai-chip" type="button" data-bt="builder">🏗️ Bet builder</button>
        <button class="ai-chip" type="button" data-bt="combi">🔗 Combi van de dag</button>
        <button class="ai-chip" type="button" data-bt="longshot">🎲 Verrassing</button>
      </div>
      <div class="ai-bets-panel" id="ai-bets-panel" hidden></div>
      <div class="ai-bets-disc">Opus 4.8 zoekt live vorm, nieuws &amp; odds (~20s) · geen garantie, wed met mate</div>
    </div>'''


def load_predictions():
    """Leest poule.txt met de Supabase-gegevens:
    url=..., key=..., spelers=Rick,Rean,Tung (spelers optioneel)."""
    global SUPABASE_URL, SUPABASE_KEY, SPELERS
    if not os.path.exists("poule.txt"):
        return
    cfg = {}
    with open("poule.txt", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    SUPABASE_URL = cfg.get("url", "").rstrip("/")
    SUPABASE_KEY = cfg.get("key", "")
    if cfg.get("spelers"):
        SPELERS = [s.strip() for s in cfg["spelers"].split(",") if s.strip()]
    if SUPABASE_URL and SUPABASE_KEY:
        print(f"Poule actief · spelers: {', '.join(SPELERS)}")


def parse_pred(s):
    if not s or "-" not in str(s):
        return None
    try:
        h, u = str(s).replace("–", "-").split("-")
        return int(h.strip()), int(u.strip())
    except ValueError:
        return None


def pred_points(pred, ah, au):
    ph, pu = pred
    if ph == ah and pu == au:
        return PUNTEN_EXACT
    if (ph > pu and ah > au) or (ph < pu and ah < au) or (ph == pu and ah == au):
        return PUNTEN_TOTO
    return 0



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

    # data-attributen zodat de poule-JS deze wedstrijd kan koppelen
    key = f"{home} - {away}" if home and away else ""
    ts = int(datetime.fromisoformat(
        m["utcDate"].replace("Z", "+00:00")).timestamp() * 1000)
    res_attr = ""
    if played:
        res_attr = f' data-th="{ft["home"]}" data-tu="{ft["away"]}"'
    data = f' data-key="{key}" data-ts="{ts}"{res_attr}' if key else ""
    chips = f'<div class="chips" data-chips="{key}"></div>' if key else ""

    return f'''<div class="match {"played" if played else ""}"{data}>
      <div class="m-when"><b>{datum}</b>{tijd}</div>
      <div class="m-teams">{flag(home)} {nm(home_lbl)}<br>{flag(away)} {nm(away_lbl)}{chips}</div>
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


def build_poule(matches):
    if not (SUPABASE_URL and SUPABASE_KEY):
        return ""
    return f'''
  <div class="poule" id="poule">
    <div class="poule-head">
      <span class="poule-title">De Poule</span>
      <span class="poule-rules">exact = {PUNTEN_EXACT} ptn · toto = {PUNTEN_TOTO} ptn</span>
    </div>
    <div id="poule-stand"><div class="poule-loading">Stand laden…</div></div>
    <div class="poule-invul">
      <span class="poule-invul-label">Wie ben jij?</span>
      <div id="speler-keuze" class="speler-keuze"></div>
      <button id="invul-start" class="poule-btn" type="button" hidden>Voorspellingen invullen / wijzigen</button>
      <span id="invul-hint" class="poule-hint"></span>
    </div>
  </div>'''



DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag",
         "vrijdag", "zaterdag", "zondag"]
STAGE_LABEL = dict(STAGES)


def stage_or_group(m):
    g = m.get("group")
    if g:
        return f"Groep {g.replace('GROUP_', '')}"
    return STAGE_LABEL.get(m.get("stage"), "")


def build_today(matches):
    now = datetime.now(TZ)
    today = now.date()
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(hours=32)  # t/m 08:00 morgenvroeg

    def local_dt(m):
        return datetime.fromisoformat(
            m["utcDate"].replace("Z", "+00:00")).astimezone(TZ)

    todays = sorted([m for m in matches
                     if window_start <= local_dt(m) < window_end],
                    key=lambda x: x["utcDate"])

    header_date = f"{DAGEN[now.weekday()]} {now.day} {MAANDEN[now.month - 1]}"

    if not todays:
        upcoming = sorted([m for m in matches if local_dt(m) >= window_end],
                          key=lambda x: x["utcDate"])
        sub = "Geen wedstrijden vandaag — rustdag."
        if upcoming:
            nxt = local_dt(upcoming[0])
            sub = (f"Geen wedstrijden vandaag. Volgende speeldag: "
                   f"{DAGEN[nxt.weekday()]} {nxt.day} {MAANDEN[nxt.month - 1]}.")
        return f'''
  <div class="today">
    <div class="today-head">
      <span class="today-title">Vandaag</span>
      <span class="today-date">{header_date}</span>
    </div>
    <div class="today-empty">{sub}</div>
  </div>'''

    rows = []
    for m in todays:
        home, away = nl_name(m["homeTeam"]), nl_name(m["awayTeam"])
        home_lbl = home or "Nog te bepalen"
        away_lbl = away or "Nog te bepalen"
        dt = local_dt(m)
        tijd = dt.strftime("%H:%M")
        is_night = dt.date() > today
        when = (f'{tijd}<span class="t-night">vannacht</span>'
                if is_night else tijd)
        ft = m.get("score", {}).get("fullTime", {})
        status = m["status"]
        if status == "FINISHED" and ft.get("home") is not None:
            score = f'<span class="t-score">{ft["home"]}–{ft["away"]}</span>'
        elif status in ("IN_PLAY", "PAUSED") and ft.get("home") is not None:
            score = f'<span class="t-score t-live">{ft["home"]}–{ft["away"]} ●</span>'
        else:
            score = f'<span class="t-time">{tijd}</span>'
        nl_cls = " t-nl" if "Nederland" in (home, away) else ""
        rows.append(f'''
      <div class="today-row{nl_cls}">
        <div class="t-when">{when}</div>
        <div class="t-teams">{flag(home)} {home_lbl} — {away_lbl} {flag(away)}</div>
        <div class="t-meta">{stage_or_group(m)}</div>
        {score}
      </div>''')

    bet_matches = []
    for mm in todays:
        if mm["status"] in ("FINISHED", "IN_PLAY", "PAUSED"):
            continue
        h_nl, a_nl = nl_name(mm["homeTeam"]), nl_name(mm["awayTeam"])
        if not h_nl or not a_nl:
            continue
        bet_matches.append({
            "key": f"{h_nl} - {a_nl}", "home_nl": h_nl, "away_nl": a_nl,
            "home_en": (mm["homeTeam"] or {}).get("name"),
            "away_en": (mm["awayTeam"] or {}).get("name"),
            "tijd": local_dt(mm).strftime("%H:%M"),
        })
    return f'''
  <div class="today">
    <div class="today-head">
      <span class="today-title">Vandaag &amp; vannacht</span>
      <span class="today-date">{header_date} · {len(todays)} wedstrijden</span>
    </div>
    {"".join(rows)}
    {ai_bets_block(bet_matches, header_date)}
  </div>'''


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
  .today{background:var(--ink);color:#F4F6F2;border-radius:12px;padding:18px 20px;margin-bottom:26px;}
  .today-head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px;border-bottom:1.5px solid rgba(244,246,242,.25);padding-bottom:10px;margin-bottom:4px;}
  .today-title{font-family:'Anton',sans-serif;font-size:22px;text-transform:uppercase;letter-spacing:.02em;}
  .today-date{font-size:12px;color:rgba(244,246,242,.65);}
  .today-row{display:grid;grid-template-columns:52px 1fr auto 58px;align-items:center;gap:10px;padding:9px 0;border-top:1px dashed rgba(244,246,242,.18);font-size:14px;}
  .today-row:first-of-type{border-top:none;}
  .today-row.t-nl{color:#FFB385;font-weight:600;}
  .t-when{font-variant-numeric:tabular-nums;color:rgba(244,246,242,.75);font-size:12.5px;}
  .t-night{display:block;font-size:8.5px;letter-spacing:.08em;text-transform:uppercase;color:#FFB385;margin-top:1px;}
  .t-teams{line-height:1.35;}
  .t-meta{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:rgba(244,246,242,.5);}
  .t-score{font-family:'Caveat',cursive;font-size:26px;font-weight:700;color:#FFB385;text-align:right;}
  .t-live{color:#6FDF9B;}
  .t-time{font-size:12.5px;color:rgba(244,246,242,.55);text-align:right;}
  .today-empty{padding:12px 0 4px;font-size:13.5px;color:rgba(244,246,242,.75);}
  @media (max-width:480px){.t-meta{display:none;}.today-row{grid-template-columns:46px 1fr 56px;}}
  .chips{margin-top:3px;display:flex;flex-wrap:wrap;gap:4px;}
  .chip{font-size:10.5px;font-weight:600;padding:1px 6px;border-radius:9px;border:1.2px solid var(--pc);color:var(--pc);background:#fff;font-variant-numeric:tabular-nums;}
  .chip.exact{background:var(--pc);color:#fff;}
  .chip.toto{background:color-mix(in srgb,var(--pc) 15%,#fff);}
  .chip.mis{opacity:.42;}
  .bet-btn{margin-top:5px;display:inline-flex;align-items:center;gap:4px;font-size:10.5px;font-weight:700;letter-spacing:.02em;padding:2px 8px;border-radius:9px;border:1.2px solid var(--groen);color:var(--groen);background:#fff;cursor:pointer;line-height:1.5;}
  .bet-btn:hover{background:var(--groen);color:#fff;}
  .bet-btn.open{background:var(--groen);color:#fff;}
  .bet-panel{margin-top:6px;background:#F0F4F0;border:1px solid var(--line);border-left:3px solid var(--groen);border-radius:8px;padding:9px 11px;font-size:12px;line-height:1.45;color:var(--ink);}
  .bet-panel .bp-preview{margin-bottom:6px;}
  .bet-panel .bp-line{display:flex;gap:6px;margin:2px 0;}
  .bet-panel .bp-k{color:var(--ink-soft);min-width:74px;font-weight:600;}
  .bet-panel .bp-markt{font-weight:700;color:var(--groen);}
  .bet-panel .bp-odds{font-variant-numeric:tabular-nums;}
  .bet-panel .bp-conf{display:inline-block;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;padding:1px 7px;border-radius:8px;background:#E2EAE2;color:var(--groen);}
  .bet-panel .bp-share{margin-top:8px;font-size:11px;font-weight:600;padding:4px 10px;border-radius:7px;border:1px solid var(--groen);background:#fff;color:var(--groen);cursor:pointer;}
  .bet-panel .bp-share:hover{background:var(--groen);color:#fff;}
  .bet-panel .bp-disc{margin-top:7px;font-size:9.5px;color:var(--ink-soft);font-style:italic;}
  .mday{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--oranje);font-weight:700;margin:12px 0 2px;padding-bottom:3px;border-bottom:1px solid var(--line);}
  .mday:first-child{margin-top:0;}
  .toon-alle{display:flex;align-items:center;gap:7px;margin-top:14px;font-size:12px;color:var(--ink-soft);cursor:pointer;}
  .modal-leeg{padding:16px 0;font-size:13px;color:var(--ink-soft);text-align:center;}
  .ai-bets{margin-top:16px;border-top:1.5px solid rgba(244,246,242,.25);padding-top:14px;}
  .ai-bets-head{font-family:'Anton',sans-serif;font-size:17px;letter-spacing:.02em;text-transform:uppercase;color:#F4F6F2;margin-bottom:10px;}
  .ai-bets-sub{font-family:'Archivo',sans-serif;font-size:11px;font-weight:500;letter-spacing:.04em;color:rgba(244,246,242,.55);text-transform:none;}
  .ai-bets-menu{display:flex;flex-wrap:wrap;gap:8px;}
  .ai-chip{font-size:13px;font-weight:600;padding:9px 15px;border-radius:22px;border:1.5px solid rgba(244,246,242,.4);background:transparent;color:#F4F6F2;cursor:pointer;}
  .ai-chip:hover{border-color:#FFB385;color:#FFB385;}
  .ai-chip.actief{background:#FFB385;border-color:#FFB385;color:#14201A;}
  .ai-bets-panel{margin-top:12px;background:#FFF;color:#14201A;border-radius:10px;padding:14px 16px;}
  .ab-title{font-weight:700;font-size:15px;margin-bottom:8px;}
  .ab-match{font-size:13px;color:#5C6A61;margin-bottom:8px;}
  .ab-pick{display:flex;justify-content:space-between;align-items:center;gap:10px;background:#F0F4F0;border-left:3px solid var(--groen);border-radius:8px;padding:10px 12px;}
  .ab-markt{font-weight:700;color:var(--groen);font-size:15px;}
  .ab-bigod{font-family:'Caveat',cursive;font-size:30px;font-weight:700;color:var(--pen);}
  .ab-sels{list-style:none;margin:4px 0 0;padding:0;}
  .ab-sels li{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px dashed var(--line);font-size:13.5px;}
  .ab-sels li:last-child{border-bottom:none;}
  .ab-od{font-variant-numeric:tabular-nums;font-weight:700;color:var(--pen);}
  .ab-total{margin-top:8px;text-align:right;font-size:14px;}
  .ab-total b{font-family:'Caveat',cursive;font-size:26px;color:var(--pen);}
  .ab-line{font-size:12.5px;color:#5C6A61;margin-top:6px;}
  .ab-why{margin-top:10px;font-size:12.5px;line-height:1.45;color:#14201A;background:#F7F5EF;border-radius:7px;padding:8px 10px;}
  .ab-foot{display:flex;justify-content:space-between;align-items:center;margin-top:10px;}
  .ab-bron{font-size:11px;color:#5C6A61;}
  .ab-share{font-size:12px;font-weight:600;padding:6px 12px;border-radius:7px;border:1px solid var(--groen);background:#fff;color:var(--groen);cursor:pointer;}
  .ab-share:hover{background:var(--groen);color:#fff;}
  .ab-empty{font-size:13px;color:#5C6A61;padding:6px 0;}
  .ab-loading{display:flex;align-items:center;gap:12px;padding:10px 2px;font-size:13px;color:#5C6A61;}
  .ab-loading small{color:#8a968d;}
  .ab-spin{width:20px;height:20px;border-radius:50%;border:3px solid #E2EAE2;border-top-color:var(--groen);animation:abspin .8s linear infinite;flex:none;}
  @keyframes abspin{to{transform:rotate(360deg);}}
  /* ── mobiel ── */
  @media (max-width:560px){
    .wrap{padding:18px 12px 48px;}
    .groups,.ko-grid{grid-template-columns:1fr;gap:14px;}
    h1{font-size:clamp(30px,9vw,52px);}
    .statusline{font-size:12.5px;gap:6px 16px;}
    .legend{gap:6px 14px;font-size:12px;}
    .match{grid-template-columns:62px 1fr 50px;}
    .bet-btn{font-size:11.5px;padding:4px 11px;}
    .bet-panel{font-size:12.5px;}
    .today-row{grid-template-columns:46px 1fr 54px;}
    .modal{margin:10px 0;border-radius:12px;}
    .modal-body{max-height:70vh;}
    .mrow{grid-template-columns:1fr 104px;}
    .mrow-inp input{width:44px;padding:8px 0;font-size:16px;}
    .speler-chip{padding:8px 16px;font-size:13.5px;}
    .poule-btn{padding:10px 16px;font-size:13.5px;}
    .poule-row{grid-template-columns:30px 1fr 56px;}
  }
  .poule{background:var(--ink);color:#F4F6F2;border-radius:12px;padding:18px 20px;margin-bottom:26px;}
  .poule-head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px;border-bottom:1.5px solid rgba(244,246,242,.25);padding-bottom:10px;margin-bottom:6px;}
  .poule-title{font-family:'Anton',sans-serif;font-size:22px;text-transform:uppercase;letter-spacing:.02em;}
  .poule-rules{font-size:11.5px;color:rgba(244,246,242,.65);}
  .poule-row{display:grid;grid-template-columns:34px 1fr auto 60px;align-items:center;gap:10px;padding:9px 0;border-top:1px dashed rgba(244,246,242,.18);}
  .poule-row:first-of-type{border-top:none;}
  .poule-pos{font-size:18px;text-align:center;}
  .poule-naam{font-weight:600;font-size:15px;display:flex;align-items:center;gap:8px;}
  .poule-dot{width:10px;height:10px;border-radius:50%;display:inline-block;}
  .poule-detail{font-size:11.5px;color:rgba(244,246,242,.6);text-align:right;}
  .poule-punten{font-family:'Caveat',cursive;font-size:30px;font-weight:700;text-align:right;color:#FFB385;}
  .poule-btn{display:inline-block;margin-top:12px;padding:8px 16px;border-radius:8px;background:var(--oranje);color:#fff;text-decoration:none;font-size:13px;font-weight:600;border:none;cursor:pointer;}
  .poule-btn:active{opacity:.85;}
  .poule-loading{padding:10px 0;font-size:13px;color:rgba(244,246,242,.6);}
  .poule-invul{border-top:1.5px solid rgba(244,246,242,.25);margin-top:12px;padding-top:14px;display:flex;flex-wrap:wrap;align-items:center;gap:10px;}
  .poule-invul-label{font-size:13px;color:rgba(244,246,242,.8);font-weight:600;}
  .speler-keuze{display:flex;gap:6px;flex-wrap:wrap;}
  .speler-chip{padding:6px 14px;border-radius:20px;border:1.5px solid rgba(244,246,242,.4);background:transparent;color:#F4F6F2;font-size:13px;font-weight:600;cursor:pointer;}
  .speler-chip.actief{background:var(--oranje);border-color:var(--oranje);}
  .poule-hint{font-size:11.5px;color:rgba(244,246,242,.55);width:100%;}
  /* modal */
  .modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.6);display:none;align-items:flex-start;justify-content:center;z-index:50;padding:20px;overflow-y:auto;}
  .modal-bg.open{display:flex;}
  .modal{background:var(--card);color:var(--ink);border-radius:14px;max-width:560px;width:100%;margin:24px 0;padding:0;overflow:hidden;}
  .modal-head{position:sticky;top:0;background:var(--ink);color:#fff;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;}
  .modal-head h3{font-family:'Anton',sans-serif;font-size:20px;text-transform:uppercase;font-weight:400;}
  .modal-close{background:none;border:none;color:#fff;font-size:26px;cursor:pointer;line-height:1;}
  .modal-body{padding:14px 20px 20px;max-height:62vh;overflow-y:auto;}
  .mrow{display:grid;grid-template-columns:1fr 96px;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--line);font-size:13.5px;}
  .mrow-when{font-size:11px;color:var(--ink-soft);}
  .mrow-inp{display:flex;align-items:center;gap:4px;}
  .mrow-inp input{width:38px;padding:6px 0;text-align:center;border:1.5px solid var(--line);border-radius:7px;font-size:15px;font-variant-numeric:tabular-nums;}
  .mrow-inp input:focus{outline:none;border-color:var(--oranje);}
  .modal-foot{position:sticky;bottom:0;background:var(--card);border-top:1.5px solid var(--line);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;gap:10px;}
  .modal-foot .save{background:var(--groen);color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:14px;font-weight:600;cursor:pointer;}
  .modal-status{font-size:12px;color:var(--ink-soft);}
  @media (max-width:480px){.poule-detail{display:none;}.poule-row{grid-template-columns:34px 1fr 60px;}}
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
  __TODAY__
  __POULE__
  <div class="groups">__GROUPS__</div>
  <h2 class="section-title">Knock-outfase</h2>
  <p class="section-sub">Vanaf 28 juni. De nummers 1 en 2 van elke groep plaatsen zich, plus de acht beste nummers 3 — in totaal 32 landen.</p>
  <div class="ko-grid">__KO__</div>
  <footer>Automatisch bijgewerkt via GitHub Actions · Data: football-data.org · Tijden in Nederlandse tijd</footer>
</div>

<div class="modal-bg" id="modal">
  <div class="modal">
    <div class="modal-head">
      <h3 id="modal-titel">Voorspellingen</h3>
      <button class="modal-close" id="modal-close" type="button">&times;</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
    <div class="modal-foot">
      <span class="modal-status" id="modal-status"></span>
      <button class="save" id="modal-save" type="button">Opslaan</button>
    </div>
  </div>
</div>

__POULE_JS__
__BETS_JS__
</body>
</html>
"""


def build_poule_js():
    if not (SUPABASE_URL and SUPABASE_KEY):
        return ""
    spelers_json = json.dumps(SPELERS, ensure_ascii=False)
    kleuren_json = json.dumps(PLAYER_COLORS, ensure_ascii=False)
    # let op: dubbele accolades omdat dit een f-string is
    return f'''<script>
(function(){{
  const SB_URL = "{SUPABASE_URL}";
  const SB_KEY = "{SUPABASE_KEY}";
  const SPELERS = {spelers_json};
  const KLEUREN = {kleuren_json};
  const EXACT = {PUNTEN_EXACT}, TOTO = {PUNTEN_TOTO};
  const REST = SB_URL + "/rest/v1/voorspellingen";
  const H = {{ "apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY, "Content-Type": "application/json" }};

  const kleurVan = n => KLEUREN[Math.max(0, SPELERS.indexOf(n)) % KLEUREN.length];
  let DATA = [];          // alle rijen uit Supabase
  let IK = localStorage.getItem("wk26-speler") || "";

  // alle wedstrijden uit de pagina halen (met evt. echte uitslag)
  const MATCHES = [...document.querySelectorAll(".match[data-key]")].map(el => ({{
    key: el.getAttribute("data-key"),
    ts: el.hasAttribute("data-ts") ? +el.getAttribute("data-ts") : 0,
    th: el.hasAttribute("data-th") ? +el.getAttribute("data-th") : null,
    tu: el.hasAttribute("data-tu") ? +el.getAttribute("data-tu") : null
  }})).filter(m => m.key);

  const punten = (ph,pu,ah,au) => {{
    if(ah==null) return null;
    if(ph===ah && pu===au) return EXACT;
    if((ph>pu&&ah>au)||(ph<pu&&ah<au)||(ph===pu&&ah===au)) return TOTO;
    return 0;
  }};

  async function laden(){{
    try{{
      const r = await fetch(REST + "?select=*", {{ headers: H }});
      DATA = await r.json();
      if(!Array.isArray(DATA)) DATA = [];
    }}catch(e){{ DATA = []; }}
    tekenStand(); tekenChips();
  }}

  function predVan(speler, key){{
    return DATA.find(d => d.speler===speler && d.wedstrijd===key);
  }}

  function tekenStand(){{
    const resultMap = {{}};
    MATCHES.forEach(m => {{ if(m.th!=null) resultMap[m.key]=[m.th,m.tu]; }});
    const rij = SPELERS.map(sp => {{
      let tot=0,ex=0,to=0,inv=0;
      DATA.filter(d=>d.speler===sp).forEach(d=>{{
        inv++;
        const res = resultMap[d.wedstrijd];
        if(res){{ const p = punten(d.thuis,d.uit,res[0],res[1]);
          tot+=p; if(p===EXACT)ex++; else if(p===TOTO)to++; }}
      }});
      return {{sp,tot,ex,to,inv}};
    }}).sort((a,b)=> b.tot-a.tot || b.ex-a.ex || a.sp.localeCompare(b.sp));
    const med=["🥇","🥈","🥉"];
    document.getElementById("poule-stand").innerHTML = rij.map((r,i)=>`
      <div class="poule-row">
        <div class="poule-pos">${{i<3?med[i]:i+1}}</div>
        <div class="poule-naam"><span class="poule-dot" style="background:${{kleurVan(r.sp)}}"></span>${{r.sp}}</div>
        <div class="poule-detail">${{r.ex}}× exact · ${{r.to}}× toto · ${{r.inv}} ingevuld</div>
        <div class="poule-punten">${{r.tot}}</div>
      </div>`).join("");
  }}

  function tekenChips(){{
    const resultMap = {{}};
    MATCHES.forEach(m => {{ if(m.th!=null) resultMap[m.key]=[m.th,m.tu]; }});
    document.querySelectorAll(".chips[data-chips]").forEach(box=>{{
      const key = box.getAttribute("data-chips");
      const res = resultMap[key];
      box.innerHTML = SPELERS.map(sp=>{{
        const d = predVan(sp,key); if(!d) return "";
        let cls="chip";
        if(res){{ const p=punten(d.thuis,d.uit,res[0],res[1]);
          cls += p===EXACT?" exact":(p===TOTO?" toto":" mis"); }}
        return `<span class="${{cls}}" style="--pc:${{kleurVan(sp)}}">${{sp[0]}}&thinsp;${{d.thuis}}-${{d.uit}}</span>`;
      }}).join("");
    }});
  }}

  // speler-keuze knoppen
  const keuze = document.getElementById("speler-keuze");
  function tekenKeuze(){{
    keuze.innerHTML = SPELERS.map(sp=>
      `<button class="speler-chip${{sp===IK?" actief":""}}" data-sp="${{sp}}" type="button">${{sp}}</button>`).join("");
  }}
  tekenKeuze();
  keuze.addEventListener("click", e=>{{
    const b = e.target.closest("[data-sp]"); if(!b) return;
    IK = b.getAttribute("data-sp");
    localStorage.setItem("wk26-speler", IK);
    tekenKeuze(); toonStartknop();
  }});

  const startBtn = document.getElementById("invul-start");
  const hint = document.getElementById("invul-hint");
  function toonStartknop(){{
    if(IK){{ startBtn.hidden=false; hint.textContent = "Je vult in als "+IK+". Je kunt altijd wijzigen tot de aftrap."; }}
  }}
  toonStartknop();

  // modal
  const modal = document.getElementById("modal");
  const body = document.getElementById("modal-body");
  const status = document.getElementById("modal-status");
  startBtn.addEventListener("click", openModal);
  document.getElementById("modal-close").addEventListener("click", ()=>modal.classList.remove("open"));
  modal.addEventListener("click", e=>{{ if(e.target===modal) modal.classList.remove("open"); }});

  let TOON_ALLE = false;
  function modalMatches(){{
    let arr = MATCHES.slice().sort((a,b)=> (a.ts||0)-(b.ts||0));
    if(!TOON_ALLE) arr = arr.filter(m=> m.th==null);   // standaard: alleen nog te spelen
    return arr;
  }}
  function renderModalBody(){{
    const arr = modalMatches();
    let html = "", lastDay = "";
    arr.forEach(m=>{{
      const d = new Date(m.ts);
      const day = d.toLocaleDateString('nl-NL',{{weekday:'long',day:'numeric',month:'short'}});
      if(day!==lastDay){{ html += `<div class="mday">${{day}}</div>`; lastDay = day; }}
      const pred = predVan(IK,m.key);
      const locked = m.th!=null;
      const tijd = d.toLocaleTimeString('nl-NL',{{hour:'2-digit',minute:'2-digit'}});
      html += `<div class="mrow">
        <div><div class="mrow-when">${{tijd}}</div>${{m.key}}</div>
        <div class="mrow-inp">
          <input type="number" min="0" max="20" data-key="${{m.key}}" data-side="h" value="${{pred?pred.thuis:''}}" ${{locked?'disabled':''}}>
          <span>-</span>
          <input type="number" min="0" max="20" data-key="${{m.key}}" data-side="u" value="${{pred?pred.uit:''}}" ${{locked?'disabled':''}}>
        </div>
      </div>`;
    }});
    if(!arr.length) html = `<div class="modal-leeg">Geen komende wedstrijden om in te vullen.</div>`;
    html += `<label class="toon-alle"><input type="checkbox" id="toon-alle-chk" ${{TOON_ALLE?'checked':''}}> ook al gespeelde wedstrijden tonen</label>`;
    body.innerHTML = html;
    const chk = document.getElementById("toon-alle-chk");
    if(chk) chk.addEventListener("change", e=>{{ TOON_ALLE = e.target.checked; renderModalBody(); }});
  }}
  function openModal(){{
    document.getElementById("modal-titel").textContent = "Voorspellingen — " + IK;
    TOON_ALLE = false;
    renderModalBody();
    status.textContent = "";
    modal.classList.add("open");
  }}

  document.getElementById("modal-save").addEventListener("click", async ()=>{{
    const inputs = [...body.querySelectorAll("input")];
    const byKey = {{}};
    inputs.forEach(inp=>{{
      const k = inp.getAttribute("data-key");
      byKey[k] = byKey[k] || {{}};
      byKey[k][inp.getAttribute("data-side")] = inp.value.trim();
    }});
    const rows = [];
    Object.entries(byKey).forEach(([k,v])=>{{
      if(v.h!==""&&v.u!==""&&v.h!=null&&v.u!=null)
        rows.push({{ speler:IK, wedstrijd:k, thuis:+v.h, uit:+v.u }});
    }});
    if(!rows.length){{ status.textContent="Niets ingevuld."; return; }}
    status.textContent = "Opslaan…";
    try{{
      const r = await fetch(REST + "?on_conflict=speler,wedstrijd", {{
        method:"POST",
        headers: {{...H, "Prefer":"resolution=merge-duplicates"}},
        body: JSON.stringify(rows)
      }});
      if(!r.ok) throw new Error(await r.text());
      status.textContent = "Opgeslagen!";
      await laden();
      setTimeout(()=>modal.classList.remove("open"), 700);
    }}catch(e){{ status.textContent = "Fout bij opslaan."; console.error(e); }}
  }});

  laden();
}})();
</script>'''


def build_bets_js():
    if not (SUPABASE_URL and SUPABASE_KEY):
        return ""
    return '''<script>
(function(){
  const box=document.querySelector('.ai-bets'); if(!box) return;
  let CFG={}; try{ CFG=JSON.parse(box.getAttribute('data-aicfg')); }catch(e){ return; }
  const panel=document.getElementById('ai-bets-panel');
  const labels={banker:'🛡️ Veilige tip',builder:'🏗️ Bet builder',combi:'🔗 Combi van de dag',longshot:'🎲 Verrassing'};
  let busy=false;
  function esc(s){return (s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
  function od(n){ return (typeof n==='number')? n.toFixed(2): esc(n); }
  function selList(items, withMatch){
    return '<ul class="ab-sels">'+items.map(s=>'<li><span>'
      +(withMatch?('<b>'+esc(s.wedstrijd)+'</b> — '):'')+esc(s.markt)
      +'</span><span class="ab-od">'+od(s.odds)+'</span></li>').join('')+'</ul>';
  }
  function renderBet(t,b){
    let h='<div class="ab-title">'+labels[t]+'</div>';
    if(t==='banker'){
      h+='<div class="ab-match">'+esc(b.wedstrijd)+'</div>';
      h+='<div class="ab-pick"><span class="ab-markt">'+esc(b.markt)+'</span><span class="ab-bigod">'+od(b.odds)+'</span></div>';
      if(b.kans) h+='<div class="ab-line">Geschatte kans: '+esc(b.kans)+'</div>';
    } else if(t==='builder'){
      h+='<div class="ab-match">'+esc(b.wedstrijd)+'</div>';
      h+=selList(b.selecties,false);
      h+='<div class="ab-total">Samen <b>'+od(b.combi_odds)+'</b></div>';
    } else {
      h+=selList(b.selecties,true);
      h+='<div class="ab-total">Samen <b>'+od(b.combi_odds)+'</b></div>';
    }
    if(b.uitleg) h+='<div class="ab-why">'+esc(b.uitleg)+'</div>';
    h+='<div class="ab-foot"><span class="ab-bron">via '+esc(b.bron||'Unibet')+' · Opus 4.8 live</span><button class="ab-share" type="button">📋 Deel</button></div>';
    panel.innerHTML=h;
    const sb=panel.querySelector('.ab-share');
    if(sb) sb.addEventListener('click',()=>{
      navigator.clipboard.writeText(shareText(t,b)).then(
        ()=>{ sb.textContent='✓ Gekopieerd'; setTimeout(()=>sb.textContent='📋 Deel',1500); },
        ()=>{ sb.textContent='Mislukt'; });
    });
  }
  function shareText(t,b){
    let x='🤖 '+labels[t]+' ('+(CFG.datum||'')+')\\n';
    if(t==='banker'){ x+=b.wedstrijd+'\\n'+b.markt+' @ '+od(b.odds)+'\\n'; }
    else if(t==='builder'){ x+=b.wedstrijd+'\\n'+b.selecties.map(s=>'• '+s.markt+' @ '+od(s.odds)).join('\\n')+'\\nSamen @ '+od(b.combi_odds)+'\\n'; }
    else { x+=b.selecties.map(s=>'• '+s.wedstrijd+': '+s.markt+' @ '+od(s.odds)).join('\\n')+'\\nSamen @ '+od(b.combi_odds)+'\\n'; }
    if(b.uitleg) x+=b.uitleg+'\\n';
    x+='(AI-suggestie, geen garantie · '+(b.bron||'Unibet')+')';
    return x;
  }
  async function zoek(t){
    if(busy) return; busy=true;
    box.querySelectorAll('.ai-chip').forEach(c=>c.classList.remove('actief'));
    const chip=box.querySelector('.ai-chip[data-bt="'+t+'"]'); if(chip) chip.classList.add('actief');
    panel.hidden=false;
    panel.innerHTML='<div class="ab-loading"><span class="ab-spin"></span><div>Opus 4.8 zoekt live vorm, nieuws &amp; odds…<br><small>dit kan ~20 seconden duren</small></div></div>';
    try{
      const r=await fetch(CFG.url,{method:'POST',headers:{'apikey':CFG.key,'Authorization':'Bearer '+CFG.key,'Content-Type':'application/json'},body:JSON.stringify({type:t,datum:CFG.datum,wedstrijden:CFG.wedstrijden})});
      const j=await r.json().catch(()=>({error:'Ongeldig antwoord'}));
      if(!r.ok || j.error || !j.bet){ panel.innerHTML='<div class="ab-empty">'+esc(j.error||('Fout '+r.status))+'</div>'; busy=false; return; }
      renderBet(t,j.bet);
    }catch(e){ panel.innerHTML='<div class="ab-empty">Kon de AI niet bereiken. Probeer het zo nog eens.</div>'; }
    busy=false;
  }
  box.querySelectorAll('.ai-chip').forEach(ch=>{
    ch.addEventListener('click',()=>zoek(ch.getAttribute('data-bt')));
  });
})();
</script>'''


TEMPLATE_FOOTER_NOTE = None


def main():
    if not TOKEN:
        print("FOUT: zet FOOTBALL_DATA_TOKEN als environment variable / repo secret.")
        sys.exit(1)

    load_predictions()
    matches = fetch("/matches")["matches"]
    standings = fetch("/standings")

    groups_html, played = build_groups(matches, standings)
    ko_html, ko_played = build_knockout(matches)
    poule_html = build_poule(matches)
    today_html = build_today(matches)
    poule_js = build_poule_js()
    bets_js = build_bets_js()

    updated = datetime.now(TZ).strftime("%d-%m-%Y %H:%M")
    html = (TEMPLATE
            .replace("__TODAY__", today_html)
            .replace("__POULE__", poule_html)
            .replace("__POULE_JS__", poule_js)
            .replace("__BETS_JS__", bets_js)
            .replace("__GROUPS__", groups_html)
            .replace("__KO__", ko_html)
            .replace("__UPDATED__", updated)
            .replace("__PLAYED__", str(played + ko_played)))

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html geschreven · {played + ko_played} gespeelde wedstrijden")


if __name__ == "__main__":
    main()
