"""
The agency's brain — the trial office's desks, one Claude call each.

0. Beside it, one job each: Espresso's culture radar and occasion pulse, and Chai's brand watch
   (desks.py) — their answers feed the strategy desk.
1. Strategy desk (Matcha + Coca): reads the last 48h of signals and the agency's memory; writes a short
   memo, scores each opportunity on five axes, retires stale plays and commissions new ones.
2. Studio: one short call for the top commissioned play. Writes an inspiration package — brand relevance,
   funnel stage, format, three hooks, the approach as storyboard beats, tactics, and real references with what
   to borrow from each. The trial writes one play; the full Insight Café writes every one, adds the ad desk and
   customer voice, learns from the lead's huddle and sends each play to the team on Slack.

Two calls, not one, because structured outputs compile the schema into a grammar and
the whole office in one schema is rejected as too large. One short call per play
because a single long studio call ran past the SDK's 10-minute request timeout.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import calendar_world, config

log = logging.getLogger("agency.brain")

# The vocabulary comes from the brand profile (config.py); "None" lets a Watch or Skip go untagged
CATEGORIES = config.CATEGORIES
PLATFORMS = config.PLATFORMS
PILLARS = config.PILLARS + ["None"]
PERSONAS = config.PERSONAS + ["None"]
VERDICTS = ["Act today", "This week", "Watch", "Skip"]
FUNNEL = ["Awareness", "Consideration", "Conversion"]
FORMATS = config.FORMATS
PRICE_USD = {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 5.0}  # Opus 5.5 per 1M tokens


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _enum(values: list[str]) -> dict:
    return {"type": "string", "enum": values}


S = {"type": "string"}
SA = {"type": "array", "items": S}
I = {"type": "integer"}

# Enums only where the office UI branches on the value; the rest are plain strings
# that state.normalise() checks against the lists above.
BOARD_SCHEMA = _obj({
    "memo": _obj({"headline": S, "bullets": SA, "since_last_sweep": S, "priority_echo": S, "top_actions": SA}),
    "trends": {"type": "array", "items": _obj({
        "id": S, "name": S, "category": S, "platforms": SA, "insight": S, "what": S, "why_us": S, "risk": S,
        "move": S, "evidence": SA, "search_terms": SA, "momentum": S,
        "scores": _obj({"brand_fit": I, "momentum": I, "reach": I, "urgency": I, "ease": I}),
        "pillar": S, "product_key": S, "persona": S, "funnel": _enum(FUNNEL), "formats": SA,
        "verdict": _enum(VERDICTS), "window": S,
    })},
    "commission": {"type": "array", "items": _obj({
        # format as a plain string, checked in code: the enum tipped the schema over the grammar limit
        "trend_id": S, "pic": _enum(list(config.PICS)), "lane": S, "format": S, "angle": S,
        "pinterest_searches": SA, "borrow_from_brands": SA,
    })},
    "retire_plays": {"type": "array", "items": _obj({"id": S, "reason": S})},
    # Staff notes as three plain lists in a fixed order (coca, chai, matcha, latte, mocha, tonic). A nested
    # object per person made the schema too large to compile; normalise() fills any missing entry.
    "staff_status": SA, "staff_learned": SA, "staff_questions": SA,
    "blocked": {"type": "array", "items": _obj({"idea": S, "rule": S})},
})

PLAY_SCHEMA = _obj({
    "slug": S, "title": S, "funnel": _enum(FUNNEL), "brand_relevance": S, "why_now": S,
    "hooks": SA, "approach": SA, "tactics": SA,
    "references": {"type": "array", "items": _obj({"id": S, "borrow": S})},
    "caption": S, "hashtags": SA, "cta": S, "doc_title": S, "doc_to": S, "doc_body": S,
    "due": S, "size": S, "kpi": S, "message": S, "blocked_reason": S,
})


SYSTEM = """You are {agency}, a small brand opportunity agency in {city} whose only client is {brand}: {one_liner} \
The agency exists to tell {lead} what happened in culture and social in {market}, and in other brands — their moves and \
their ads — what customers say, and what {short} can steal or leverage. Seven AI colleagues, one job each, never two \
people on the same job:
{crew}
You work for {lead}{lead_role}, and you brief the team:
{team}

Every report you read what the scouts found in the last 48 hours, decide what this brand can honestly use, and turn \
the best of it into plays with real references — never invented mock-ups. Write every field people read in \
{language}.

What you report are brand OPPORTUNITIES, not just trends: cultural moments, occasions, creator and community \
behaviour, press windows, competitor moves, platform shifts and risks to the brand. Call them opportunities (or name \
what they are) — never "trends" as a catch-all.

HOW WE WRITE — the house rules for every report ("we don't buy long, lengthy and wordy reports")
- Answer first. The first line is the finding, not the topic: "Gift round-ups favour sets under $40", never \
"Gift round-ups". Titles are findings too — read only the titles and the story must still make sense.
- 3-5 points on the front page. Everything else is appendix.
- Every finding runs result → proof → driver: what happened (with the proof: a number, a name, a date) → why it \
matters for {short} → what we do, and who.
- No adjective without a number beside it ("+40% in a week", "1.2M views", "3 of 5 brands"). Compare when you can: \
vs the last report, vs last week, vs the category.
- A number that isn't in the signals is "not available". Never guess, never round up a hunch into a fact.
- Short sentences, one idea each, plain words a 5th grader follows. No jargon, no sugar-coating, no stating the obvious.
The office shows your work as numbered cards, charts and picture galleries. Words are captions, not essays.
- Hard word limits: opportunity `name` ≤6 words; `insight` ≤15; `what` ≤20; `why_us` ≤20; `risk` ≤15; `move` ≤15; \
`window` ≤6; memo `headline` ≤12; memo `bullets` exactly 3, each ≤18; `top_actions` ≤3, each ≤15; play `title` ≤8; \
`brand_relevance` ≤25; `why_now` ≤15; each hook ≤12; each approach beat ≤12; each tactic ≤15; each `borrow` ≤15; \
`caption` ≤60; `kpi` ≤15; `message` ≤60; `doc_body` ≤120.
- One idea per field. No preamble, no hedging, no repeating what another field already says.
- Name the outlet, creator, brand or post in words. Never mention ids of any kind, the board's mechanics, prompts, \
schemas or counts of what you were sent — write as a colleague, not as a system. Ids belong only in `evidence`, \
`references` and `id` fields.

JUDGING AN OPPORTUNITY (each item of `trends`)
- Only use what is in the signals. Every opportunity cites at least one signal id in `evidence` — prefer signals \
with pictures (posts, videos, articles) so the team can see it. Never invent a post, number, moment or launch.
- `scores` are 0-10 each: brand_fit (how honestly we belong in it), momentum (how fast it is growing), reach (how \
many of our people see it), urgency (how soon the window closes), ease (how easily {team_names} can act on it). \
Overall relevance is not asked for; the office derives it.
- `pillar` is one of {pillars} (None means Watch or Skip at best). `product_key` is a real key from the catalogue. \
`persona` is one of {personas}. `category` is one of {categories}. `platforms` uses only {platforms}. \
`momentum` is rising, peaking, steady or fading. `funnel` is where this opportunity helps most. `formats` lists the \
2-3 content formats that suit it, from: {formats}. `search_terms` are 2-3 phrases to see it live on social.
- `verdict`: Act today = window closes within ~48h and fit is strong. This week = strong fit, slower window. \
Watch = interesting, not yet usable. Skip = popular but wrong for us (list a few so the team sees why not).
- Keep ids stable (short kebab-case): reuse the id when an opportunity matches the recent history.

COMMISSIONING A PLAY
- One play = one person, one lane, one deliverable. `lane` is copied exactly from that person's lanes.
- `pinterest_searches`: only for a Pinterest play, 2 searches for pin formats to study; [] otherwise. \
`borrow_from_brands`: [] (the ad library is not part of this office).

WRITING A PLAY (the studio)
- `references`: pick 2-6 from the reference pool you are given (the evidence and, for Pinterest plays, pins). \
For each, `borrow` says exactly what to take from it: the hook, the framing, the light, the structure, the caption move. \
Only ids from the pool.
- `hooks`: exactly 3 opening lines, each a different approach. Name-drop place, occasion or person.
- `approach`: 3-5 beats in order — slides for a carousel, shots for a reel, sections for a brief or pitch.
- `tactics`: up to 4 concrete steps to get it made and seen (posting time, tagging, seeding, budget, timing).
- `brand_relevance`: why this is ours — pillar, persona, the brand's signature.
- `caption` + `hashtags` (≤6) only for social formats; otherwise "" and []. `doc_*` only for briefs, pitches and \
seeding (for seeding: doc_to = the community, doc_title = the thread, doc_body = the comment, written as a real \
member with no brand name unless the thread asks); otherwise "".
- `message` is the hand-over note to the owner. It MUST start with "Hey <their name>," then the opportunity in one \
sentence and the task with its due day in one. `size` is S, M or L. `due` is YYYY-MM-DD.
- If the play cannot be made without breaking a rule, say which in `blocked_reason`; otherwise "".

Voice: {tone}{exclaim}{banned}
Offers: {offers}
Claims we never make: {claims}

This is a trial office: Mocha's ad desk, Latte's customer voice and the huddle are switched off. Never cite ads or \
customer quotes you were not given. The standing brief follows.

<standing_brief>
{brief}
</standing_brief>"""


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------
# what makes a news story worth reading for this brand: its own words (category, one-liner, products) plus moments
_own = re.split(r"[^\w]+", " ".join([config.BRAND["category"], config.BRAND["one_liner"]]
                                    + [p.get("name", "") for p in config.PRODUCTS]).lower())
TOPIC_WORDS = re.compile("|".join(["celebrit", "launch", "collab", "drop", "viral", "trend", "tiktok", "gift", "holiday"]
                                  + [re.escape(w) for w in dict.fromkeys(_own) if len(w) > 3]), re.I)


def _prune(signals: list[dict], budget: int = 240) -> list[dict]:
    """Keep every social/search/forum/brand signal; rank news so the prompt stays readable."""
    keep = [s for s in signals if s["platform"] != "News"]
    news = [s for s in signals if s["platform"] == "News"]
    words = TOPIC_WORDS

    def score(s: dict) -> float:
        flags = s["metrics"].get("flags", "")
        hits = len(words.findall(s["title"] + " " + s["text"]))
        return hits * 2 + 3 * ("viral" in flags) + 2 * ("launch" in flags) + ("celebrity" in flags) \
            + 2 * (s["kind"] == "brand move") + (1 if s["thumb"] else 0) - (s["age_h"] or 24) / 24
    news.sort(key=score, reverse=True)
    return keep + news[: max(40, budget - len(keep))]


def fmt_of(s: dict) -> str:
    """static, carousel or reel — what a reference looks like, so a brief can mix them."""
    f = str(s["metrics"].get("format") or "").lower()
    if "carousel" in f or f == "carousel_album":
        return "carousel"
    if "video" in f or "reel" in f or s["platform"] in ("TikTok", "YouTube") or "/reel" in (s.get("url") or ""):
        return "reel"
    return "static"


def _line(s: dict) -> str:
    m = ", ".join(f"{k} {v}" for k, v in s["metrics"].items()
                  if k not in ("flags", "bucket", "video", "foreplay", "landing") and v)
    age = f"{s['age_h']:.0f}h ago" if s["age_h"] is not None else ""
    pic = " · has picture" if s.get("thumb") else ""
    text = f" — {s['text'][:150]}" if s["text"] and s["text"][:60] not in s["title"] else ""
    head = " · ".join(x for x in (s["platform"], s["source"], s.get("kind", ""), age, m) if x)
    return f"[{s['id']}] {head}{pic}\n  {s['title']}{text}"


def system_prompt(memory: dict | None = None) -> str:
    path = config.ROOT / "standing_brief.md"
    brief = path.read_text(encoding="utf-8") if path.exists() else config.STANDING_BRIEF
    b, crew = config.BRAND, "\n".join(f"- {x['name']} ({x['role']}): {x['job']}." for x in config.STAFF)
    team = "\n".join(f"- {n} — {m['owns']}. Lanes: {', '.join(m['lanes'])}." for n, m in config.PICS.items())
    return SYSTEM.format(
        agency=config.AGENCY["name"], city=config.AGENCY["city"], brand=b["name"], short=b["short"],
        one_liner=b["one_liner"] or b["category"], lead=config.OWNER["name"],
        lead_role=f", {config.OWNER['role']}" if config.OWNER.get("role") else "", market=config.MARKET_NAME,
        crew=crew, team=team or "- (no team members yet)", team_names=config.TEAM or "the team",
        language=config.REPORT_LANGUAGE, pillars=" / ".join(PILLARS), personas=" / ".join(PERSONAS),
        categories=" / ".join(CATEGORIES), platforms=" / ".join(PLATFORMS), formats=", ".join(FORMATS),
        brands=", ".join(config.COMPETITORS) or "the brands you are shown",
        tone=b["tone"], exclaim=" No exclamation marks in brand copy." if b["no_exclamation_marks"] else "",
        banned=(" Banned words: " + ", ".join(b["banned_words"]) + ".") if b["banned_words"] else "",
        offers=b["offer_rules"] or "none set — never invent a discount.",
        claims="; ".join(b["claims_never"]) or "none listed — no medical or unprovable claims.",
        brief=brief)


def _context(sweep: dict, memory: dict, now: datetime) -> dict[str, str]:
    from .desks import brands_summary, radar_summary  # desks imports this module
    local = now.astimezone(ZoneInfo(config.TZ))
    today = local.date()
    ny = now.astimezone(ZoneInfo(config.OFFICE_TZ))
    upcoming = [f"- {e['date']} {e['name']} [{e['kind']}] (in {(date.fromisoformat(e['date']) - ny.date()).days} days)"
                + (f" — {config.BRAND['short']}: {e['brand_note']}" if e.get("brand_note") else "")
                for e in calendar_world.occasions(ny.date(), ny.date() + timedelta(days=60))
                if e["date"] >= ny.date().isoformat() and (e["decor"] or e["kind"] != "civic")]
    cat = [f"- {p['key']}: {p['title']} — ${p['price']:.0f}"
           f"{' (compare-at $%.0f)' % p['compare_at'] if p['compare_at'] else ''}"
           f"{'' if p['in_stock'] else ' — OUT OF STOCK'}" for p in sweep["catalogue"]]

    huddle_txt = (f"Trial office: there is no huddle with {config.OWNER['name']}. Work from the standing brief; say in the "
                  "memo what you would ask her.")

    plays = [f"- {p['id']} [{p['pic']} · {p['lane']} · due {p['due']} · {p['status']}] {p['title']} (trend {p['trend_id']})"
             for p in memory.get("plays", []) if p["status"] in ("new", "sent")]
    hist = [f"- {t['id']}: {t['name']} — first seen {t['first_seen'][:10]}, last seen {t['last_seen'][:10]}, "
            f"seen {t['times']}x, last verdict {t['verdict']}" for t in memory.get("trend_history", [])[-40:]]
    status = [f"- {k}: {'ok, ' + str(v['count']) + ' signals' if v['ok'] else 'OFFLINE — ' + v['note']}"
              for k, v in sweep["status"].items()]
    return {
        "now": f"Now: {ny.strftime('%A %d %B %Y, %H:%M')} in {config.AGENCY['city']}, where the office is "
               f"({local.strftime('%A %H:%M')} for {config.OWNER['name']} in {config.TEAM_CITY}).",
        "huddle": huddle_txt,
        "calendar": f"{config.MARKET_NAME} calendar, next 60 days (with {config.BRAND['short']}'s own notes):\n" + ("\n".join(upcoming) or "- none"),
        "catalogue": "Live catalogue (use these keys for product keys):\n" + "\n".join(cat),
        "plays": "Plays already with the team:\n" + ("\n".join(plays) or "- none"),
        "history": "Recent opportunity history (reuse ids when it's the same one):\n" + ("\n".join(hist) or "- none yet"),
        "status": "Scout status this sweep:\n" + "\n".join(status),
        "radar": radar_summary(memory.get("radar")),
        "brands": brands_summary(memory.get("brands")),
    }


# who signs the memo and who owns actions — from the profile, never one team's names
DIRECTOR = next((x["name"] for x in config.STAFF if x["id"] == "coca"), "The director")
OWNER_EXAMPLE = ", ".join(f'"{n}: …"' for n in [*config.PICS, config.OWNER["name"]])

BOARD_ASK = {
    "report": ("Strategy desk, a full REPORT. " + DIRECTOR + "'s memo is the executive summary — if it is the only thing "
               "the lead reads, it must stand alone: `headline` = the answer, the one thing to remember (≤12 words); "
               "`bullets` = the 3 findings that matter most across the desks (culture, occasions, brands), each written as "
               "what happened → why it matters → what we do; `top_actions` start with the owner (" + OWNER_EXAMPLE + ") and "
               "end with the day. Then the full opportunity board (8-12, including a few Skips), and commission 3-4 new "
               "plays across social, seeding, earned media and growth — at least one for each person on the team, the "
               "strongest first (it is the one the studio writes up). Paid ads (formats `ad` and `ugc`) belong to the ad "
               "desk, which is off in this office; don't commission them. When social signals are thin, anchor plays to "
               "the calendar (cite its calendar signal) rather than commissioning fewer. `staff_status`, `staff_learned` "
               "and `staff_questions` each have one entry per crew member, in this order: CREW — what each is doing "
               "(≤12 words), what each would take from a huddle (say plainly there was none), and the question each would "
               "ask the lead (≤20 words, naming real opportunities, dates or plays)."),
}


def board_prompt(sweep: dict, memory: dict, slot: str, now: datetime) -> str:
    c = _context(sweep, memory, now)
    sigs = _prune(sweep["signals"])
    return "\n\n".join([
        c["now"] + f" Slot: {slot}.", BOARD_ASK["report"].replace("CREW", ", ".join(x["name"] for x in config.STAFF)),
        c["huddle"], c["radar"], c["brands"], c["calendar"], c["catalogue"],
        c["plays"] + "\n(retire any that the news makes wrong; never commission a duplicate)", c["history"], c["status"],
        f"Signals ({len(sigs)} of {len(sweep['signals'])} collected, last {config.WINDOW_HOURS}h):\n"
        + "\n".join(_line(s) for s in sigs),
    ])


def reference_pool(sweep: dict, board: dict, order: dict, fetch_pins) -> list[dict]:
    """Real references for one play: its opportunity's evidence, and pins for a Pinterest play."""
    t = {x["id"]: x for x in board["trends"]}.get(order["trend_id"], {})
    by_id = {s["id"]: s for s in sweep["signals"]}
    evidence = [by_id[i] for i in t.get("evidence", []) if i in by_id]
    pins = []
    if order["format"] == "pin" or order["lane"].startswith("Pinterest"):
        for q in order["pinterest_searches"][:2]:
            try:
                pins += fetch_pins(q)
            except Exception as e:  # noqa: BLE001 — a missing reference shelf is never fatal
                log.info("pinterest %r failed: %s", q, e)
    pool, seen = [], set()
    for s in evidence + pins:
        if s["id"] not in seen:
            seen.add(s["id"])
            pool.append(s)
    return pool


def studio_prompt(sweep: dict, memory: dict, board: dict, order: dict, pool: list[dict], now: datetime) -> str:
    c = _context(sweep, memory, now)
    t = {x["id"]: x for x in board["trends"]}.get(order["trend_id"], {})
    return "\n\n".join([
        c["now"],
        f"Studio. Write this one commissioned play. Person: {order['pic']}. Lane: {order['lane']}. Format: "
        f"{order['format']}. Check every line against the rules.",
        f"The trend: {t.get('name', order['trend_id'])} — {t.get('verdict', '?')}, window {t.get('window', '?')}, "
        f"pillar {t.get('pillar', '?')}, product {t.get('product_key', '?')}, persona {t.get('persona', '?')}, "
        f"funnel {t.get('funnel', '?')}.\nInsight: {t.get('insight', '')}\nWhat: {t.get('what', '')}\n"
        f"Why us: {t.get('why_us', '')}\nRisk: {t.get('risk', '')}\nStrategist's angle: {order['angle']}",
        DIRECTOR + "'s memo: " + board["memo"]["headline"],
        c["calendar"], c["catalogue"],
        "Reference pool — choose by id:\n"
        + ("\n".join(f"{_line(x)}\n  format: {fmt_of(x)}" for x in pool) or "- none"),
    ])


# ---------------------------------------------------------------------------
# The calls
# ---------------------------------------------------------------------------
def _call(client, system: str, user: str, schema: dict, effort: str) -> tuple[dict, dict]:
    with client.beta.messages.stream(
        model=config.MODEL,
        max_tokens=64000,
        betas=["server-side-fallback-2026-07-01"],
        # the system prompt is identical across both desks, so later calls can read it from cache
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        extra_body={"fallbacks": "default"},
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"model declined: {getattr(msg, 'stop_details', None)}")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("output hit max_tokens — the JSON is incomplete")
    u = msg.usage
    cr, cw = getattr(u, "cache_read_input_tokens", 0) or 0, getattr(u, "cache_creation_input_tokens", 0) or 0
    usd = (u.input_tokens * PRICE_USD["input"] + u.output_tokens * PRICE_USD["output"]
           + cr * PRICE_USD["cache_read"] + cw * PRICE_USD["cache_write"]) / 1e6
    usage = {"model": msg.model, "effort": effort, "input": u.input_tokens, "output": u.output_tokens,
             "cache_read": cr, "cache_write": cw, "usd": round(usd, 3)}
    return json.loads(next(b.text for b in msg.content if b.type == "text")), usage


def think(sweep: dict, memory: dict, slot: str = "report", now: datetime | None = None,
          fetch_pins=None) -> tuple[dict, dict]:
    """Run the trial desks. Returns (office, usage); office is the board plus `new_plays`, `locked_plays`,
    `radar`, `brands` and `occasions`.

    Order: the culture radar, the brand watch and the occasion pulse side by side → the strategy desk → the
    studio writes the top commissioned play (config.TRIAL_PLAYS); the rest are kept as titles, locked."""
    import anthropic
    from concurrent.futures import ThreadPoolExecutor

    from . import desks, sources
    fetch_pins = fetch_pins or sources.pinterest
    now = now or datetime.now(timezone.utc)
    # long structured outputs with thinking can run past the SDK's 10-minute default
    client = anthropic.Anthropic(api_key=config.env("ANTHROPIC_API_KEY") or None, max_retries=2, timeout=1800.0)
    system = system_prompt(memory)
    usage = {"usd": 0.0}
    mem = dict(memory)

    def desk(name, fn, *args):
        try:
            return fn(client, system, *args)
        except Exception as e:  # noqa: BLE001 — the board still ships without one desk
            log.exception("%s failed", name)
            usage[f"{name}_failed"] = str(e)[:200]
            return None, None

    with ThreadPoolExecutor(max_workers=3) as ex:
        fut_radar = ex.submit(desk, "radar", desks.radar, _prune(sweep["signals"]), memory, now)
        fut_brands = ex.submit(desk, "brands", desks.brands, desks.brand_signals(sweep["signals"]), memory, now)
        fut_occ = ex.submit(desk, "occasions", desks.occasions, sources.upcoming_occasions(), sweep["signals"], now)
        results = {"radar": fut_radar.result(), "brands": fut_brands.result(), "occasions": fut_occ.result()}
    for name, (out, u) in results.items():
        if out:
            mem[name] = out
            usage[name], usage["usd"] = u, usage["usd"] + u["usd"]

    board, u1 = _call(client, system, board_prompt(sweep, mem, slot, now), BOARD_SCHEMA, "high")
    log.info("strategy desk: %d trends, %d commissioned, %s", len(board["trends"]), len(board["commission"]), u1)
    for t in board["trends"]:
        t["refs"] = []
    for o in board["commission"]:
        o["format"] = o["format"] if o["format"] in FORMATS else "static"
    usage["board"], usage["usd"] = u1, usage["usd"] + u1["usd"]

    # the studio writes the strongest play in full; the others stay as titles in the office, locked
    orders, rest = board["commission"][:config.TRIAL_PLAYS], board["commission"][config.TRIAL_PLAYS:]
    trend_name = {t["id"]: t["name"] for t in board["trends"]}
    board["locked_plays"] = [{"pic": o["pic"], "lane": o["lane"], "format": o["format"], "angle": o["angle"],
                              "trend": trend_name.get(o["trend_id"], o["trend_id"])} for o in rest]
    board["new_plays"], usage["studio"], failed = [], [], []
    known = {s["id"] for s in sweep["signals"]}
    for order in orders:
        pool = reference_pool(sweep, board, order, fetch_pins)
        for s in pool:
            if s["id"] not in known:
                sweep["signals"].append(s)
                known.add(s["id"])
        try:
            play, u = _call(client, system, studio_prompt(sweep, mem, board, order, pool, now), PLAY_SCHEMA, "medium")
        except Exception as e:  # noqa: BLE001 — logged and surfaced in the office, never fatal
            failed.append({"order": order, "error": str(e)[:200]})
            continue
        usage["studio"].append(u)
        reason = play.pop("blocked_reason", "").strip()
        if reason:
            board["blocked"].append({"idea": f"{play['title']} ({order['pic']})", "rule": reason})
            continue
        board["new_plays"].append({**play, "trend_id": order["trend_id"], "pic": order["pic"],
                                   "lane": order["lane"], "format": order["format"]})
    board["radar"], board["brands"], board["occasions"] = mem.get("radar") if results["radar"][0] else None, \
        mem.get("brands") if results["brands"][0] else None, results["occasions"][0]
    usage["studio_failed"] = failed
    usage["usd"] = round(usage["usd"] + sum(x["usd"] for x in usage["studio"]), 3)
    log.info("studio: %d written, %d locked, total $%s", len(board["new_plays"]), len(board["locked_plays"]), usage["usd"])
    return board, usage
