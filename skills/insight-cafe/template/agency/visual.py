"""
A picture for every signal the office shows ("every single signal you propose must have
a visualization/proof alongside").

Scouts keep the picture their source gives. For the ones that arrive without — articles whose feed has no
image, Instagram reels, TikToks, YouTube links — this finds one: YouTube's thumbnail, Instagram's public
media redirect, TikTok's oEmbed thumbnail, or the page's og:image / twitter:image. A found picture is written
onto the signal in memory's library, so each link is looked up once (a miss is retried after 12 hours). The
build then downloads it into the image cache, which outlives Instagram's expiring CDN links.
"""

from __future__ import annotations

import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

log = logging.getLogger("agency.visual")
BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/130.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
META = [r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
        r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image']


def picture(url: str) -> str:
    """The best picture for a link, or ""."""
    if not url:
        return ""
    yt = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})", url)
    if yt:
        return f"https://i.ytimg.com/vi/{yt.group(1)}/hqdefault.jpg"
    ig = re.search(r"instagram\.com/(?:[\w.]+/)?(?:p|reel|reels|tv)/([\w-]+)", url)
    if ig:  # public posts redirect to their image without a login
        r = requests.get(f"https://www.instagram.com/p/{ig.group(1)}/media/?size=l", headers=BROWSER, timeout=12,
                         allow_redirects=False)
        loc = r.headers.get("Location", "")
        return loc if re.search(r"cdninstagram|fbcdn", loc) else ""
    if "tiktok.com" in url and "/video/" in url:
        d = requests.get("https://www.tiktok.com/oembed", params={"url": url}, headers=BROWSER, timeout=12).json()
        return d.get("thumbnail_url", "")
    r = requests.get(url, headers=BROWSER, timeout=10, stream=True)
    page = r.raw.read(500_000, decode_content=True).decode(r.encoding or "utf-8", "replace")
    for pat in META:
        m = re.search(pat, page, re.I)
        if m:
            src = html.unescape(m.group(1)).strip()
            return requests.compat.urljoin(url, src)
    return ""


def cited(memory: dict) -> set[str]:
    """Every signal id a room shows: desks' findings, their appendix, the board's evidence and references."""
    ids: set[str] = set()
    for key, lists in (("radar", ("moves", "signals")), ("brands", ("moves", "also"))):
        for k in lists:
            for it in (memory.get(key) or {}).get(k, []):
                ids |= set(it.get("evidence", []))
    for o in (memory.get("occasions") or {}).get("occasions", []):
        ids |= set(o.get("evidence", [])) | {e for i in o.get("insights", []) for e in i.get("evidence", [])}
    for t in memory.get("trends", []):
        ids |= set(t.get("evidence", [])) | set(t.get("looks", []))
    for p in memory.get("plays", []):
        if p.get("status") in ("new", "sent"):
            ids |= {r["id"] for r in p.get("references", [])}
    v = memory.get("voice") or {}
    ids |= {x.get("src") for k in ("love", "complaints", "language", "peers") for x in v.get(k, []) if x.get("src")}
    return ids


def enrich(memory: dict, now: datetime | None = None, limit: int = 80) -> int:
    """Find pictures for cited signals that have none. Returns how many were found."""
    now = now or datetime.now(timezone.utc)
    lib, retry = memory.get("library", {}), (now - timedelta(hours=12)).isoformat()
    todo = [lib[i] for i in cited(memory) if i in lib and not lib[i].get("thumb") and lib[i].get("url")
            and lib[i].get("thumb_tried", "") < retry][:limit]

    def one(s: dict) -> tuple[dict, str]:
        try:
            return s, picture(s["url"])
        except Exception as e:  # noqa: BLE001 — a missing picture is never fatal
            log.info("picture %s: %s", s["url"][:80], e)
            return s, ""

    found = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for s, pic in ex.map(one, todo):
            s["thumb_tried"] = now.isoformat()
            if pic:
                s["thumb"], found = pic, found + 1
    log.info("pictures: %d of %d signals without one now have one", found, len(todo))
    return found
