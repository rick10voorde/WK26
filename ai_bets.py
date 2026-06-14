#!/usr/bin/env python3
"""
Genereert ai_bets.json: een setje 'bets van vandaag & vannacht' in vier smaken
(banker / bet builder / combi / longshot) met Unibet-odds. Draait in de GitHub
Action VOOR generate.py.

Env: FOOTBALL_DATA_TOKEN (verplicht), ANTHROPIC_API_KEY (optioneel),
     ODDS_API_KEY (optioneel), AI_MODEL (optioneel).

WK 2026 speelt op NEUTRAAL terrein: geen thuisvoordeel (behalve de gastlanden
VS/Canada/Mexico in eigen land). De AI krijgt dat expliciet mee.
Alleen standaardbibliotheek + generate.py.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import generate

TZ = ZoneInfo("Europe/Amsterdam")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
MODEL = os.environ.get("AI_MODEL", "claude-haiku-4-5-20251001")
OUT = "ai_bets.json"
MAANDEN = generate.MAANDEN
DAGEN = generate.DAGEN


def http_get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wk26-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_odds():
    if not ODDS_KEY:
        print("Geen ODDS_API_KEY - geen odds.")
        return []
    sport = "soccer_fifa_world_cup"
    try:
        for s in http_get_json(f"https://api.the-odds-api.com/v4/sports/?apiKey={ODDS_KEY}"):
            k = s.get("key", "")
            if "world_cup" in k and "soccer" in k and s.get("active"):
                sport = k
                break
    except Exception as e:
        print("sports-lookup faalde:", e)
    url = (f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
           f"?apiKey={ODDS_KEY}&regions=eu,uk&markets=h2h,totals&oddsFormat=decimal")
    try:
        return http_get_json(url)
    except Exception as e:
        print("odds faalde:", e)
        return []


def pick_bookmaker(ev):
    # the-odds-api gebruikt regio-specifieke keys: unibet_eu / unibet_uk / unibet_nl.
    bks = ev.get("bookmakers", [])
    for b in bks:
        if "unibet" in (b.get("key", "").lower()):
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
    idx = {}
    for ev in events:
        eh = generate.nl_name({"name": ev.get("home_team")})
        ea = generate.nl_name({"name": ev.get("away_team")})
        if eh and ea:
            idx[(norm(eh), norm(ea))] = odds_for(ev)
    return idx


def select_today(matches):
    now = datetime.now(TZ)
    end = now + timedelta(hours=30)
    sel = []
    for m in matches:
        if m["status"] in ("FINISHED", "IN_PLAY", "PAUSED"):
            continue
        h = generate.nl_name(m["homeTeam"])
        a = generate.nl_name(m["awayTeam"])
        if not h or not a:
            continue
        dt = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).astimezone(TZ)
        if dt < now - timedelta(minutes=15) or dt > end:
            continue
        sel.append((f"{h} - {a}", h, a, dt))
    sel.sort(key=lambda x: x[3])
    return sel


def markten_for(t1, t2, od):
    m = {}
    if not od:
        return m
    if od.get("thuis") is not None:
        m[f"{t1} wint"] = od["thuis"]
    if od.get("gelijk") is not None:
        m["Gelijkspel"] = od["gelijk"]
    if od.get("uit") is not None:
        m[f"{t2} wint"] = od["uit"]
    if od.get("over25") is not None:
        m["Meer dan 2.5 goals"] = od["over25"]
    if od.get("under25") is not None:
        m["Minder dan 2.5 goals"] = od["under25"]
    return m


def call_claude(payload):
    sys_p = (
        "Je bent een nuchtere voetbalanalist die voor een vriendengroep goede, eerlijke "
        "weddenschappen samenstelt voor het WK 2026 (wedden via Unibet). "
        "BELANGRIJK: dit toernooi is op NEUTRAAL terrein. Er is GEEN thuisvoordeel; negeer "
        "volledig welke ploeg administratief 'thuis' staat, behalve de gastlanden "
        "(Verenigde Staten, Canada, Mexico) als die in eigen land spelen. "
        "Kies selecties UITSLUITEND uit de aangeleverde markten. Wees realistisch: de odds "
        "bevatten al de kansen plus een marge, dus beloof geen winst. "
        "Antwoord UITSLUITEND met geldige JSON, zonder extra tekst.")
    schema = (
        '{'
        '"banker":{"wedstrijd":"<key>","markt":"<exacte marktnaam>","kans":"bv ~75%","uitleg":"1 zin"},'
        '"builder":{"wedstrijd":"<key>","selecties":["<marktnaam>","<marktnaam>"],"uitleg":"1 zin"},'
        '"combi":{"selecties":[{"wedstrijd":"<key>","markt":"<marktnaam>"}],"uitleg":"1 zin"},'
        '"longshot":{"selecties":[{"wedstrijd":"<key>","markt":"<marktnaam>"}],"uitleg":"1 zin"}}')
    user = (
        "Wedstrijden van vandaag/vannacht met Unibet-odds (markt: decimale odd):\n"
        + json.dumps(payload, ensure_ascii=False, indent=1)
        + "\n\nStel 4 weddenschappen samen, met exact de gegeven marktnamen:\n"
        "- banker: 1 selectie met het laagste risico (korte odds, hoogste kans).\n"
        "- builder: 2 of 3 selecties BINNEN EEN wedstrijd (bv resultaat + meer/minder goals).\n"
        "- combi: 2 of 3 selecties uit VERSCHILLENDE wedstrijden.\n"
        "- longshot: durf-bet met hoge odds (1 lange selectie of een kleine gewaagde combi).\n"
        "Geef JSON volgens dit schema: " + schema)
    body = json.dumps({
        "model": MODEL, "max_tokens": 1500, "system": sys_p,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
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


def lookup(markten_by_key, key, markt):
    return (markten_by_key.get(key) or {}).get(markt)


def prod(vals):
    p = 1.0
    for v in vals:
        p *= v
    return round(p, 2)


def normalize_bets(raw, mk, bron):
    out = {}
    b = raw.get("banker") or {}
    if b.get("wedstrijd") and b.get("markt"):
        o = lookup(mk, b["wedstrijd"], b["markt"])
        if o:
            out["banker"] = {"type": "banker", "wedstrijd": b["wedstrijd"],
                             "markt": b["markt"], "odds": o, "kans": b.get("kans", ""),
                             "uitleg": b.get("uitleg", ""), "bron": bron}
    bu = raw.get("builder") or {}
    if bu.get("wedstrijd") and bu.get("selecties"):
        key = bu["wedstrijd"]
        sels = []
        for s in bu["selecties"]:
            mt = s if isinstance(s, str) else (s.get("markt") or "")
            o = lookup(mk, key, mt)
            if o:
                sels.append({"markt": mt, "odds": o})
        if len(sels) >= 2:
            out["builder"] = {"type": "builder", "wedstrijd": key, "selecties": sels,
                              "combi_odds": prod([x["odds"] for x in sels]),
                              "uitleg": bu.get("uitleg", ""), "bron": bron}
    for tkey in ("combi", "longshot"):
        c = raw.get(tkey) or {}
        if c.get("selecties"):
            sels = []
            for s in c["selecties"]:
                if not isinstance(s, dict):
                    continue
                w, mt = s.get("wedstrijd"), s.get("markt") or ""
                o = lookup(mk, w, mt)
                if o:
                    sels.append({"wedstrijd": w, "markt": mt, "odds": o})
            if sels:
                out[tkey] = {"type": tkey, "selecties": sels,
                             "combi_odds": prod([x["odds"] for x in sels]),
                             "uitleg": c.get("uitleg", ""), "bron": bron}
    return out


def main():
    if not os.environ.get("FOOTBALL_DATA_TOKEN", ""):
        print("Geen FOOTBALL_DATA_TOKEN; stop.")
        return
    matches = generate.fetch("/matches")["matches"]
    today = select_today(matches)
    now = datetime.now(TZ)
    datum_lbl = f"{DAGEN[now.weekday()]} {now.day} {MAANDEN[now.month - 1]}"

    if not today:
        json.dump({"datum": datum_lbl, "bron": "Unibet", "wedstrijden": [], "bets": {}},
                  open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Geen wedstrijden vandaag/vannacht; lege bets.")
        return

    odds_idx = build_odds_index(fetch_odds())
    markten_by_key, payload, wedstrijden = {}, [], []
    bron = "Unibet"
    for key, t1, t2, dt in today:
        od = odds_idx.get((norm(t1), norm(t2)))
        mkt = markten_for(t1, t2, od)
        markten_by_key[key] = mkt
        if od and od.get("bron"):
            bron = od["bron"]
        wedstrijden.append({"key": key, "tijd": dt.strftime("%H:%M")})
        payload.append({"wedstrijd": key, "tijd": dt.strftime("%H:%M"), "markten": mkt})

    bets = {}
    if not ANTHROPIC_KEY:
        print("Geen ANTHROPIC_API_KEY; geen bets gemaakt.")
    elif not any(p["markten"] for p in payload):
        print("Geen odds beschikbaar voor de wedstrijden van vandaag; geen bets.")
    else:
        try:
            bets = normalize_bets(call_claude(payload), markten_by_key, bron)
        except Exception as e:
            print("Claude-call faalde:", e)
            bets = {}

    out = {"datum": datum_lbl, "gegenereerd": now.isoformat(), "bron": bron,
           "wedstrijden": wedstrijden, "bets": bets}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ai_bets.json geschreven · {len(today)} wedstrijden · types: {list(bets)}")


if __name__ == "__main__":
    main()
