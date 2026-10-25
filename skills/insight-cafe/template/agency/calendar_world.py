"""
The calendar for any market. The US gets the full hand-built calendar (calendar_us.py: federal holidays,
retail moments, heritage months, faith dates, decor). Every other country gets its public holidays (the
`holidays` package, in English where it has them) plus the global and regional moments the profile switches
on (`market.global_moments`), plus the brand's own dates (`calendar.occasions`) folded in.

Every entry has the same shape as calendar_us: date, end, name, kind, decor, colors, lead, weight, note.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import calendar_us as us
from . import config

# moment → (how to date it in a year, name, kind, decor, colours, weight, lead days)
MOMENTS = {
    "valentines": (lambda y: date(y, 2, 14), "Valentine's Day", "culture", "valentine", ["#C8102E", "#F4B6C2"], 3, 14),
    "womens_day": (lambda y: date(y, 3, 8), "International Women's Day", "culture", "flowers", ["#7B4A63", "#F2D7E0"], 2, 7),
    "mothers_day": (lambda y: us.nth_weekday(y, 5, us.SUN, 2), "Mother's Day", "culture", "flowers", ["#E8A0B4", "#FFFFFF"], 3, 21),
    "fathers_day": (lambda y: us.nth_weekday(y, 6, us.SUN, 3), "Father's Day", "culture", "", ["#3C5A7A", "#FFFFFF"], 2, 14),
    "halloween": (lambda y: date(y, 10, 31), "Halloween", "culture", "halloween", ["#F28C28", "#1B1A20"], 2, 14),
    "singles_day": (lambda y: date(y, 11, 11), "11.11 Singles' Day sale", "retail", "shopping", ["#E4002B", "#FFFFFF"], 3, 10),
    "black_friday": (lambda y: us.nth_weekday(y, 11, us.THU, 4) + timedelta(days=1), "Black Friday", "retail", "shopping", ["#1B1A20", "#D7A536"], 3, 10),
    "cyber_monday": (lambda y: us.nth_weekday(y, 11, us.THU, 4) + timedelta(days=4), "Cyber Monday", "retail", "shopping", ["#2F5BD6", "#FFFFFF"], 2, 5),
    "double_12": (lambda y: date(y, 12, 12), "12.12 sale", "retail", "shopping", ["#E4002B", "#FFFFFF"], 2, 7),
    "christmas": (lambda y: date(y, 12, 25), "Christmas", "culture", "christmas", ["#C8102E", "#0B6623"], 3, 30),
    "new_year": (lambda y: date(y, 1, 1), "New Year's Day", "culture", "newyear", ["#D7A536", "#1B1A20"], 2, 5),
    "lunar_new_year": (lambda y: _mv("lny", y), "Lunar New Year", "culture", "lny", ["#C8102E", "#D7A536"], 3, 30),
    "mid_autumn": (lambda y: _mv("midautumn", y), "Mid-Autumn Festival", "culture", "midautumn", ["#D7A536", "#C8102E"], 2, 14),
    "diwali": (lambda y: _mv("diwali", y), "Diwali", "faith", "diwali", ["#F28C28", "#7B2D8E"], 2, 10),
    "eid": (lambda y: _mv("eid_fitr", y), "Eid al-Fitr", "faith", "eid", ["#0B6623", "#D7A536"], 2, 7),
    "ramadan": (lambda y: _mv("ramadan", y), "Ramadan begins", "faith", "eid", ["#0B6623", "#D7A536"], 2, 7),
}
# what a market gets when the profile doesn't choose
DEFAULT_MOMENTS = {
    "VN": ["valentines", "womens_day", "singles_day", "double_12", "christmas", "new_year", "lunar_new_year", "mid_autumn", "halloween"],
    "SG": ["valentines", "mothers_day", "singles_day", "double_12", "christmas", "lunar_new_year", "mid_autumn", "diwali", "eid"],
    "MY": ["valentines", "mothers_day", "singles_day", "double_12", "christmas", "lunar_new_year", "eid", "ramadan", "diwali"],
    "ID": ["valentines", "mothers_day", "singles_day", "double_12", "eid", "ramadan", "christmas"],
    "TH": ["valentines", "singles_day", "double_12", "christmas", "new_year", "lunar_new_year"],
    "PH": ["valentines", "mothers_day", "singles_day", "double_12", "christmas", "new_year"],
    "GB": ["valentines", "halloween", "black_friday", "cyber_monday", "christmas", "new_year", "diwali"],
}
# a few local dates the public-holiday list doesn't carry
LOCAL = {
    "VN": [(lambda y: date(y, 10, 20), "Vietnamese Women's Day", "culture", "flowers", ["#7B4A63", "#F2D7E0"], 3, 14),
           (lambda y: date(y, 11, 20), "Vietnamese Teachers' Day", "culture", "flowers", ["#2F5BD6", "#FFFFFF"], 2, 7)],
    "GB": [(lambda y: us.easter(y) - timedelta(days=21), "Mothering Sunday", "culture", "flowers", ["#E8A0B4", "#FFFFFF"], 3, 21)],
}
DECOR_WORDS = [("christmas", "christmas"), ("new year", "newyear"), ("lunar", "lny"), ("chinese new year", "lny"),
               ("tet", "lny"), ("mid-autumn", "midautumn"), ("diwali", "diwali"), ("deepavali", "diwali"),
               ("eid", "eid"), ("hari raya", "eid"), ("independence", "flags"), ("national day", "flags"),
               ("easter", "easter"), ("halloween", "halloween")]


def _mv(key: str, y: int) -> date | None:
    d = us.MOVABLE.get(key, {}).get(y)
    return date.fromisoformat(f"{y}-{d}") if d else None


def _public(y: int) -> list[dict]:
    import holidays
    try:
        cal = holidays.country_holidays(config.COUNTRY, years=y)
        if "en_US" in getattr(cal, "supported_languages", ()):
            cal = holidays.country_holidays(config.COUNTRY, years=y, language="en_US")
    except (NotImplementedError, KeyError):
        return []
    out = []
    for d, name in sorted(cal.items()):
        if "observed" in name.lower():
            continue
        decor = next((v for w, v in DECOR_WORDS if w in name.lower()), "")
        out.append(us._e(d, name, "federal", decor=decor, weight=2, lead=7 if decor else 0, note="Public holiday."))
    return out


def year(y: int) -> list[dict]:
    items = _public(y)
    moments = config.GLOBAL_MOMENTS or DEFAULT_MOMENTS.get(config.COUNTRY, ["valentines", "black_friday", "christmas", "new_year"])
    for key in moments:
        if key not in MOMENTS:
            continue
        when, name, kind, decor, colors, weight, lead = MOMENTS[key]
        d = when(y)
        if d and not any(e["date"] == d.isoformat() and e["decor"] == decor and decor for e in items):
            items.append(us._e(d, name, kind, decor=decor, colors=colors, weight=weight, lead=lead))
    for when, name, kind, decor, colors, weight, lead in LOCAL.get(config.COUNTRY, []):
        items.append(us._e(when(y), name, kind, decor=decor, colors=colors, weight=weight, lead=lead))
    return items


def occasions(start: date, end: date) -> list[dict]:
    """Every occasion touching [start, end], with the brand's own notes folded into the matching entry."""
    if config.CALENDAR == "US":
        return us.occasions(start, end)
    lo, hi = start.isoformat(), end.isoformat()
    items = [e for y in range(start.year - 1, end.year + 1) for e in year(y) if e["end"] >= lo and e["date"] <= hi]
    for d, name, note in config.OCCASIONS:
        if not lo <= d <= hi:
            continue
        twin = next((e for e in items if e["date"] == d and us._words(e["name"]) & us._words(name)), None)
        if twin:
            twin["brand_note"] = note
        else:
            items.append(us._e(date.fromisoformat(d), name, "brand", weight=1) | {"brand_note": note})
    return sorted(items, key=lambda e: (e["date"], -e["weight"]))
