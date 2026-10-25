"""
Configuration, read from the brand profile (agency/profile.json, or the file named by $AGENCY_PROFILE).

Every brand-specific value — the brand, its market, competitors, audience, products, offers, team,
sources — lives in the profile, which the setup dashboard writes. This module turns it into
the names the rest of the code uses. Secrets never live here — they come from env.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RENDERS = ROOT / "renders"
SITE = Path(os.getenv("AGENCY_SITE_DIR", ROOT.parent / "site"))
PROFILE_PATH = Path(os.getenv("AGENCY_PROFILE", ROOT / "profile.json"))
P: dict = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def _get(path: str, default=None):
    cur = P
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return default if cur in (None, "", [], {}) else cur


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


# ---------------------------------------------------------------------------
# The brand and its market
# ---------------------------------------------------------------------------
BRAND = {
    "name": _get("brand.name"), "short": _get("brand.short") or _get("brand.name"),
    "website": _get("brand.website", ""), "category": _get("brand.category", ""),
    "one_liner": _get("brand.one_liner", ""), "benefit": _get("brand.benefit", ""),
    "signature": _get("brand.signature", ""), "price_position": _get("brand.price_position", ""),
    "tone": _get("brand.voice.tone", "Clear, warm and specific."),
    "banned_words": _get("brand.voice.banned_words", []),
    "no_exclamation_marks": bool(_get("brand.voice.no_exclamation_marks", False)),
    "look": _get("brand.look", ""), "look_avoid": _get("brand.look_avoid", ""),
    "claims_never": _get("claims_never", []), "offer_rules": _get("offers.rules", ""),
    "offer_never": _get("offers.never", []), "season_focus": _get("business.season_focus", ""),
    "model": _get("business.model", ""), "channels": _get("business.channels", []),
    "goals": _get("business.goals", ""),
}
COUNTRY = _get("market.country", "US").upper()
LANGUAGE = _get("market.language", "en-US")
CURRENCY = _get("market.currency", "USD")
BING_MKT = _get("market.bing_mkt") or LANGUAGE
TRENDS_GEO = _get("market.trends_geo") or COUNTRY
YT_REGION = _get("market.youtube_region") or COUNTRY
YT_LANG = LANGUAGE.split("-")[0]
CALENDAR = (_get("market.calendar") or COUNTRY).upper()
GLOBAL_MOMENTS = _get("market.global_moments", [])
MARKET_NAME = {"US": "the US", "GB": "the UK", "VN": "Vietnam", "SG": "Singapore", "AU": "Australia",
               "ID": "Indonesia", "TH": "Thailand", "PH": "the Philippines", "MY": "Malaysia", "JP": "Japan",
               "KR": "Korea", "FR": "France", "DE": "Germany", "CA": "Canada"}.get(COUNTRY, COUNTRY)
REPORT_LANGUAGE = _get("agency.report_language", "English")
PERSONAS = [p["name"] for p in _get("audience.personas", [])]
PERSONA_LINES = [f"{p['name']}: {p.get('description', '')}" for p in _get("audience.personas", [])]
PRODUCTS = _get("products", [])
SHOP_DOMAIN = _get("catalog.shopify_domain", "")
STANDING_BRIEF = P.get("standing_brief") or ""

# ---------------------------------------------------------------------------
# The office
# ---------------------------------------------------------------------------
AGENCY = {"name": _get("agency.name", "The Insight Café"), "tagline": _get("agency.tagline", "Your AI research agency"),
          "city": _get("agency.office_city", "New York"), "neighbourhood": _get("agency.office_neighbourhood", ""),
          "scene": _get("agency.scene", "city")}
OFFICE_TZ = _get("agency.office_tz", "America/New_York")
MODEL = "claude-opus-5-5"

# ---------------------------------------------------------------------------
# The trial. Four of the seven specialists work; the rest of the office is shown, locked.
# ---------------------------------------------------------------------------
TRIAL = True
TRIAL_PLAYS = 1             # the studio writes the top play in full; the others are listed, locked
LOCKED_ROOMS = ["inspo", "voice", "huddle", "archive", "dispatch", "rules"]
FULL_URL = "https://www.tiktok.com/@himeline"

# ---------------------------------------------------------------------------
# The humans the agency works for.
# ---------------------------------------------------------------------------
_lead = _get("team.lead", {})
OWNER = {"name": _lead.get("name", "the lead"), "role": _lead.get("role", "")}
PICS = {m["name"]: {"lanes": m.get("lanes") or ["General"], "owns": m.get("owns", "")} for m in _get("team.members", [])}
LANES = [lane for p in PICS.values() for lane in p["lanes"]]
LANE_OWNER = {lane: name for name, p in PICS.items() for lane in p["lanes"]}
TEAM = " and ".join(PICS) if len(PICS) <= 2 else ", ".join(list(PICS)[:-1]) + " and " + list(PICS)[-1]

# ---------------------------------------------------------------------------
# The AI staff, one room each. In the trial Mocha and Latte's rooms are locked and Tonic doesn't send to Slack.
# ---------------------------------------------------------------------------
DEFAULT_CREW = [
    {"id": "coca", "name": "Coca", "role": "Agency director", "room": "desk",
     "job": "The brief: what happened, what it means, what we do",
     "look": {"hair": "bun", "top": "#A8443A", "skin": "#EDB892", "acc": "clip"},
     "question": "What is the one thing the brand needs most this week?"},
    {"id": "espresso", "name": "Espresso", "role": "Culture & social radar", "room": "radar",
     "job": "What happened in culture and social — and what people think, feel and do around the next occasions",
     "look": {"hair": "short", "top": "#3B3430", "skin": "#D9A27A", "acc": "glasses", "hairColor": "#4A2E22"},
     "question": "Any culture moment, show or creator you want me to keep on the radar?"},
    {"id": "chai", "name": "Chai", "role": "Brand watch", "room": "brands",
     "job": "What other brands launched, said and did",
     "look": {"hair": "bob", "top": "#4E5D78", "skin": "#C98E6B", "acc": "glasses"},
     "question": "Any brand you want me to watch more closely, or drop?"},
    {"id": "mocha", "name": "Mocha", "role": "Creative strategist", "room": "inspo",
     "job": "Reads other brands' ads, then proposes our static and video ads for every funnel stage, and why they'll work",
     "look": {"hair": "beret", "top": "#8C6A5C", "skin": "#E8B48A", "acc": "beret"},
     "question": "Any ad you saw that we should study, or any asset you want held back?"},
    {"id": "latte", "name": "Latte", "role": "Customer voice", "room": "voice",
     "job": "What our customers and the audiences of brands we sit beside say — and the hooks, angles and plans it gives us",
     "look": {"hair": "short", "top": "#B6A188", "skin": "#F2C9A5", "acc": "earring"},
     "question": "Anything we must not say, show or push right now? Claims, stock, sensitive topics."},
    {"id": "matcha", "name": "Matcha", "role": "Strategist", "room": "wall",
     "job": "What we steal or leverage: every opportunity, scored",
     "look": {"hair": "curly", "top": "#2C332F", "skin": "#8D5A3B", "acc": "pencil"},
     "question": "Which campaigns, promotions, launches or events are live or coming up? Dates and codes, please."},
    {"id": "tonic", "name": "Tonic", "role": "Producer", "room": "war",
     "job": "The plays in flight with the team, and their tickets",
     "look": {"hair": "braid", "top": "#716A56", "skin": "#B9845F", "acc": "headset"},
     "question": "How is the team this week? Anyone away, overloaded, or waiting on something?"},
]
_crew = {c["id"]: c for c in _get("agency.crew", [])}
STAFF = [{**d, **{k: v for k, v in _crew.get(d["id"], {}).items() if v}} for d in DEFAULT_CREW]
STAFF_IDS = [s["id"] for s in STAFF]

# ---------------------------------------------------------------------------
# Schedule: open 24/7. On GitHub the workflow ticks every hour and schedule.py runs whatever report is due
# (one or two a day at schedule.reports, the team's time). On your computer, `python -m agency.run` runs one now.
# ---------------------------------------------------------------------------
TZ = _get("schedule.team_tz", "UTC")
TEAM_CITY = _get("schedule.team_city") or TZ.split("/")[-1].replace("_", " ")
_times = [t for t in _get("schedule.reports", ["07:00"]) if re.fullmatch(r"\d{1,2}:\d{2}", t)][:2]
REPORTS = {name: tuple(int(x) for x in t.split(":")) for name, t in zip(("morning", "evening"), _times)}
REPORT_SLOTS = ("report", "morning", "evening")  # "report" = one you start by hand
REPORT_RETRIES = 2
WINDOW_HOURS = 48

# Where the office lives when it runs on GitHub: a private repo for the brain, a public one for the (encrypted) page
BRAIN_REPO = _get("delivery.brain_repo", "")
SITE_REPO = _get("delivery.site_repo", "")
SITE_URL = _get("delivery.site_url") or (f"https://{SITE_REPO.split('/')[0]}.github.io/{SITE_REPO.split('/')[1]}/" if "/" in SITE_REPO else "")

# ---------------------------------------------------------------------------
# Content vocabulary — what an opportunity can be about, where it lives, how we make it
# ---------------------------------------------------------------------------
PILLARS = _get("content.pillars", ["Discovery", "Proof", "Occasion", "Brand story"])
CATEGORIES = _get("content.categories", ["Occasions", "Culture & celebrity", "Internet culture", "Our category",
                                         "Competitor move", "Our brand"])
PLATFORMS = _get("content.platforms", ["TikTok", "Instagram", "YouTube", "News", "Search", "Calendar", "Meta Ads"])
FORMATS = _get("content.formats", ["static", "carousel", "reel", "tiktok", "story", "ugc", "ad", "creator_brief",
                                   "affiliate_brief", "pr_pitch", "seeding"])
RADAR_EXTRA = _get("content.radar_sections", [])

# ---------------------------------------------------------------------------
# Watchlists
# ---------------------------------------------------------------------------
COMPETITORS = list(dict.fromkeys([c["name"] for c in _get("competitors.peers", []) + _get("competitors.performance", [])]
                                 + _get("competitors.also_watch", [])))
PINS_PER_QUERY = 8
NEWS_FEEDS = _get("sources.news_feeds", {})
NEWS_QUERIES = _get("sources.news_queries", [])

OCCASION_PULSE = 4
OCCASION_DAYS = 45
OCCASIONS = [(o["date"], o["name"], o.get("note", "")) for o in _get("calendar.occasions", [])]
