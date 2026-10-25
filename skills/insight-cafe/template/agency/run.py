"""
One trial report, end to end:

    python -m agency.run              # scouts → desks → office: a full report (a few minutes, about $1 of Claude)
    python -m agency.run --rebuild    # just redraw the office from the last report (free, no Claude)
    python -m agency.run --scouts     # see what the scouts find right now (free, no Claude)

Put your Anthropic API key in agency/.env (ANTHROPIC_API_KEY=sk-ant-…) or export it. The office opens from
site/index.html. If the brain fails, the office is still drawn from the last good report.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import webbrowser
from datetime import datetime, timezone

from . import build, config, sources, state, visual

log = logging.getLogger("agency")


def _load_env() -> None:
    """KEY=value lines from agency/.env, without overriding what's already set."""
    f = config.ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        k, _, v = line.strip().partition("=")
        if k and not k.startswith("#") and v and k not in os.environ:
            os.environ[k] = v.strip().strip('"').strip("'")


def main() -> int:
    ap = argparse.ArgumentParser(description=f"{config.AGENCY['name']} (trial)")
    ap.add_argument("--rebuild", action="store_true", help="redraw the office from the last report, no Claude")
    ap.add_argument("--scouts", action="store_true", help="print what the scouts find, no Claude")
    ap.add_argument("--no-open", action="store_true", help="don't open the office in the browser")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    _load_env()

    if args.scouts:
        sweep = sources.sweep()
        print(json.dumps(sweep["status"], indent=1))
        print(len(sweep["signals"]), "signals,", len(sweep["catalogue"]), "products")
        return 0

    now = datetime.now(timezone.utc)
    memory = state.load()
    error = None
    if not args.rebuild:
        if not (config.env("ANTHROPIC_API_KEY") or config.env("ANTHROPIC_AUTH_TOKEN")):
            print("✕ No Anthropic API key. Add ANTHROPIC_API_KEY=… to agency/.env, or export it, then run again.\n"
                  "  Get a key at https://console.anthropic.com/settings/keys")
            return 1
        from . import brain
        sweep = sources.sweep()
        log.info("scouts: %s", {k: (v["ok"], v["count"]) for k, v in sweep["status"].items()})
        if not sweep["catalogue"] and memory.get("catalogue"):
            sweep["catalogue"] = memory["catalogue"]
        try:
            office, usage = brain.think(sweep, memory, "report", now)
            state.merge(memory, office, sweep, "report", usage, now)
            memory.pop("last_error", None)
            memory.setdefault("reports", {})["report"] = now.isoformat()
            log.info("report done: $%s of Claude", usage["usd"])
        except Exception as e:  # noqa: BLE001 — draw the last good report, then say what broke
            log.exception("brain failed")
            error = f"{type(e).__name__}: {e}"
            memory["last_error"] = {"at": now.isoformat(), "slot": "report", "error": error[:400]}
        try:  # a picture for every signal the office shows
            visual.enrich(memory, now)
        except Exception as e:  # noqa: BLE001 — pictures are never worth a failed run
            log.warning("pictures: %s", e)
        state.save(memory)

    page = build.build(memory, now=now)
    print(f"\n{'⚠ The report failed: ' + error[:200] if error else '✓ Your office is ready'}: {page}")
    if not args.no_open:
        webbrowser.open(page.resolve().as_uri())
    return 1 if error else 0


if __name__ == "__main__":
    sys.exit(main())
