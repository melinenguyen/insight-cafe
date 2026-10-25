"""
The US calendar the office lives by — one list the brain plans from and the office hangs on its wall.

Federal holidays, cultural and faith observances, retail moments and heritage months, plus the brand's
own dated notes from config.OCCASIONS. Fixed and nth-weekday dates are computed for any year, Easter
by the Gregorian computus. Dates that follow the lunar, Hebrew, Islamic or Hindu calendars come from
MOVABLE — verified through 2029; add the following years before then or those occasions vanish.
Eid dates are the expected ones and can shift a day with the moon sighting.

Each entry also says how the office dresses for it: `decor` names the props office.html draws,
`colors` light the Empire State Building and the bunting, `lead` is how many days early the decor
goes up, and `weight` decides which occasion wins the garland when several overlap.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from . import config

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)

# first day (MM-DD) of occasions that don't follow the Gregorian calendar; Jewish ones begin at sundown
MOVABLE = {
    "lny": {2026: "02-17", 2027: "02-06", 2028: "01-26", 2029: "02-13"},
    "ramadan": {2026: "02-18", 2027: "02-08", 2028: "01-28", 2029: "01-16"},
    "eid_fitr": {2026: "03-20", 2027: "03-10", 2028: "02-27", 2029: "02-15"},
    "passover": {2026: "04-01", 2027: "04-21", 2028: "04-10", 2029: "03-30"},
    "eid_adha": {2026: "05-27", 2027: "05-16", 2028: "05-05", 2029: "04-24"},
    "rosh": {2026: "09-11", 2027: "10-01", 2028: "09-20", 2029: "09-09"},
    "yom_kippur": {2026: "09-20", 2027: "10-10", 2028: "09-29", 2029: "09-18"},
    "midautumn": {2026: "09-25", 2027: "09-15", 2028: "10-03", 2029: "09-22"},
    "diwali": {2026: "11-08", 2027: "10-29", 2028: "10-17", 2029: "11-05"},
    "hanukkah": {2026: "12-04", 2027: "12-24", 2028: "12-12", 2029: "12-01"},
}

RWB = ["#B22234", "#FFFFFF", "#3C3B6E"]
RAINBOW = ["#E0262F", "#F28C28", "#F5D33A", "#2F9E5B", "#2F5BD6", "#6B4FB8"]
NO_MAIL = "Federal holiday — banks and USPS closed, no mail delivery."


def nth_weekday(y: int, m: int, weekday: int, n: int) -> date:
    """n-th weekday of a month; n = -1 is the last one."""
    if n > 0:
        d = date(y, m, 1)
        return d + timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
    d = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def easter(y: int) -> date:
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741 — the algorithm's own name
    m = (a + 11 * h + 19 * l) // 433
    month = (h + l - 7 * m + 90) // 25
    return date(y, month, (h + l - 7 * m + 33 * month + 19) % 32)


def _e(d: date, name: str, kind: str, *, days: int = 1, decor: str = "", colors=(), lead: int = 0,
       weight: int = 2, note: str = "", greeting: str = "") -> dict:
    return {"date": d.isoformat(), "end": (d + timedelta(days=days - 1)).isoformat(), "name": name, "kind": kind,
            "decor": decor, "colors": list(colors), "lead": lead, "weight": weight, "note": note,
            "greeting": greeting}


def _month(y: int, m: int, name: str, decor: str, colors, weight: int = 1) -> dict:
    last = ((date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - date(y, m, 1)).days
    return _e(date(y, m, 1), name, "month", days=last, decor=decor, colors=colors, weight=weight)


def year(y: int) -> list[dict]:
    mv = lambda k: date.fromisoformat(f"{y}-{MOVABLE[k][y]}") if y in MOVABLE[k] else None  # noqa: E731
    tg = nth_weekday(y, 11, THU, 4)
    ea = easter(y)
    out = [
        # --- heritage & awareness months ---
        _month(y, 2, "Black History Month", "banner", ["#C8102E", "#F2B530", "#00843D"]),
        _month(y, 3, "Women's History Month", "banner", ["#6B4FB8", "#FFFFFF", "#F2B530"]),
        _month(y, 5, "AAPI Heritage Month", "banner", ["#E0262F", "#F2B530"]),
        _month(y, 6, "Pride Month", "pride", RAINBOW, weight=2),
        _e(date(y, 9, 15), "Hispanic Heritage Month", "month", days=31, decor="papelpicado",
           colors=["#E0262F", "#F2B530", "#2F9E5B", "#2F5BD6", "#F26D9E"], weight=1),
        _month(y, 10, "Breast Cancer Awareness Month", "pinkribbon", ["#F26D9E", "#FFFFFF"]),
        _month(y, 11, "Native American Heritage Month", "banner", ["#B4472E", "#F2B530", "#2F5BD6"]),
        # --- winter ---
        _e(date(y, 1, 1), "New Year's Day", "federal", decor="newyear", colors=["#D9B44A", "#FFFFFF", "#C0C0C0"],
           weight=3, note=NO_MAIL, greeting="Happy New Year"),
        _e(nth_weekday(y, 1, MON, 3), "Martin Luther King Jr. Day", "federal", decor="banner",
           colors=["#3C3B6E", "#FFFFFF", "#D9B44A"], note=NO_MAIL),
        _e(nth_weekday(y, 2, SUN, 2), "Super Bowl Sunday", "culture", decor="superbowl",
           colors=["#7A4A2A", "#FFFFFF"], lead=2),
        _e(date(y, 2, 14), "Valentine's Day", "culture", decor="valentine", colors=["#E0262F", "#F26D9E", "#FFFFFF"],
           lead=7, weight=3, greeting="Happy Valentine's Day"),
        _e(nth_weekday(y, 2, MON, 3), "Presidents' Day", "federal", decor="flags", colors=RWB, note=NO_MAIL),
        _e(ea - timedelta(days=47), "Mardi Gras", "culture", decor="mardigras",
           colors=["#6B2C91", "#2F9E5B", "#F2B530"], lead=1),
        # --- spring ---
        _e(date(y, 3, 8), "International Women's Day", "culture", decor="flowers",
           colors=["#6B4FB8", "#F5D33A", "#FFFFFF"], lead=1),
        _e(nth_weekday(y, 3, SUN, 2), "Daylight saving time begins", "civic", weight=0,
           note="Clocks go forward an hour in the US: check meeting and report times with teams abroad."),
        _e(date(y, 3, 17), "St. Patrick's Day", "culture", decor="stpatricks", colors=["#169B62", "#7BC96F", "#FFFFFF"],
           lead=3, weight=3, greeting="Happy St. Patrick's Day"),
        _e(ea, "Easter", "faith", decor="easter", colors=["#F6C6D8", "#FFF1A8", "#C9F0D6", "#C9D8F5"], lead=6,
           weight=3, greeting="Happy Easter"),
        _e(date(y, 4, 22), "Earth Day", "culture", decor="earth", colors=["#2F9E5B", "#2F5BD6"], lead=1),
        _e(nth_weekday(y, 5, SUN, 2), "Mother's Day", "culture", decor="flowers", colors=["#F26D9E", "#FFD1DC", "#FFFFFF"],
           lead=7, weight=3, greeting="Happy Mother's Day"),
        _e(nth_weekday(y, 5, MON, -1), "Memorial Day", "federal", decor="flags", colors=RWB, lead=2, note=NO_MAIL),
        # --- summer ---
        _e(nth_weekday(y, 6, SUN, -1), "NYC Pride March", "culture", decor="pride", colors=RAINBOW, weight=3,
           greeting="Happy Pride"),
        _e(date(y, 6, 19), "Juneteenth", "federal", decor="juneteenth", colors=["#C8102E", "#F2B530", "#00843D"],
           lead=1, weight=3, note=NO_MAIL),
        _e(nth_weekday(y, 6, SUN, 3), "Father's Day", "culture", decor="banner", colors=["#3C3B6E", "#C4882B"],
           lead=4, greeting="Happy Father's Day"),
        _e(date(y, 7, 4), "Independence Day", "federal", decor="july4", colors=RWB, lead=4, weight=3, note=NO_MAIL,
           greeting="Happy Fourth of July"),
        _e(date(y, 8, 10), "Back-to-school season", "retail", days=26, decor="school", colors=["#F2B530", "#E0262F"],
           weight=1),
        _e(nth_weekday(y, 9, MON, 1), "Labor Day", "federal", decor="flags", colors=RWB, lead=2, note=NO_MAIL),
        # --- autumn ---
        _e(nth_weekday(y, 10, MON, 2), "Indigenous Peoples' Day / Columbus Day", "federal", decor="banner",
           colors=["#B4472E", "#F2B530", "#2F5BD6"], note=NO_MAIL),
        _e(date(y, 10, 31), "Halloween", "culture", decor="halloween", colors=["#F28C28", "#F28C28", "#7A3FB8"],
           lead=16, weight=3, greeting="Happy Halloween"),
        _e(nth_weekday(y, 11, SUN, 1), "Daylight saving time ends", "civic", weight=0,
           note="Clocks go back an hour in the US: check meeting and report times with teams abroad."),
        _e(nth_weekday(y, 11, MON, 1) + timedelta(days=1), "Election Day" + (" (midterms)" if y % 4 == 2 else ""),
           "civic", decor="vote", colors=RWB),
        _e(date(y, 11, 11), "Veterans Day", "federal", decor="flags", colors=RWB, note=NO_MAIL),
        _e(tg - timedelta(days=5), "Friendsgiving", "culture", decor="thanksgiving",
           colors=["#C9662F", "#D99A2B", "#A8452A"], weight=2),
        _e(tg, "Thanksgiving", "federal", decor="thanksgiving", colors=["#C9662F", "#D99A2B", "#A8452A"], lead=7,
           weight=3, note=NO_MAIL, greeting="Happy Thanksgiving"),
        _e(tg + timedelta(days=1), "Black Friday", "retail", decor="shopping", colors=["#241E2A", "#F2B530"]),
        _e(tg + timedelta(days=2), "Small Business Saturday", "retail", decor="shopping", colors=["#2F5BD6", "#FFFFFF"]),
        _e(tg + timedelta(days=4), "Cyber Monday", "retail", decor="shopping", colors=["#2F5BD6", "#6B4FB8"]),
        _e(tg + timedelta(days=5), "Giving Tuesday", "culture", decor="giving", colors=["#E0262F", "#FFFFFF"]),
        _e(date(y, 12, 25), "Christmas Day", "federal", days=2, decor="christmas", colors=["#E0262F", "#2E8B57", "#FFFFFF"],
           lead=24, weight=3, note=NO_MAIL, greeting="Merry Christmas"),
        _e(date(y, 12, 26), "Kwanzaa", "culture", days=7, decor="kwanzaa", colors=["#C8102E", "#1B1620", "#00843D"],
           weight=3, greeting="Happy Kwanzaa"),
        _e(date(y, 12, 31), "New Year's Eve", "culture", decor="newyear", colors=["#D9B44A", "#FFFFFF", "#C0C0C0"],
           lead=4, weight=3, greeting="Happy New Year"),
    ]
    movable = [
        ("lny", "Lunar New Year", "culture", 3, "lny", ["#E0262F", "#F2B530"], 7, 3,
         "Happy Lunar New Year · Chúc Mừng Năm Mới"),
        ("ramadan", "Ramadan begins", "faith", 1, "ramadan", ["#2E6B5A", "#F2B530"], 0, 2, "Ramadan Mubarak"),
        ("eid_fitr", "Eid al-Fitr", "faith", 1, "eid", ["#2E8B57", "#F2B530"], 1, 3, "Eid Mubarak"),
        ("passover", "Passover (begins at sundown)", "faith", 8, "passover", ["#2F5BD6", "#FFFFFF"], 0, 3,
         "Chag Pesach Sameach"),
        ("eid_adha", "Eid al-Adha", "faith", 1, "eid", ["#2E8B57", "#F2B530"], 0, 2, "Eid Mubarak"),
        ("rosh", "Rosh Hashanah (begins at sundown)", "faith", 3, "roshhashanah", ["#D9B44A", "#E0262F"], 0, 3,
         "Shanah Tovah"),
        ("yom_kippur", "Yom Kippur (begins at sundown)", "faith", 2, "", ["#FFFFFF"], 0, 2, ""),
        ("midautumn", "Mid-Autumn Festival", "culture", 1, "midautumn", ["#F2B530", "#E0262F"], 3, 2,
         "Happy Mid-Autumn · Tết Trung Thu"),
        ("diwali", "Diwali", "faith", 1, "diwali", ["#F28C28", "#F2B530", "#E0262F"], 2, 3, "Happy Diwali"),
        ("hanukkah", "Hanukkah (first candle at sundown)", "faith", 9, "hanukkah", ["#2F5BD6", "#FFFFFF"], 0, 3,
         "Happy Hanukkah"),
    ]
    for key, name, kind, days, decor, colors, lead, weight, greeting in movable:
        d = mv(key)
        if d:
            out.append(_e(d, name, kind, days=days, decor=decor, colors=colors, lead=lead, weight=weight,
                          greeting=greeting))
    return out


def _words(name: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", name.lower()) if len(w) >= 4}


def occasions(start: date, end: date) -> list[dict]:
    """Every occasion touching [start, end], with the brand's own notes folded into the matching entry."""
    lo, hi = start.isoformat(), end.isoformat()
    items = [e for y in range(start.year - 1, end.year + 1) for e in year(y) if e["end"] >= lo and e["date"] <= hi]
    for d, name, note in config.OCCASIONS:
        if not lo <= d <= hi:
            continue
        twin = next((e for e in items if e["date"] == d and _words(e["name"]) & _words(name)), None)
        if twin:
            twin["brand_note"] = note
        else:
            items.append(_e(date.fromisoformat(d), name, "brand", weight=1) | {"brand_note": note})
    return sorted(items, key=lambda e: (e["date"], -e["weight"]))
