#!/usr/bin/env python3
"""
Turn a brand profile into your café, ready to run on your computer, or on GitHub around the clock.

    python3 scaffold.py --profile profile.json --out ~/Desktop/acme-cafe [--force]

It validates the profile, copies the office (agency code, page and the GitHub workflow), writes the profile and
the standing brief into it, leaves an .env file for your Anthropic API key, and prints the next steps: three to
run a report on your computer, and, when the profile names its GitHub repos, the four to open 24/7.
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
# the café's memory IS agency/data/*.json: keep it committed
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
    d = p.get("delivery") or {}
    brain, site_repo = d.get("brain_repo", ""), d.get("site_repo", "")
    wf = out / ".github" / "workflows" / "agency.yml"
    if site_repo:
        site_url = d.get("site_url") or f"https://{site_repo.split('/')[0]}.github.io/{site_repo.split('/')[1]}/"
        name = p["agency"]["name"].replace("'", "’").replace('"', "”")  # lands inside YAML
        wf.write_text(wf.read_text(encoding="utf-8").replace("__SITE_REPO__", site_repo).replace("__AGENCY__", name),
                      encoding="utf-8")
    else:
        shutil.rmtree(out / ".github", ignore_errors=True)

    print(f"\n✓ {p['agency']['name']} for {p['brand']['name']} is ready in {out}\n")
    print("Three steps to your first report:")
    print(f"  1. Paste your Anthropic API key into {out / 'agency' / '.env'}")
    print(f"  2. cd {out} && python3 -m pip install -r agency/requirements.txt")
    print("  3. python3 -m agency.run      (a few minutes; the office opens in your browser)")
    if site_repo:
        print("\nOpen 24/7 on GitHub (free; see references/setup.md):")
        print(f"  1. Create a PRIVATE repo {brain or 'you/your-cafe-brain'} and push this folder to it.")
        print(f"  2. Create a PUBLIC repo {site_repo}; Settings → Pages → deploy from main, root.")
        print("  3. In the private repo → Settings → Secrets and variables → Actions, add ANTHROPIC_API_KEY,")
        print("     AGENCY_PASSPHRASE (the office's lock) and PUBLISH_TOKEN (a token that can push to the public repo).")
        print(f"  4. Actions → Run workflow (slot: morning). Your office opens at {site_url}")
    else:
        print("\nWant it open 24/7? Add your two GitHub repos in the dashboard (Schedule & delivery), export, and scaffold again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
