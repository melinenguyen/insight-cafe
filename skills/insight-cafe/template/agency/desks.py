"""
The desks that sit beside the strategy desk, one job each, every one written the report-and-presentation way
(answer first, 3-5 findings, result → proof → driver, the rest as appendix).

The trial office runs three of them: Espresso's culture radar and occasion pulse, and Chai's brand watch.
Latte's customer voice, Mocha's ad desk and the learning desk are part of the full Insight Café.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from . import config
from .brain import S, SA, I, _call, _enum, _line, _obj

log = logging.getLogger("agency.desks")

B, SHORT, LEAD = config.BRAND, config.BRAND["short"], config.OWNER["name"]
OWNERS = list(dict.fromkeys(list(config.PICS) + [config.OWNER["name"], "Nobody yet"]))


# ---------------------------------------------------------------------------
# Culture & social radar (Espresso) — the original trend agent's beat (pop culture, Hollywood, viral social,
# beauty, fashion, events, search, hashtags), written the report-and-presentation way: one answer,
# 3-5 moves that matter (what happened → proof → why us → what we steal, and who), a short rising/fading list,
# the week ahead, and every other signal as a one-line appendix. Brand launches belong to Chai's brand watch.
# ---------------------------------------------------------------------------
SECTIONS = ["Pop culture", "Hollywood & celebrity", "Viral social"] + (config.RADAR_EXTRA or ["Our category"]) + \
           ["Fashion & style", "Cultural events", "Search spikes", "Hashtags"]
HEAT = ["now", "this week", "watch"]
RADAR_SCHEMA = _obj({
    "headline": S,
    "moves": {"type": "array", "items": _obj({
        "title": S, "area": _enum(SECTIONS), "happened": S, "proof": S, "why_us": S, "steal": S,
        "owner": _enum(OWNERS), "heat": _enum(HEAT), "relevance": I, "evidence": SA})},
    "watch": {"type": "array", "items": _obj({"name": S, "line": S, "direction": _enum(["rising", "fading"])})},
    "skip": {"type": "array", "items": _obj({"name": S, "why": S})},
    "week": SA,
    "signals": {"type": "array", "items": _obj({"area": _enum(SECTIONS), "name": S, "line": S, "heat": _enum(HEAT),
                                                 "relevance": I, "evidence": SA})},
    "creator_brief": _obj({"concept": S, "creator": S, "deliverable": S, "hook": S}),
})


def pictured(ids: list[str], by_id: dict) -> list[str]:
    """Evidence with a picture first: the office shows the first one big."""
    return sorted(ids, key=lambda i: not (by_id.get(i) or {}).get("thumb"))


def _clamp(v) -> int:
    return max(1, min(10, int(v)))


def radar(client, system: str, sigs: list[dict], memory: dict, now: datetime) -> tuple[dict, dict]:
    prev = memory.get("radar") or {}
    seen = [x.get("title") or x.get("name", "") for x in prev.get("moves", prev.get("pulse", []))]
    user = "\n\n".join([
        f"Culture & social radar (Espresso), {now:%A %d %B %Y}. Your one job: what happened in culture and social in {config.MARKET_NAME} "
        "in the last 48 hours — " + ", ".join(x.lower() for x in SECTIONS) + f" — and what it means for {B['name']}. Other "
        "brands' launches and campaigns are Chai's (brand watch) and their ads are Mocha's: leave them out unless the "
        "culture moment is bigger than the brand. Our own creators' posts (codes, captions, compliance) are the plays "
        "desk's, not culture. Use only the public signals below (news and PR, Google Trends, the calendar).",
        "Write it for a busy brand lead, by the house rules:\n"
        "- `headline` (≤20 words): the answer — the one thing to remember from today's culture.\n"
        f"- `moves`: exactly 3-5, ranked by what matters most to {SHORT}. `title` (≤10 words) is the finding, not the topic. "
        "`happened` (≤25 words): what happened, naming who/where. `proof` (≤15 words): the number or fact that shows it "
        f"is real — views, growth, rank, date — or \"not available\". `why_us` (≤20): why it matters for {SHORT}. `steal` "
        f"(≤18): exactly what we take or do. `owner`: {', '.join(OWNERS[:-1])} ({LEAD} = a decision) or Nobody yet. `heat`: now = act "
        f"within hours, this week = strong momentum, watch = slow burn. `relevance` 1-10 for {SHORT}. `evidence`: 1-3 "
        "signal ids — every move rests on a real signal, and the first one should carry a picture ('has picture') so "
        "the team sees the proof; a calendar date alone is not proof.\n"
        "- `watch`: up to 6 one-liners (line ≤15 words) of what is rising or fading but not yet worth a move.\n"
        "- `skip`: up to 3 loud moments that are wrong for us, and why (≤15 words) — so the team learns what not to chase.\n"
        "- `week`: 7 lines, one per day starting tomorrow, as 'Mon · the moment · what we do' (≤14 words each).\n"
        "- `signals`: the appendix — 10-20 other real signals worth a glance, one line each (name ≤7 words, line ≤18), "
        "with area, heat, relevance and 1-2 evidence ids. Hashtags go here as '#tag' with how to use it.\n"
        "- `creator_brief`: one creator idea of the week (concept, creator profile, deliverable, hook ≤12 words).\n"
        "",
        "On the radar last report (repeat only if it moved, and say how): " + ("; ".join(seen) or "none"),
        f"Signals ({len(sigs)}):\n" + "\n".join(_line(s) for s in sigs),
    ])
    out, usage = _call(client, system, user, RADAR_SCHEMA, "medium")
    known = {s["id"]: s for s in sigs}
    for key in ("moves", "signals"):
        for it in out[key]:
            it["evidence"] = pictured([e for e in it["evidence"] if e in known], known)
            it["relevance"] = _clamp(it["relevance"])
        out[key] = [it for it in out[key] if it["evidence"] or it["area"] == "Hashtags"]
    out["moves"] = sorted(out["moves"], key=lambda x: -x["relevance"])[:5]
    out["generated_at"] = now.isoformat()
    log.info("culture radar: %d moves, %d signals, $%s", len(out["moves"]), len(out["signals"]), usage["usd"])
    return out, usage


def radar_summary(radar: dict | None) -> str:
    if not radar:
        return ""
    if "moves" not in radar:  # written before 25 Oct 2026
        return f"Espresso's culture radar ({radar.get('generated_at', '')[:16]}): {radar.get('summary', '')}"
    lines = [f"Espresso's culture radar ({radar.get('generated_at', '')[:16]}): {radar.get('headline', '')}"]
    lines += [f"- [{m['area']} · {m['heat']} · relevance {m['relevance']}] {m['title']}: {m['happened']} "
              f"Proof: {m['proof']}. Steal: {m['steal']} ({m['owner']})" for m in radar.get("moves", [])]
    lines += [f"- {w['direction']}: {w['name']} — {w['line']}" for w in radar.get("watch", [])]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Brand watch (Chai) — what other brands launched, said and did: launches, collaborations, campaigns,
# promotions and pricing, retail and channel moves, press, their own social posts. Ads are Mocha's.
# ---------------------------------------------------------------------------
BRAND_KINDS = ["Launch", "Collab", "Campaign", "Promo & pricing", "Retail & channel", "PR & press", "Social"]
BRANDS_SCHEMA = _obj({
    "headline": S,
    "moves": {"type": "array", "items": _obj({
        "brand": S, "title": S, "kind": _enum(BRAND_KINDS), "happened": S, "proof": S, "why_us": S, "steal": S,
        "owner": _enum(OWNERS), "evidence": SA})},
    "also": {"type": "array", "items": _obj({"brand": S, "line": S, "evidence": SA})},
    "quiet": SA,
})


def watched_brands() -> list[str]:
    return config.COMPETITORS


def brand_signals(sigs: list[dict]) -> list[dict]:
    """What Chai reads: brand-move feeds, brands' own posts, launch news, and any story naming a watched brand."""
    names = re.compile("|".join(re.escape(n) for n in watched_brands()), re.I) if watched_brands() else None
    out = []
    for s in sigs:
        m = s["metrics"]
        if s["kind"] in ("brand move", "brand post") or m.get("brand_post") or "launch" in (m.get("flags") or "") \
                or (names and s["kind"] in ("news", "post", "video") and names.search(s["title"] + " " + s["text"][:300])):
            out.append(s)
    return out[:160]


def brands(client, system: str, sigs: list[dict], memory: dict, now: datetime) -> tuple[dict, dict]:
    prev = memory.get("brands") or {}
    user = "\n\n".join([
        f"Brand watch (Chai), {now:%A %d %B %Y}. Your one job: what other brands launched, said and did in the last "
        "48 hours — launches, collaborations, campaigns, promotions and pricing, retail and channel moves, press, their "
        f"own social posts — and what {B['name']} can steal or must answer. Watch the like-minded brands we position "
        "beside and the direct competitors: " + ", ".join(watched_brands()) + ".",
        "Write it by the house rules:\n"
        "- `headline` (≤20 words): the answer — the brand move that matters most to us today, or plainly that it was a "
        "quiet day.\n"
        f"- `moves`: 3-5 at most (fewer is honest on a quiet day), ranked by what matters to {SHORT}. `title` (≤10 words) "
        "is the finding. `happened` (≤25): what the brand did, where. `proof` (≤15): price, date, outlet, numbers — or "
        f"\"not available\". `why_us` (≤20). `steal` (≤18): what we copy, counter or avoid. `owner`: {', '.join(OWNERS[:-1])} "
        "or Nobody yet. `evidence`: 1-3 signal ids, the first one with a picture where possible — never invent a move.\n"
        "- `also`: up to 8 smaller moves, one line each (≤15 words) with evidence.\n"
        "- `quiet`: watched brands with nothing new.",
        "Last report's headline: " + (prev.get("headline") or "none"),
        f"Signals ({len(sigs)}):\n" + ("\n".join(_line(s) for s in sigs) or "- none"),
    ])
    out, usage = _call(client, system, user, BRANDS_SCHEMA, "medium")
    known = {s["id"]: s for s in sigs}
    for key in ("moves", "also"):
        for it in out[key]:
            it["evidence"] = pictured([e for e in it["evidence"] if e in known], known)
        out[key] = [it for it in out[key] if it["evidence"]]
    out["moves"] = out["moves"][:5]
    out["generated_at"] = now.isoformat()
    log.info("brand watch: %d moves, %d smaller, $%s", len(out["moves"]), len(out["also"]), usage["usd"])
    return out, usage


def brands_summary(b: dict | None) -> str:
    if not b:
        return ""
    lines = [f"Chai's brand watch ({b.get('generated_at', '')[:16]}): {b.get('headline', '')}"]
    lines += [f"- {m['brand']} [{m['kind']}] {m['title']}: {m['happened']} Proof: {m['proof']}. Steal: {m['steal']} "
              f"({m['owner']})" for m in b.get("moves", [])]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The occasion pulse (Espresso) — the calendar as a trend report: for the next few occasions that matter to
# the brand, what people think, feel, do, buy and post around them right now, with the proof.
# ---------------------------------------------------------------------------
INSIGHT_KINDS = ["Think", "Feel", "Do", "Buy", "Post"]
OCCASION_SCHEMA = _obj({
    "headline": S,
    "occasions": {"type": "array", "items": _obj({
        "name": S, "theme": S, "mood": S,
        "insights": {"type": "array", "items": _obj({"kind": _enum(INSIGHT_KINDS), "fact": S, "evidence": SA})},
        "our_move": S, "owner": _enum(OWNERS), "evidence": SA})},
})


def occasions(client, system: str, upcoming: list[dict], sigs: list[dict], now: datetime) -> tuple[dict, dict]:
    names = [re.sub(r" \(.*\)$", "", e["name"]) for e in upcoming]
    words = re.compile("|".join(re.escape(w.split()[0]) for w in names), re.I) if names else None
    pool = [s for s in sigs if s["kind"] == "occasion news" or (words and s["kind"] in ("post", "video", "news")
                                                                and words.search(s["title"] + " " + s["text"][:200]))][:150]
    user = "\n\n".join([
        f"The occasion pulse (Espresso), {now:%A %d %B %Y}. The calendar as a trend report: for each occasion below, "
        f"what people in {config.MARKET_NAME} think, feel, do, buy and post around it RIGHT NOW, and what {B['name']} does about it.",
        f"Occasions, in date order (keep this order and these names; follow {SHORT}'s own notes):\n" + "\n".join(
            f"- {n} · {e['date']} ({(datetime.fromisoformat(e['date']).date() - now.date()).days} days)"
            + (f" — {SHORT}: {e['brand_note']}" if e.get("brand_note") else "") for n, e in zip(names, upcoming)),
        "Write by the house rules. `headline` (≤20 words): the one thing to know about the season ahead. Per occasion: "
        "`theme` (≤8 words: its mood this year, in a phrase); `mood` (≤20 words: how people feel about it this year); "
        "3-5 `insights`, each a fact with a number or a named source (≤22 words) and 1-2 signal ids in `evidence` — "
        "Think (beliefs, attitudes), Feel (mood, pressure, joy), Do (plans, rituals, travel, hosting), Buy (spend, gifts, "
        "price points), Post (what they share, hashtags, formats). Prefer current coverage; if a survey is from an "
        "earlier year, say the year. Never invent a number. `our_move` (≤20 words) + `owner`; `evidence` = 1-3 ids "
        "with pictures that best show the occasion. Fewer insights is honest when the signals are thin.",
        f"Signals ({len(pool)}):\n" + ("\n".join(_line(s) for s in pool) or "- none"),
    ])
    out, usage = _call(client, system, user, OCCASION_SCHEMA, "medium")
    known = {s["id"]: s for s in pool}
    for o, e in zip(out["occasions"], upcoming):
        o.update(date=e["date"], key=e.get("decor") or "", colors=e.get("colors") or [], note=e.get("brand_note", ""))
        o["evidence"] = pictured([i for i in o["evidence"] if i in known], known)
        for i in o["insights"]:
            i["evidence"] = pictured([x for x in i["evidence"] if x in known], known)
        o["insights"] = [i for i in o["insights"] if i["evidence"]]
    out["generated_at"] = now.isoformat()
    log.info("occasion pulse: %d occasions, %d insights, $%s", len(out["occasions"]),
             sum(len(o["insights"]) for o in out["occasions"]), usage["usd"])
    return out, usage
