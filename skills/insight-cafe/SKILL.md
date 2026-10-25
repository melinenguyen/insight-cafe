---
name: insight-cafe
description: The Insight Café (trial) — set up a small AI research agency for any brand, shop or service, drawn as an illustrated office. Four AI specialists read culture, the calendar and competitors in the news, score the opportunities and write up the strongest one as a play. It opens 24/7 on GitHub (scheduled reports, an encrypted office page that lives on the real calendar) or runs on the user's computer, with their own AI key: free Gemini or open-source models, or Claude. Use when someone wants to try an AI research agency or opportunity tracker for their brand, a trend and competitor watch, or a daily marketing brief, or wants to set up, run or change their trial office. Starts from a local setup dashboard that collects the brand's context.
---

# The Insight Café (trial)

A brand's own research agency, drawn as an office. In the trial, four AI specialists work:

| Crew | Job |
|---|---|
| Coca | The brief: what happened, what it means, what we do — answer first |
| Espresso | Culture & social radar, and what people think, feel and do around the next occasions |
| Chai | Brand watch: what competitors launched, said and did, from the news |
| Matcha | Every opportunity, scored on five axes for the brand |

The studio writes the strongest play in full (hooks, approach, tactics, references). The café opens 24/7 on
GitHub: reports at the user's times, and an office page that runs on real time (clocks, day and night, decor for
the calendar's occasions), locked with a passphrase. Mocha (ads), Latte (customer voice), Tonic's Slack
hand-over, the morning huddle that learns the lead's taste, the 2-hourly ad spy and the report archive sit in the
office too, locked: they are part of the full Insight Café. When the user asks for one of those, say plainly that
it is in the full version.

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
4. **The AI and its key.** Ask which AI writes the reports, then the user pastes one key into
   `<office>/agency/.env`. Never ask for the key, never print it, never write it anywhere else.
   - **Gemini** (`GEMINI_API_KEY`, free from aistudio.google.com/apikey, no card) is the default: free, a big
     context, good writing. Say plainly that free tiers have daily limits and Google may use what is sent to
     improve its models (the café sends public signals and the brand profile, nothing private).
   - **OpenRouter** (`OPENROUTER_API_KEY`, free from openrouter.ai/keys): free open-source models; the same
     caveats, and the free models change over time.
   - **Claude** (`ANTHROPIC_API_KEY`): the sharpest reports, about $1 each.
   - **Ollama** (`AGENCY_AI=ollama`): an open-source model on the user's own computer, nothing leaves it, but it
     needs ollama.com installed, a strong laptop and patience, and it can't run 24/7 on GitHub.
   `agency/llm.py` explains the rest (`AGENCY_MODEL` to change the model, `AGENCY_AI=custom` for any
   OpenAI-compatible service).
5. **First report.** In the office folder: `python3 -m pip install -r agency/requirements.txt`, then
   `python3 -m agency.run`. It takes a few minutes; free on Gemini or OpenRouter, about $1 on Claude. Say
   which before running it.
   The office opens from `site/index.html`. Walk the user through the rooms.
6. **Without spending:** `python3 -m agency.run --scouts` shows what the scouts find; `--rebuild` redraws
   the office from the last report.
7. **Open 24/7 (when the user asks, e.g. "open my café 24/7").** Follow `references/setup.md` → "Open 24/7":
   - Ask for the report time(s) and the two repo names (private brain, public site); put them in
     `schedule.reports` and `delivery` in the profile, validate and scaffold again (this writes the workflow).
   - Creating repos, pushing and switching on Pages are the user's calls: confirm before doing any of them. With
     the `gh` CLI signed in, you can run them for the user once they say yes.
   - The three secrets (the AI key under the same name as in `.env`, `AGENCY_PASSPHRASE`, `PUBLISH_TOKEN`) are
     pasted by the user in the repo's Settings. Never ask for, print or store their values.
   - Say the cost before switching it on: free on Gemini or OpenRouter (within their daily limits: one or two
     reports a day fit), about $1 per report on Claude (about $30 a month for one a day). GitHub's free plan
     covers the hourly checks.
   - First run: Actions → Run workflow → slot `morning`, then open the site URL with the passphrase.

## Rules
- Every number in a report comes from a signal or says "not available". Every finding shows its proof.
- The office reads public information only and never posts, likes, follows or messages on any platform.
- No brand is ever impersonated.
