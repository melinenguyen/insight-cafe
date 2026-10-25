"""
The scouts. Every source is turned into the same small "signal" record so the
brain can cite evidence by id and the office can show the real thing behind a
opportunity (headline, post, video, search spike, date).

The trial office reads the free, keyless sources: news (RSS feeds and Bing News), Google Trends, the
occasion calendar, competitors in the news, Pinterest and the shop's catalogue. Instagram, TikTok, YouTube,
Reddit, the competitor ad spy and customer reviews are part of the full Insight Café.

A source that fails, or has no credentials, reports why in `status` and returns
nothing — one dead feed must never stop the agency from opening its doors.
"""

from __future__ import annotations

import email.utils
import hashlib
import html
import json
import logging
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

import requests

from . import config

log = logging.getLogger("agency.sources")
# headers must be plain ASCII: a brand name like "Sương Sớm" would break every request
UA = {"User-Agent": "Mozilla/5.0 (" + re.sub(r"[^ -~]", "", config.BRAND["name"]).strip() + " brand agency)"}
NOW = lambda: datetime.now(timezone.utc)  # noqa: E731


def _sid(prefix: str, key: str) -> str:
    return f"{prefix}-{hashlib.sha1(key.encode()).hexdigest()[:8]}"


def _age_h(ts: datetime | None) -> float | None:
    return round((NOW() - ts).total_seconds() / 3600, 1) if ts else None


def _parse_ts(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    s = str(value).replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", s):
        s = s[:-2] + ":" + s[-2:]
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def signal(prefix: str, key: str, *, source: str, platform: str, kind: str, title: str,
           text: str = "", url: str = "", author: str = "", ts: datetime | None = None,
           metrics: dict | None = None, thumb: str = "", max_text: int = 320) -> dict:
    # voice-of-customer and ad signals keep more text: quotes are checked word for word against it
    return {
        "id": _sid(prefix, key), "source": source, "platform": platform, "kind": kind,
        "title": (title or "").strip()[:220], "text": re.sub(r"\s+", " ", text or "").strip()[:max_text],
        "url": url, "author": author or "", "ts": ts.isoformat() if ts else "",
        "age_h": _age_h(ts), "metrics": {k: v for k, v in (metrics or {}).items() if v not in (None, "")},
        "thumb": thumb or "",
    }


def _fresh(sig: dict, hours: float = config.WINDOW_HOURS) -> bool:
    return sig["age_h"] is None or sig["age_h"] <= hours


# ---------------------------------------------------------------------------
# News and brand moves — the old trend agent's RSS collectors, widened to 48h.
# ---------------------------------------------------------------------------
HOLLYWOOD = {"The Hollywood Reporter", "Variety", "Deadline", "Entertainment Weekly", "People Magazine", "E! News",
             "TMZ", "Page Six", "Just Jared", "Us Weekly", "Daily Mail Showbiz"}


def _entry_image(e) -> str:
    """The article's picture, from whichever field this feed uses."""
    for key in ("media_content", "media_thumbnail"):
        for m in e.get(key) or []:
            if m.get("url"):
                return m["url"]
    for enc in e.get("enclosures") or []:
        if str(enc.get("type", "")).startswith("image") and enc.get("href"):
            return enc["href"]
    html_ = " ".join([e.get("summary", "")] + [c.get("value", "") for c in e.get("content") or []])
    m = re.search(r'<img[^>]+src="([^"]+)"', html_)
    return m.group(1) if m else ""


def _feed_jobs() -> list[tuple[str, str, str]]:
    from . import feeds
    f = config.NEWS_FEEDS
    if isinstance(f, str) and f.startswith("default:"):
        pack = feeds.PACKS.get(f.split(":", 1)[1], {})
        return [(o, u, kind) for kind, d in pack.items() for o, u in d.items()]
    return [(o, u, "news") for o, u in (f or {}).items()]


def news() -> list[dict]:
    """News and brand moves: the profile's RSS feeds (or a feed pack) plus Bing News searches in the
    market's language, each with its picture."""
    import feedparser
    from . import feeds

    cutoff = NOW() - timedelta(hours=config.WINDOW_HOURS)
    flag = lambda words, text: any(w in text.lower() for w in words)  # noqa: E731

    def one(item):
        outlet, url, kind = item
        out = []
        try:
            feed = feedparser.parse(url, agent=UA["User-Agent"])
        except Exception as e:  # noqa: BLE001
            log.info("feed %s failed: %s", outlet, e)
            return out
        for e in feed.entries[:25]:
            p = e.get("published_parsed") or e.get("updated_parsed")
            ts = datetime(*p[:6], tzinfo=timezone.utc) if p else None
            if not ts or ts < cutoff:
                continue
            title, summary = e.get("title", ""), re.sub(r"<[^>]+>", "", e.get("summary", e.get("description", ""))).strip()
            flags = [f for f, on in (("viral", flag(feeds.VIRAL, title + " " + summary)),
                                     ("launch", flag(feeds.LAUNCH, title + " " + summary)),
                                     ("celebrity", outlet in feeds.HOLLYWOOD)) if on]
            out.append(signal("nw" if kind == "news" else "bi", e.get("link", "") or title, source=outlet,
                              platform="News", kind=kind, title=title, text=summary, url=e.get("link", ""), ts=ts,
                              metrics={"flags": ",".join(flags)} if flags else None, thumb=_entry_image(e)))
        return out

    with ThreadPoolExecutor(max_workers=12) as ex:
        sigs = [sig for batch in ex.map(one, _feed_jobs()) for sig in batch]
    for q in config.NEWS_QUERIES:  # any market, no feed list needed
        try:
            for it in _bing(q)[:10]:
                if it["ts"] and _age_h(it["ts"]) <= config.WINDOW_HOURS:
                    sigs.append(signal("nw", it["url"], source=it["source"] or "News", platform="News", kind="news",
                                       title=it["title"], text=it["text"], url=it["url"], ts=it["ts"], thumb=it["thumb"],
                                       metrics={"flags": "launch"} if flag(feeds.LAUNCH, it["title"]) else None))
        except requests.RequestException as e:
            log.info("bing %r: %s", q, e)
    # the same story often appears in two feeds: keep one, prefer the one with a picture
    best: dict[str, dict] = {}
    for sig in sigs:
        k = sig["url"] or sig["title"]
        if k not in best or (sig["thumb"] and not best[k]["thumb"]):
            best[k] = sig
    return list(best.values())


# ---------------------------------------------------------------------------
# Google Trends — US daily trending searches (public RSS, no key).
# ---------------------------------------------------------------------------
def google_trends() -> list[dict]:
    xml = requests.get(f"https://trends.google.com/trending/rss?geo={config.TRENDS_GEO}", headers=UA, timeout=30).text
    out = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
        def tag(name: str) -> str:
            m = re.search(rf"<{name}>(.*?)</{name}>", item, re.S)
            return (m.group(1).strip() if m else "").replace("&amp;", "&").replace("&apos;", "'")
        title = tag("title")
        news_titles = re.findall(r"<ht:news_item_title>(.*?)</ht:news_item_title>", item, re.S)
        news_urls = re.findall(r"<ht:news_item_url>(.*?)</ht:news_item_url>", item, re.S)
        out.append(signal("gt", title + tag("pubDate")[:16], source=f"Google Trends ({config.TRENDS_GEO})", platform="Search",
                          kind="search", title=f"Search spike: {title}",
                          text=" | ".join(t.replace("&apos;", "'") for t in news_titles[:2]),
                          url=news_urls[0] if news_urls else f"https://trends.google.com/trends/explore?geo={config.TRENDS_GEO}&q={urllib.parse.quote(title)}",
                          ts=_parse_ts(_rfc822(tag("pubDate"))), metrics={"searches": tag("ht:approx_traffic")},
                          thumb=tag("ht:picture")))
    return out


def _rfc822(s: str) -> str | None:
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(s).isoformat()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# The shop — live catalogue, prices and stock (Shopify public products.json).
# ---------------------------------------------------------------------------
def shop() -> list[dict]:
    # Shopify throttles python-requests ("429 local_rate_limited") by client fingerprint even when a
    # plain urllib/curl request from the same machine is served fine — so this scout uses urllib.
    import urllib.error
    import urllib.request
    if not config.SHOP_DOMAIN:
        return [{"key": re.sub(r"[^a-z0-9]+", "-", p["name"].lower()).strip("-")[:60], "title": p["name"],
                 "url": p.get("url", ""), "price": float(p.get("price") or 0), "compare_at": None, "in_stock": True,
                 "type": "", "images": [p["image"]] if p.get("image") else []} for p in config.PRODUCTS]
    req = urllib.request.Request(f"https://{config.SHOP_DOMAIN}/products.json?limit=250",
                                 headers={"User-Agent": "curl/8.7.1", "Accept": "*/*"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                prods = json.loads(r.read())["products"]
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))
    out = []
    for p in prods:
        v = p["variants"]
        prices = sorted({float(x["price"]) for x in v})
        out.append({
            "key": p["handle"][:60], "title": p["title"].strip(), "url": f"https://{config.SHOP_DOMAIN}/products/{p['handle']}",
            "price": prices[0], "compare_at": max([float(x.get("compare_at_price") or 0) for x in v] or [0]) or None,
            "in_stock": any(x["available"] for x in v), "type": p.get("product_type", ""),
            "images": [i["src"] for i in p.get("images", [])[:4]],
        })
    return out


# ---------------------------------------------------------------------------
# Pinterest — real pins for a search phrase (the web app's own JSON resource; no login).
# Called per play between the strategy desk and the studio, not in the sweep.
# ---------------------------------------------------------------------------
def pinterest(query: str, n: int = config.PINS_PER_QUERY) -> list[dict]:
    data = {"options": {"query": query, "scope": "pins", "page_size": n}, "context": {}}
    r = requests.get("https://www.pinterest.com/resource/BaseSearchResource/get/",
                     params={"source_url": f"/search/pins/?q={query}", "data": json.dumps(data)},
                     headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                                            "Chrome/130 Safari/537.36", "Accept": "application/json",
                              "X-Requested-With": "XMLHttpRequest", "X-Pinterest-PWS-Handler": "www/search/[scope].js"},
                     timeout=30)
    out = []
    for p in (r.json().get("resource_response") or {}).get("data", {}).get("results", [])[:n]:
        if p.get("type") != "pin" or not p.get("id"):
            continue
        img = (p.get("images") or {}).get("474x") or (p.get("images") or {}).get("236x") or {}
        title = (p.get("grid_title") or p.get("title") or p.get("description") or "").strip()
        out.append(signal("pn", p["id"], source=f"Pinterest · “{query}”", platform="Pinterest", kind="pin",
                          title=title[:120] or "Pinterest pin", text=(p.get("description") or "")[:200],
                          url=f"https://www.pinterest.com/pin/{p['id']}/", author=p.get("domain") or "",
                          ts=_parse_ts(p.get("created_at") and _rfc822(p["created_at"])),
                          metrics={"source_site": p.get("domain") or ""}, thumb=img.get("url", "")))
    return out


# ---------------------------------------------------------------------------
# The occasion calendar — so plays can anchor to a real date when social is quiet.
# ---------------------------------------------------------------------------
def calendar() -> list[dict]:
    from datetime import date, timedelta
    from zoneinfo import ZoneInfo

    from . import calendar_world
    today = NOW().astimezone(ZoneInfo(config.OFFICE_TZ)).date()
    out = []
    for e in calendar_world.occasions(today, today + timedelta(days=45)):
        days = (date.fromisoformat(e["date"]) - today).days
        if days < 0 or e["kind"] == "civic" and not e["decor"]:
            continue
        out.append(signal("cal", e["date"] + e["name"], source=f"{config.MARKET_NAME} calendar", platform="Calendar", kind="occasion",
                          title=f"{e['name']} — {e['date']} (in {days} days)",
                          text=" ".join(x for x in (e.get("brand_note", ""), e["note"]) if x), ts=None,
                          metrics={"days_away": days, "kind": e["kind"]}))
    return out


NOTES: dict[str, str] = {}  # a scout's remark for the office even when it succeeded

_tags = lambda h: html.unescape(re.sub(r"<[^>]+>", " ", h or "")).strip()  # noqa: E731
BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/130.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}

# ---------------------------------------------------------------------------
# The occasion pulse (Espresso) — what people think, feel and do around the next big occasions: Bing News
# (direct links, a picture for most stories) for the nearest few occasions on the US calendar.
# ---------------------------------------------------------------------------
def _bing(q: str) -> list[dict]:
    x = requests.get("https://www.bing.com/news/search", headers=BROWSER, timeout=30,
                     params={"q": q, "format": "rss", "mkt": config.BING_MKT, "setlang": config.BING_MKT,
                             "cc": config.COUNTRY}).text
    items = []
    for it in x.split("<item>")[1:]:
        g = lambda tag: html.unescape((re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S) or [None, ""])[1]).strip()  # noqa: E731
        link = g("link")
        real = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("url", [link])[0]
        items.append({"title": g("title"), "text": _tags(g("description")), "url": real, "source": g("News:Source"),
                      "ts": _parse_ts(email.utils.parsedate_to_datetime(g("pubDate")).isoformat()) if g("pubDate") else None,
                      "thumb": g("News:Image")})
    return items


def upcoming_occasions(today: date | None = None) -> list[dict]:
    from . import calendar_world
    today = today or datetime.now(ZoneInfo(config.OFFICE_TZ)).date()
    soon = [e for e in calendar_world.occasions(today, today + timedelta(days=config.OCCASION_DAYS))
            if e["date"] >= today.isoformat() and e["kind"] not in ("month", "civic") and e["weight"] >= 2]
    # the ones that matter most to the brand (weight, plus its own note), then in date order; the nearest always leads
    ranked = sorted(soon, key=lambda e: (-(e["weight"] + 2 * bool(e.get("brand_note"))), e["date"]))[:config.OCCASION_PULSE]
    if soon and soon[0] not in ranked:
        ranked = [soon[0]] + ranked[:-1]
    return sorted(ranked, key=lambda e: e["date"])


def occasions() -> list[dict]:
    out, year = [], NOW().year
    for e in upcoming_occasions():
        name = re.sub(r" \(.*\)$", "", e["name"])
        for q in (f"{name} {year}", f"{name} survey", f"{name} gift ideas"):
            try:
                found = _bing(q)
            except requests.RequestException as ex:
                log.info("bing %r: %s", q, ex)
                continue
            for it in found[:6]:
                age = _age_h(it["ts"]) if it["ts"] else None
                # current coverage first; a survey may be older if it is the latest one (the desk says its year)
                if age is not None and age > (24 * 420 if "survey" in q else 24 * 60):
                    continue
                out.append(signal("oc", it["url"], source=it["source"] or "News", platform="News", kind="occasion news",
                                  title=it["title"], text=it["text"], url=it["url"], ts=it["ts"], thumb=it["thumb"],
                                  metrics={"occasion": name, "date": e["date"]}))
            time.sleep(1)
    NOTES["occasions"] = ", ".join(re.sub(r" \(.*\)$", "", e["name"]) for e in upcoming_occasions())
    return _dedupe(out)


# ---------------------------------------------------------------------------
# Competitors in the news (Chai) — a Bing News search per watched brand, so the brand watch works with no keys.
# ---------------------------------------------------------------------------
def rivals() -> list[dict]:
    out = []
    for name in config.COMPETITORS[:8]:
        try:
            found = _bing(f'"{name}"')
        except requests.RequestException as e:
            log.info("bing %r: %s", name, e)
            continue
        for it in found[:6]:
            if it["ts"] and _age_h(it["ts"]) <= 24 * 7:  # a quiet brand's latest move may be a few days old
                out.append(signal("bi", it["url"], source=it["source"] or "News", platform="News", kind="brand move",
                                  title=it["title"], text=it["text"], url=it["url"], ts=it["ts"], thumb=it["thumb"],
                                  author=name, metrics={"brand": name}))
        time.sleep(1)
    return _dedupe(out)


def _dedupe(sigs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for s in sigs:
        if s["id"] not in seen:
            seen.add(s["id"])
            out.append(s)
    return out


SCOUTS: dict[str, Callable[[], list]] = {
    "news": news, "google_trends": google_trends, "calendar": calendar, "shop": shop, "rivals": rivals,
    "occasions": occasions,
}


def sweep(only: list[str] | None = None, skip: list[str] | tuple = ()) -> dict[str, Any]:
    """Run every scout in parallel. Returns signals, the catalogue and a status per scout."""
    names = [n for n in (only or list(SCOUTS)) if n not in skip]
    status: dict[str, dict] = {}
    results: dict[str, list] = {}

    def run(name: str):
        t0 = time.time()
        try:
            data = SCOUTS[name]()
            status[name] = {"ok": True, "count": len(data), "seconds": round(time.time() - t0, 1), "note": NOTES.get(name, "")}
            return name, data
        except Exception as e:  # a dead scout must never close the office
            log.warning("scout %s failed: %s", name, e)
            status[name] = {"ok": False, "count": 0, "seconds": round(time.time() - t0, 1), "note": str(e)[:200]}
            return name, []

    with ThreadPoolExecutor(max_workers=len(names)) as ex:
        for name, data in ex.map(run, names):
            results[name] = data

    catalogue = results.pop("shop", [])
    signals = _dedupe([s for name in results for s in results[name]])
    return {"swept_at": NOW().isoformat(), "signals": signals, "catalogue": catalogue, "status": status}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    res = sweep(sys.argv[1:] or None)
    print(json.dumps(res["status"], indent=1))
    print(len(res["signals"]), "signals,", len(res["catalogue"]), "products")
