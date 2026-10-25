---
name: insight-cafe
description: The Insight Café (trial) — set up a small AI research agency for any brand, shop or service, drawn as an illustrated office. Four AI specialists read culture, the calendar and competitors in the news, score the opportunities and write up the strongest one as a play; it runs on the user's own computer with their Anthropic API key. Use when someone wants to try an AI research agency or opportunity tracker for their brand, a trend and competitor watch, or a daily marketing brief, or wants to set up, run or change their trial office. Starts from a local setup dashboard that collects the brand's context.
---

# The Insight Café (trial)

A brand's own research agency, drawn as an office. In the trial, four AI specialists work:

| Crew | Job |
|---|---|
| Coca | The brief: what happened, what it means, what we do — answer first |
| Espresso | Culture & social radar, and what people think, feel and do around the next occasions |
| Chai | Brand watch: what competitors launched, said and did, from the news |
| Matcha | Every opportunity, scored on five axes for the brand |

The studio writes the strongest play in full (hooks, approach, tactics, references). Mocha (ads), Latte
(customer voice) and Tonic's Slack hand-over sit in the office too, locked: they are part of the full Insight
Café, along with the morning huddle that learns the lead's taste and the 24/7 cloud schedule. When the user
asks for one of those, say plainly that it is in the full version.

## What's in this skill
- `dashboard/index.html` — the setup dashboard. Opens offline, autosaves, EN/VI. Exports `profile.json`.
  Fields tagged "Full version" are locked and never required.
- `references/setup.md` — the human steps. `references/profile-schema.md` — every profile field.
  `references/agency-guide.md` — how an office works (it becomes the office's CLAUDE.md).
- `scripts/validate.py` checks a profile; `scripts/scaffold.py` builds an office folder from it.
- `template/` — the office code (`agency/`) and the office page. Nothing brand-specific lives here.
- `profiles/` — two made-up examples: a US skincare brand (the dashboard's "Load the example") and a
  Vietnamese one.

## Workflow

1. **Collect the context.** Open the dashboard for the user (`open dashboard/index.html`). If they would rather
   talk it through, ask for the sections in the schema order and write `profile.json` yourself. Use the user's
   own words for the brand, voice and rules. Ask, don't invent: competitors, offers and claims come from the user.
2. **Validate.** `python3 scripts/validate.py profile.json`. Fix errors with the user; warnings are fine.
3. **Scaffold.** `python3 scripts/scaffold.py --profile profile.json --out ~/Desktop/<name>-insight-cafe`.
   Always an absolute path under the user's home, never a relative one (the scripts sit inside the skill folder).
4. **The key.** The user pastes their Anthropic API key into `<office>/agency/.env`. Never ask for the key,
   never print it, never write it anywhere else.
5. **First report.** In the office folder: `python3 -m pip install -r agency/requirements.txt`, then
   `python3 -m agency.run`. It takes a few minutes and costs about $1 of Claude; say so before running it.
   The office opens from `site/index.html`. Walk the user through the rooms.
6. **Without spending:** `python3 -m agency.run --scouts` shows what the scouts find; `--rebuild` redraws
   the office from the last report.

## Rules
- Every number in a report comes from a signal or says "not available". Every finding shows its proof.
- The office reads public information only and never posts, likes, follows or messages on any platform.
- No brand is ever impersonated.
