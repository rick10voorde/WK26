#!/usr/bin/env python3
"""
Genereert ai_analyse.json: per komende WK-wedstrijd een korte Claude-analyse
met (indien beschikbaar) Unibet-odds. Draait in de GitHub Action VOOR generate.py.

Env:
  FOOTBALL_DATA_TOKEN  (verplicht – zelfde token als generate.py)
  ANTHROPIC_API_KEY    (optioneel – zonder key worden er geen analyses gemaakt)
  ODDS_API_KEY         (optioneel – the-odds-api.com, bevat Unibet)
  AI_MODEL             (optioneel – default claude-haiku-4-5-20251001)
  AI_WINDOW_DAYS       (optioneel – hoeveel dagen vooruit, default 4)

Faalt een externe call, dan wordt dat netjes overgeslagen en blijft de site werken.
Gebruikt alleen de standaardbibliotheek + generate.py (voor nl_name/fetch).
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone, timedelta

import generate  # hergebruik nl_name, fetch, NL-namen voor consistente keys

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
MODEL = os.environ.get("AI_MODEL", "claude-haiku-4-5-20251001")
WINDOW_DAYS = int(os.environ.get("AI_WINDOW_DAYS", "4"))
OUT = "ai_analyse.json"


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wk26-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_odds():
    """Haalt odds-events op via the-odds-api. Lege lijst bij geen key/fout."""
    if not ODDS_KEY:
        print("Geen ODDS_API_KEY – analyses zonder odds.")
        return []
    sport = "soccer_fifa_world_cup"
    try:
        sports = http_get_json(
            f"https://api.the-odds-api.com/v4/sports/?apiKey={ODDS_KEY}")
        for s in sports:
            k = s.get("key", "")
            if "world_cup" in k and "soccer" in k and s.get("active"):
                sport = k
                break
    except Exception as e:
        print("odds sports-lookup faalde:", e)
    url = (f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
           f"?apiKey={ODDS_KEY}&regions=eu,uk&markets=h2h,totals&oddsFormat=decimal")
    try:
        return http_get_json(url)
    except Exception as e:
        print("odds ophalen faalde:", e)
        return []


def pick_bookmaker(ev):
    bks = ev.get("bookmakers", [])
    for b in bks:
        if b.get("key") == "unibet":
            return b
    return bks[0] if bks else None


def odds_for(ev):
    b = pick_bookmaker(ev)
    if not b:
        return None
    out = {"bron": b.get("title", "")}
    for m in b.get("markets", []):
        if m["key"] == "h2h":
            for o in m["outcomes"]:
                if o["name"] == ev["home_team"]:
                    out["thuis"] = o["price"]
                elif o["name"] == ev["away_team"]:
                    out["uit"] = o["price"]
                else:
                    out["gelijk"] = o["price"]
        elif m["key"] == "totals":
            for o in m["outcomes"]:
                if abs(o.get("point", 0) - 2.5) < 0.01:
                    if o["name"].lower().startswith("over"):
                        out["over25"] = o["price"]
                    else:
                        out["under25"] = o["price"]
    return out


def norm(s):
    return (s or "").lower().replace(".", "").replace("-", " ").strip()


def build_odds_index(events):
    """(genormaliseerde NL-thuis, NL-uit) -> odds-dict."""
    idx = {}
    for ev in events:
        eh = generate.nl_name({"name": ev.get("home_team")})
        ea = generate.nl_name({"name": ev.get("away_team")})
        if not eh or not ea:
            continue
        idx[(norm(eh), norm(ea))] = odds_for(ev)
    return idx


def select_upcoming(matches):
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=WINDOW_DAYS)
    sel = []
    for m in matches:
        if m["status"] == "FINISHED":
            continue
        h = generate.nl_name(m["homeTeam"])
        a = generate.nl_name(m["awayTeam"])
        if not h or not a:          # 'Nog te bepalen' duels overslaan
            continue
        dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00"))
        if dt < now - timedelta(hours=3) or dt > horizon:
            continue
        sel.append((f"{h} - {a}", h, a, dt, m))
    sel.sort(key=lambda x: x[3])
    return sel


def call_claude(items):
    out = {}
    chunk_size = 8
    for i in range(0, len(items), chunk_size):
        out.update(claude_chunk(items[i:i + chunk_size]))
        time.sleep(1)
    return out


def claude_chunk(chunk):
    sys_prompt = (
        "Je bent een nuchtere voetbalanalist voor een vriendengroep die op het "
        "WK 2026 wedt via Unibet. Geef per wedstrijd een korte, eerlijke analyse. "
        "Wees realistisch: de odds bevatten al de ingeschatte kansen plus een marge, "
        "dus beloof geen winst en overdrijf geen zekerheden. "
        "Antwoord UITSLUITEND met geldige JSON, zonder extra tekst.")
    schema = (
        '{"<key>": {'
        '"preview":"1-2 zinnen context (vorm, sleutelduel, belang)",'
        '"score":"verwachte uitslag, bv 2-1",'
        '"kansen":{"thuis":getal,"gelijk":getal,"uit":getal},'
        '"markt":"voorkeursmarkt in 1 korte regel (bv 1X2, over/under 2.5, beide scoren)",'
        '"lean":"1 regel: waarom; verwijs naar de odds als die gegeven zijn",'
        '"vertrouwen":"laag|gemiddeld|hoog"}}')
    user = (
        "Wedstrijden (met Unibet-odds indien beschikbaar):\n"
        + json.dumps(chunk, ensure_ascii=False, indent=1)
        + "\n\nGeef EEN JSON-object terug met exact deze keys: "
        + json.dumps([c["key"] for c in chunk], ensure_ascii=False)
        + ". Elke waarde volgt dit schema: " + schema
        + " De drie kansen tellen samen op tot 100.")
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 2000,
        "system": sys_prompt,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": ANTHROPIC_KEY,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.load(r)
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except Exception as e:
        print("Claude-call faalde voor chunk:", e)
        return {}


def main():
    if not os.environ.get("FOOTBALL_DATA_TOKEN", ""):
        print("Geen FOOTBALL_DATA_TOKEN; ai_bets stopt.")
        return

    existing = {}
    if os.path.exists(OUT):
        try:
            existing = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            existing = {}

    matches = generate.fetch("/matches")["matches"]
    upcoming = select_upcoming(matches)
    if not upcoming:
        print("Geen komende wedstrijden in venster; bestaande analyses behouden.")
        json.dump(existing, open(OUT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        return

    odds_idx = build_odds_index(fetch_odds())
    items = []
    for key, h, a, dt, m in upcoming:
        items.append({
            "key": key, "thuis": h, "uit": a,
            "datum": dt.strftime("%Y-%m-%d %H:%M UTC"),
            "fase": m.get("group") or m.get("stage"),
            "odds": odds_idx.get((norm(h), norm(a))),
        })

    analyses = call_claude(items) if ANTHROPIC_KEY else {}
    if not ANTHROPIC_KEY:
        print("Geen ANTHROPIC_API_KEY – geen AI-analyses gemaakt.")

    for it in items:
        a = analyses.get(it["key"])
        if a is None:
            continue
        if it.get("odds"):
            a.setdefault("odds", it["odds"])
        existing[it["key"]] = a

    json.dump(existing, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"ai_analyse.json bijgewerkt · {len(analyses)} nieuwe analyses, "
          f"{len(existing)} totaal in bestand")


if __name__ == "__main__":
    main()
