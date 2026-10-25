#!/usr/bin/env python3
"""
Check a brand profile before it becomes a trial office.

    python3 validate.py profile.json

Errors stop the scaffold (the office would not run without them); warnings are things the office runs
without, but thinner. Exit code 1 when there are errors.
"""

from __future__ import annotations

import json
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

REQUIRED = [
    ("agency.name", "the agency's name"), ("agency.office_city", "the office's city"), ("agency.office_tz", "the office's time zone"),
    ("brand.name", "brand name"), ("brand.short", "brand short name"), ("brand.category", "brand category"),
    ("brand.one_liner", "one-line description"), ("brand.voice.tone", "voice / tone"), ("brand.look", "what on-brand pictures look like"),
    ("market.country", "market country"), ("market.language", "market language"), ("market.currency", "currency"),
    ("offers.rules", "offer rules (write 'No discounts' if there are none)"), ("team.lead.name", "the lead's name"),
    ("schedule.team_tz", "the team's time zone"),
]


def get(p: dict, path: str):
    cur = p
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def check(p: dict) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    for path, label in REQUIRED:
        if get(p, path) in (None, "", [], {}):
            errors.append(f"missing {label} ({path})")
    for path in ("agency.office_tz", "schedule.team_tz"):
        tz = get(p, path)
        if tz:
            try:
                ZoneInfo(tz)
            except (ZoneInfoNotFoundError, ValueError):
                errors.append(f"{path} is not a time zone: {tz!r} (use names like Asia/Ho_Chi_Minh)")
    d = get(p, "delivery") or {}
    for path in ("delivery.brain_repo", "delivery.site_repo"):
        v = get(p, path)
        if v and not re.fullmatch(r"[\w.-]+/[\w.-]+", v):
            errors.append(f"{path} must look like owner/repo, got {v!r}")
    if bool(d.get("brain_repo")) != bool(d.get("site_repo")):
        errors.append("to open 24/7 on GitHub, give both repos: delivery.brain_repo (private) and delivery.site_repo (public)")
    for t in get(p, "schedule.reports") or []:
        if not re.fullmatch(r"\d{1,2}:\d{2}", t):
            errors.append(f"report time {t!r} must be HH:MM")
    members = get(p, "team.members") or []
    if not members:
        errors.append("add at least one team member (team.members) — plays need someone to go to")
    for m in members:
        if not m.get("name") or not m.get("lanes"):
            errors.append(f"team member {m.get('name') or '?'} needs a name and at least one lane")
    if not (get(p, "competitors.peers") or get(p, "competitors.performance") or get(p, "competitors.also_watch")):
        warns.append("no competitors — Chai's brand watch will have nothing to read")
    if not get(p, "audience.personas"):
        warns.append("no personas — opportunities can't be tagged to an audience")
    if not get(p, "products") and not get(p, "catalog.shopify_domain"):
        warns.append("no products and no Shopify domain — plays can't name a product")
    if not get(p, "sources.news_feeds") and not get(p, "sources.news_queries"):
        warns.append("no news feeds or news queries — the culture radar reads only Google Trends and the calendar")
    if not (p.get("standing_brief") or "").strip():
        warns.append("no standing brief — the dashboard can draft one from your answers")
    country = (get(p, "market.country") or "").upper()
    if country and country != "US":
        try:
            import holidays
            holidays.country_holidays(country)
        except ImportError:
            warns.append("pip install holidays to check the calendar for this country")
        except (NotImplementedError, KeyError):
            warns.append(f"no public-holiday list for {country} — the calendar will carry only global moments and your dates")
    return errors, warns


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    p = json.load(open(sys.argv[1], encoding="utf-8"))
    errors, warns = check(p)
    for e in errors:
        print("✕", e)
    for w in warns:
        print("!", w)
    print(f"\n{len(errors)} errors, {len(warns)} warnings —", "ready to scaffold" if not errors else "fix the errors first")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
