"""
The agency's memory. One JSON file in agency/data, so the next run remembers what the team was already
told and which opportunities it has seen before.

memory.json
  plays                     every play still alive, with status new → sent → retired / expired
  trends / trend_history    the current board and a 30-day log of what was seen when
  library                   the signals that trends and plays cite, kept so evidence
                            and inspiration survive after the 48h window moves on
  memo, staff, questions,   the latest office copy
  blocked, runs
  radar, brands, occasions  the desks' latest reports (culture, brand watch, the occasion pulse)
  locked_plays              plays the strategy desk commissioned that the trial doesn't write
  digests                   one short summary per report
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import config

PATH = config.DATA / "memory.json"
VERDICT_RANK = {"Act today": 0, "This week": 1, "Watch": 2, "Skip": 3}


def load() -> dict:
    if PATH.exists():
        return json.loads(PATH.read_text(encoding="utf-8"))
    return {"plays": [], "trends": [], "trend_history": [], "library": {}, "huddle_history": [], "runs": []}


def save(memory: dict) -> None:
    config.DATA.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(memory, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _today(now: datetime) -> date:
    return now.astimezone(ZoneInfo(config.TZ)).date()


def _pick(value: str, allowed: list[str], default: str) -> str:
    v = (value or "").strip()
    for a in allowed:
        if v.lower() == a.lower():
            return a
    for a in allowed:  # tolerate "Gift Guide pillar" or "the gifting"
        if a.lower() in v.lower() or (v and v.lower() in a.lower()):
            return a
    return default


def _due(value: str, today: date) -> str:
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except (ValueError, TypeError):
        return (today + timedelta(days=2)).isoformat()


# brand fit matters most: a fast, huge trend we don't belong in should still score low
WEIGHTS = {"brand_fit": 0.40, "momentum": 0.20, "reach": 0.15, "urgency": 0.15, "ease": 0.10}


def normalise(office: dict, today: date) -> dict:
    """Fold the model's flat fields into the shape the office reads, and keep values on the lists."""
    from . import brain
    for t in office["trends"]:
        t["category"] = _pick(t["category"], brain.CATEGORIES, "Internet culture")
        t["platforms"] = [p for p in (_pick(x, brain.PLATFORMS, "") for x in t["platforms"]) if p] or ["News"]
        t["momentum"] = _pick(t["momentum"], ["rising", "peaking", "steady", "fading"], "steady")
        t["formats"] = [f for f in (_pick(x, brain.FORMATS, "") for x in t["formats"]) if f][:3]
        t["scores"] = {k: max(0, min(10, int(t["scores"].get(k, 0)))) for k in WEIGHTS}
        t["relevance"] = round(sum(t["scores"][k] * w for k, w in WEIGHTS.items()) * 10)
        t["fit"] = {"pillar": _pick(t.pop("pillar"), brain.PILLARS, "None"), "product_key": t.pop("product_key"),
                    "persona": _pick(t.pop("persona"), brain.PERSONAS, "None")}
    for p in office["new_plays"]:
        lanes = config.PICS[p["pic"]]["lanes"]
        p["lane"] = _pick(p["lane"], lanes, lanes[0])
        p["size"] = _pick(p["size"], ["S", "M", "L"], "M")
        p["due"] = _due(p["due"], today)
        p["hashtags"] = ["#" + h.lstrip("#").replace(" ", "") for h in p["hashtags"] if h.strip()][:6]
        p["doc"] = {"title": p.pop("doc_title"), "to": p.pop("doc_to"), "body": p.pop("doc_body")}
    status, learned, questions = (office.pop(k, []) for k in ("staff_status", "staff_learned", "staff_questions"))
    at = lambda xs, i: (xs[i] if i < len(xs) else "").strip()  # noqa: E731 — missing entries fall back below
    office["staff"] = {sid: {"status": at(status, i), "learned": at(learned, i)} for i, sid in enumerate(config.STAFF_IDS)}
    office["questions"] = {s["id"]: at(questions, i) or s["question"] for i, s in enumerate(config.STAFF)}
    office["memo"]["bullets"] = office["memo"].get("bullets", [])[:3]
    office["memo"]["top_actions"] = office["memo"].get("top_actions", [])[:3]
    return office


def merge(memory: dict, office: dict, sweep: dict, slot: str, usage: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    office = normalise(office, _today(now))
    today = _today(now)
    sigmap = {s["id"]: s for s in sweep["signals"]}
    library = dict(memory.get("library", {}))
    known = lambda sid: sid in sigmap or sid in library  # noqa: E731

    # --- trends: replace the board, but only keep evidence that really exists ---
    board = []
    for t in office["trends"]:
        t["evidence"] = [e for e in t["evidence"] if known(e)]
        t["looks"] = [e for e in t.get("refs", t.get("looks", [])) if known(e)]  # like-minded brands' ads
        t["verified"] = bool(t["evidence"])
        board.append(t)
    board.sort(key=lambda t: (VERDICT_RANK[t["verdict"]], -t["relevance"]))
    memory["trends"] = board

    hist = {h["id"]: h for h in memory.get("trend_history", [])}
    for t in board:
        h = hist.get(t["id"]) or {"id": t["id"], "first_seen": now.isoformat(), "times": 0}
        h.update(name=t["name"], last_seen=now.isoformat(), verdict=t["verdict"], times=h["times"] + 1)
        hist[t["id"]] = h
    cutoff = (now - timedelta(days=30)).isoformat()
    memory["trend_history"] = sorted([h for h in hist.values() if h["last_seen"] >= cutoff], key=lambda h: h["last_seen"])
    first_seen = {h["id"]: h["first_seen"] for h in memory["trend_history"]}
    for t in board:
        t["first_seen"] = first_seen.get(t["id"], now.isoformat())

    # --- plays: retire, expire, then add the new ones ---
    # plays from before the reference-board format (24 Oct 2026) have no hooks: let them go
    plays = [p for p in memory.get("plays", []) if "hooks" in p]
    retire = {r["id"]: r["reason"] for r in office["retire_plays"]}
    for p in plays:
        if p["id"] in retire and p["status"] not in ("retired", "expired"):
            p.update(status="retired", retired_reason=retire[p["id"]], retired_at=now.isoformat())
        elif p["status"] in ("new", "sent") and date.fromisoformat(p["due"]) < today - timedelta(days=3):
            p.update(status="expired")
    stamp = today.strftime("%m%d")
    taken = {p["id"] for p in plays}
    for np in office["new_plays"]:
        base = f"{stamp}-{np['pic'][0].lower()}-{re.sub(r'[^a-z0-9]+', '-', np['slug'].lower()).strip('-')[:28]}"
        pid, n = base, 2
        while pid in taken:
            pid, n = f"{base}-{n}", n + 1
        taken.add(pid)
        np["message"] = _ensure_greeting(np["message"], np["pic"])
        np["references"] = [r for r in np["references"] if known(r["id"])]
        plays.append({**np, "id": pid, "status": "new", "created_at": now.isoformat(), "slot": slot})
    # keep a 21-day tail of finished plays for the archive room
    tail = (now - timedelta(days=21)).isoformat()
    memory["plays"] = [p for p in plays if p["status"] in ("new", "sent") or p.get("created_at", "") >= tail]

    # --- the desks' reports (a desk that failed keeps its last report) ---
    if office.get("radar"):
        memory["radar"] = office["radar"]
    if office.get("brands"):
        memory["brands"] = office["brands"]
    if office.get("occasions"):
        memory["occasions"] = office["occasions"]
    memory["locked_plays"] = office.get("locked_plays", [])

    # --- library: every signal a live trend, play or desk report still points at ---
    live_ids = {e for t in board for e in t["evidence"] + t["looks"]}
    live_ids |= {r["id"] for p in memory["plays"] if p["status"] in ("new", "sent") for r in p["references"]}
    radar = memory.get("radar") or {}
    live_ids |= {e for k in ("moves", "signals", "pulse") for it in radar.get(k, []) for e in it["evidence"]}
    live_ids |= {e for k in ("moves", "also") for it in (memory.get("brands") or {}).get(k, []) for e in it["evidence"]}
    for o in (memory.get("occasions") or {}).get("occasions", []):
        live_ids |= set(o["evidence"]) | {e for i in o["insights"] for e in i["evidence"]}
    memory["library"] = {sid: sigmap.get(sid) or library[sid] for sid in live_ids if known(sid)}

    # --- the rest of the office copy ---
    for key in ("memo", "staff", "blocked"):
        memory[key] = office[key]
    if slot != "sweep" or not memory.get("questions"):
        memory["questions"] = office["questions"]
    memory["scouts"] = sweep["status"]
    memory["catalogue"] = sweep["catalogue"]
    memory["swept_at"] = sweep["swept_at"]
    memory["updated_at"] = now.isoformat()
    memory["slot"] = slot
    memory.setdefault("runs", []).append({"at": now.isoformat(), "slot": slot, "usage": usage,
                                          "signals": len(sweep["signals"]), "new_plays": len(office["new_plays"])})
    memory["runs"] = memory["runs"][-60:]
    if slot in config.REPORTS:
        memory["digests"] = (memory.get("digests", []) + [digest(memory, office, slot, now, usage,
                                                                 len(sweep["signals"]))])[-120:]
    return memory


SLOT_LABEL = {"report": "Report"}


def digest(memory: dict, office: dict, slot: str, now: datetime, usage: dict, signals: int) -> dict:
    """One report in a few lines, for the archive: the answer, the three findings, what each desk said, the plays."""
    memo, trends = office.get("memo") or {}, memory.get("trends", [])
    radar, brands = memory.get("radar") or {}, memory.get("brands") or {}
    live = [p for p in memory.get("plays", []) if p["status"] in ("new", "sent")]
    report = slot in config.REPORTS  # the desks only write with the two reports; a re-plan reuses theirs
    return {
        "at": now.isoformat(), "slot": slot, "label": SLOT_LABEL.get(slot, slot),
        "headline": memo.get("headline", ""), "focuses": memo.get("bullets", [])[:3],
        "actions": memo.get("top_actions", [])[:3],
        "desks": {"culture": radar.get("headline") or radar.get("summary", ""), "brands": brands.get("headline", ""),
                  "occasions": (memory.get("occasions") or {}).get("headline", "")} if report else {},
        "act_today": [t["name"] for t in trends if t["verdict"] == "Act today"][:5],
        "plays": [{"title": p["title"], "pic": p["pic"]} for p in office.get("new_plays", [])],
        "numbers": {"signals": signals, "act_today": sum(t["verdict"] == "Act today" for t in trends),
                    "this_week": sum(t["verdict"] == "This week" for t in trends), "live_plays": len(live),
                    "new_plays": len(office.get("new_plays", []))},
        "usd": round(usage.get("usd", 0) or 0, 2),
    }


def _ensure_greeting(msg: str, pic: str) -> str:
    msg = msg.strip()
    return msg if msg.lower().startswith(f"hey {pic.lower()}") else f"Hey {pic}, {msg[0].lower() + msg[1:] if msg else ''}"
