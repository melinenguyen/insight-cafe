"""
What's due right now? On GitHub the workflow asks every hour, before anything is installed, so this uses only
the standard library.

- One or two reports a day at config.REPORTS (the team's time). A report is due once its time has passed and no
  report has finished since, so a GitHub cron that fires late, or not at all, is caught by the next tick, and a
  missed report is superseded by the newer one instead of piling up.
- A report that fails is retried on the next ticks, up to config.REPORT_RETRIES times a day.

    python -m agency.schedule      → morning | evening | none
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import config


def _memory() -> dict:
    p = config.DATA / "memory.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def last_due(name: str, now: datetime) -> datetime:
    """The most recent moment this report was due (the team's time)."""
    h, m = config.REPORTS[name]
    local = now.astimezone(ZoneInfo(config.TZ))
    at = local.replace(hour=h, minute=m, second=0, microsecond=0)
    return at if at <= local else at - timedelta(days=1)


def attempt_key(name: str, now: datetime) -> str:
    return f"{name}:{last_due(name, now).date()}"


def due(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    mem = _memory()
    done, tries = mem.get("reports", {}), mem.get("report_attempts", {})
    last_any = max(done.values(), default="")
    pending = [(last_due(n, now), n) for n in config.REPORTS
               if last_due(n, now).astimezone(timezone.utc).isoformat() > last_any
               and tries.get(attempt_key(n, now), 0) < config.REPORT_RETRIES]
    return max(pending)[1] if pending else "none"


def next_report(now: datetime) -> str:
    """The next report time, in the team's time ("07:00" or "07:00 tomorrow")."""
    local = now.astimezone(ZoneInfo(config.TZ))
    for day in (0, 1):
        for h, m in sorted(config.REPORTS.values()):
            t = (local + timedelta(days=day)).replace(hour=h, minute=m, second=0, microsecond=0)
            if t > local:
                return t.strftime("%H:%M") + ("" if day == 0 else " tomorrow")
    return ""


if __name__ == "__main__":
    print(due())
