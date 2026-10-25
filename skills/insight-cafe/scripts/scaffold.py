#!/usr/bin/env python3
"""
Turn a brand profile into your trial office, ready to run on your computer.

    python3 scaffold.py --profile profile.json --out ~/Desktop/acme-cafe [--force]

It validates the profile, copies the office (agency code and page), writes the profile and the standing brief
into it, leaves an .env file for your Anthropic API key, and prints the three steps to the first report.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
from validate import check  # noqa: E402

GITIGNORE = """__pycache__/
*.pyc
site/
agency/.env
agency/.cache/
"""
ENV = """# Your Anthropic API key (https://console.anthropic.com/settings/keys). This file never leaves your computer.
ANTHROPIC_API_KEY=
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--force", action="store_true", help="write into a folder that already has files")
    a = ap.parse_args()
    p = json.load(open(a.profile, encoding="utf-8"))
    errors, warns = check(p)
    for w in warns:
        print("!", w)
    if errors:
        for e in errors:
            print("✕", e)
        print("Fix these in the dashboard, export again, and re-run.")
        return 1
    out = Path(a.out).expanduser().resolve()
    if out.exists() and any(out.iterdir()) and not a.force:
        print(f"✕ {out} is not empty (use --force to write into it)")
        return 1

    shutil.copytree(SKILL / "template", out, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".cache", "data"))
    (out / "agency" / "data").mkdir(parents=True, exist_ok=True)
    (out / "agency" / "profile.json").write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding="utf-8")
    brief = (p.get("standing_brief") or "").strip() or f"# Standing brief — {p['brand']['name']}\n\n{p['brand'].get('one_liner', '')}\n"
    (out / "agency" / "standing_brief.md").write_text(brief + "\n", encoding="utf-8")
    env = out / "agency" / ".env"
    if not env.exists():
        env.write_text(ENV, encoding="utf-8")
    (out / ".gitignore").write_text(GITIGNORE)
    shutil.copy(SKILL / "references" / "agency-guide.md", out / "agency" / "CLAUDE.md")

    print(f"\n✓ {p['agency']['name']} for {p['brand']['name']} is ready in {out}\n")
    print("Three steps to your first report:")
    print(f"  1. Paste your Anthropic API key into {out / 'agency' / '.env'}")
    print(f"  2. cd {out} && python3 -m pip install -r agency/requirements.txt")
    print("  3. python3 -m agency.run      (a few minutes; the office opens in your browser)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
