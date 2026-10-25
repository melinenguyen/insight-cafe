"""
Builds the office: memory.json → site/index.html.

Two ways to open the café:
- on GitHub, 24/7: the page is AES-GCM encrypted with a key derived from the passphrase and decrypted in the
  browser, so the public site repo only ever holds ciphertext (third-party thumbnails ride inside it as data URIs);
- on your computer: one plain page with everything inside it, opened straight from the folder.
"""

from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import calendar_world, config, schedule, state

log = logging.getLogger("agency.build")
CACHE = Path(os.getenv("AGENCY_CACHE_DIR", config.ROOT / ".cache"))
PBKDF2_ITER = 310_000

# what the full office adds, room by room — shown in the trial's locked rooms
FULL = {
    "inspo": ["Mocha watches your competitors' live Facebook and Instagram ads, every two hours",
              "Spots the ads they keep running (the ones that work) and the new ones they launch",
              "Proposes your static and video ads for every funnel stage, and says why each will work"],
    "voice": ["Latte reads your reviews on your website and Amazon, and what people say on YouTube",
              "Groups them into what customers love, what they complain about and what stops them buying",
              "Hands you their exact words for hooks, product pages and FAQs"],
    "huddle": ["Every morning the crew asks you one question each",
               "Your answers teach them your taste: they remember what you skip and what you love",
               "One click re-plans the whole board around what you said"],
    "dispatch": ["Tonic sends every play to its owner on Slack, with the idea, the proof and the due day",
                 "Quiet hours respected; you preview first, then switch the team on"],
    "archive": ["Every report kept, so you can see what changed and what the crew got right"],
    "rules": ["Latte checks every line against your rule book before it reaches the team"],
    "plays": ["The studio writes every commissioned play, not just the top one"],
    "always": ["Instagram, TikTok, YouTube and Reddit scouts on top of the news, search and the calendar",
               "A 24/7 ad spy that checks your competitors' new ads every two hours"],
}


# ---------------------------------------------------------------------------
# images
# ---------------------------------------------------------------------------
def _fetch(url: str, timeout: int = 25) -> bytes | None:
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.7.1", "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001 — a missing picture is never fatal
        log.info("image fetch failed %s: %s", url[:80], e)
        return None


def _jpeg(data: bytes, max_side: int, quality: int, ground=(243, 236, 226)) -> bytes | None:
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, ground)
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im.thumbnail((max_side, max_side))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
        return out.getvalue()
    except Exception as e:  # noqa: BLE001
        log.info("image decode failed: %s", e)
        return None


def _cached(url: str, max_side: int, quality: int) -> bytes | None:
    """Fetch + re-encode once; later builds reuse the cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.sha1(f"{url}|{max_side}|{quality}".encode()).hexdigest() + ".jpg")
    if f.exists():
        return f.read_bytes()
    raw = _fetch(url)
    jpg = _jpeg(raw, max_side, quality) if raw else None
    if jpg:
        f.write_bytes(jpg)
    return jpg


def _datauri(jpg: bytes | None) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode() if jpg else ""


# ---------------------------------------------------------------------------
# the standing brief, as simple HTML (headings, lists, bold, italics)
# ---------------------------------------------------------------------------
def md_to_html(md: str) -> str:
    out, in_list = [], False

    def inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        return re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", s)

    for line in md.splitlines():
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(line[2:])}")
            continue
        if line.startswith("  ") and in_list and line.strip():
            out[-1] += " " + inline(line.strip())
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if line.startswith("# "):
            out.append(f"<h1 style='font-size:28px'>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.strip():
            if out and out[-1].startswith("<p>") and not out[-1].endswith("</p>"):
                out[-1] += " " + inline(line)
            else:
                out.append(f"<p>{inline(line)}")
        elif out and out[-1].startswith("<p>"):
            out[-1] += "</p>"
    if in_list:
        out.append("</ul>")
    return "\n".join(x + ("</p>" if x.startswith("<p>") and not x.endswith("</p>") else "") for x in out)


# ---------------------------------------------------------------------------
# encryption (matches unlock() in office.html)
# ---------------------------------------------------------------------------
def encrypt(payload: dict, passphrase: str) -> str:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=PBKDF2_ITER).derive(passphrase.encode())
    ct = AESGCM(key).encrypt(iv, json.dumps(payload, ensure_ascii=False).encode(), None)
    b = lambda x: base64.b64encode(x).decode()  # noqa: E731
    return json.dumps({"v": 1, "iter": PBKDF2_ITER, "salt": b(salt), "iv": b(iv), "ct": b(ct)})


def payload(memory: dict, site: Path, now: datetime, cloud: bool = False) -> dict:
    assets = site / "assets"
    (assets / "p").mkdir(parents=True, exist_ok=True)

    catalogue = []
    for p in memory.get("catalogue", []):
        img = ""
        if p.get("images"):
            jpg = _cached(p["images"][0], 900, 80)
            if jpg:
                (assets / "p" / f"{p['key']}.jpg").write_bytes(jpg)
                img = f"assets/p/{p['key']}.jpg"
        catalogue.append({k: p.get(k) for k in ("key", "title", "price", "compare_at", "in_stock", "url")} | {"img": img})

    library = {sid: {**s, "thumb_data": _datauri(_cached(s.get("thumb", ""), 360, 68)) if s.get("thumb") else ""}
               for sid, s in memory.get("library", {}).items()}
    pics = {n: {"owns": p["owns"], "lanes": p["lanes"], "slack_url": ""} for n, p in config.PICS.items()}
    staff = [{**s, "status": (memory.get("staff") or {}).get(s["id"], {}).get("status", ""),
              "learned": (memory.get("staff") or {}).get(s["id"], {}).get("learned", "")} for s in config.STAFF]
    ny = now.astimezone(ZoneInfo(config.OFFICE_TZ)).date()
    return {
        "generated_at": now.isoformat(), "updated_at": memory.get("updated_at", now.isoformat()),
        "slot": memory.get("slot", ""), "next_sweep": schedule.next_report(now) if cloud else "when you run it",
        "schedule_note": " and ".join(f"{h:02d}:{m:02d}" for h, m in config.REPORTS.values()) if cloud else "whenever you run it",
        "memo": memory.get("memo", {}), "trends": memory.get("trends", []), "plays": memory.get("plays", []),
        "library": library, "catalogue": catalogue, "staff": staff,
        "questions": memory.get("questions") or {s["id"]: s["question"] for s in config.STAFF},
        "huddle": None, "scouts": memory.get("scouts", {}), "blocked": memory.get("blocked", []),
        "pics": pics, "dispatch": {"mode": "trial", "log": []}, "archive": [], "runs": memory.get("runs", [])[-20:],
        "history": {h["id"]: {"first_seen": h["first_seen"], "times": h["times"]} for h in memory.get("trend_history", [])},
        "signals_total": (memory.get("runs") or [{}])[-1].get("signals", 0),
        "calendar": calendar_world.occasions(ny - timedelta(days=45), ny + timedelta(days=400)),
        "office_tz": config.OFFICE_TZ, "voice": None, "chamber": None, "adspy": {},
        "reports": memory.get("reports", {}), "report_times": {},
        "radar": memory.get("radar"), "brands": memory.get("brands"), "learned": [],
        "occasions": memory.get("occasions"), "review_stats": None, "digests": memory.get("digests", [])[-20:],
        "brand": {"name": config.BRAND["name"], "short": config.BRAND["short"], "website": config.BRAND["website"],
                  "lead": config.OWNER["name"], "team": list(config.PICS), "team_city": config.TEAM_CITY,
                  "team_tz": config.TZ, "agency": config.AGENCY["name"], "tagline": config.AGENCY["tagline"],
                  "city": config.AGENCY["city"], "neighbourhood": config.AGENCY["neighbourhood"],
                  "scene": config.AGENCY["scene"], "market": config.MARKET_NAME, "country": config.COUNTRY,
                  "currency": config.CURRENCY, "radar_sections": __import__("agency.desks", fromlist=["SECTIONS"]).SECTIONS},
        "brief_html": md_to_html((config.ROOT / "standing_brief.md").read_text(encoding="utf-8") if (config.ROOT / "standing_brief.md").exists() else config.STANDING_BRIEF),
        "trial": {"locked": config.LOCKED_ROOMS, "full": FULL, "url": config.FULL_URL, "cloud": cloud,
                  "locked_plays": memory.get("locked_plays", []), "plays_written": config.TRIAL_PLAYS},
    }


def build(memory: dict, *, passphrase: str = "", site: Path | None = None, now: datetime | None = None) -> Path:
    """With a passphrase: the encrypted page GitHub Pages serves. Without one: a plain page for this computer."""
    now = now or datetime.now(timezone.utc)
    site = site or config.SITE
    site.mkdir(parents=True, exist_ok=True)
    data = payload(memory, site, now, cloud=bool(passphrase))
    tpl = (config.ROOT / "web" / "office.html").read_text(encoding="utf-8")
    for k, v in (("__AGENCY__", config.AGENCY["name"]), ("__TAGLINE__", config.AGENCY["tagline"]),
                 ("__CITY__", config.AGENCY["city"])):
        tpl = tpl.replace(k, html.escape(v))
    if passphrase:
        page = tpl.replace("/*__VAULT__*/", encrypt(data, passphrase))
        (site / ".nojekyll").write_text("", encoding="utf-8")
    else:  # "</" inside the JSON would close the script tag early
        page = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    (site / "index.html").write_text(page, encoding="utf-8")
    log.info("built %s (%d KB, %d plays, %d trends, %s)", site / "index.html", len(page) // 1024,
             len(data["plays"]), len(data["trends"]), "encrypted" if passphrase else "plain")
    return site / "index.html"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build(state.load())
