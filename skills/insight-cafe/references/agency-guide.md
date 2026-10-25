# The Insight Café (trial): how this office works

A research agency drawn as an office. Four AI specialists read culture, the calendar and your competitors in
the news, score the opportunities for your brand and write up the strongest one as a play for your team.
Everything brand-specific lives in `agency/profile.json` (written by the setup dashboard); the code reads it
through `agency/config.py`.

This is the trial. Three more specialists (Mocha: ads, Latte: customer voice, Tonic: Slack hand-over), the
morning huddle that teaches the crew your taste, and the 24/7 cloud schedule are part of the full Insight Café.
Their rooms are in the office, locked.

## How it runs

| Command | What it does | Cost |
|---|---|---|
| `python -m agency.run` | scouts → desks → office: a full report, then opens `site/index.html` | about $1 of Claude, a few minutes |
| `python -m agency.run --rebuild` | redraws the office from the last report | free |
| `python -m agency.run --scouts` | prints what the scouts find right now | free |

The Anthropic API key lives in `agency/.env` (`ANTHROPIC_API_KEY=…`), or in the environment.

## The crew

| Who | Job | Desk | Room |
|---|---|---|---|
| Coca | The brief: what happened, what it means, what we do | strategy memo | `desk` |
| Espresso | Culture & social radar + the occasion pulse | `desks.radar`, `desks.occasions` | `radar`, `calendar` |
| Chai | Brand watch: what other brands launched, said, did | `desks.brands` | `brands` |
| Matcha | Opportunities, scored on five axes | strategy board | `wall` |
| Tonic | The plays (the trial writes the top one in full) | studio | `war` |
| Mocha, Latte | Ads and customer voice | full version | `inspo`, `voice` (locked) |

Every report reads the same way: the answer first, 3-5 numbered findings (what happened → proof → why it
matters → what we steal, and who), the rest folded as appendix. Every signal shows its proof: `visual.py`
finds a picture for every cited link.

## Sources (`sources.py`), all free and keyless

News (the profile's RSS feeds or a pack in `feeds.py`, plus Bing News searches in the market's language),
Google Trends (`market.trends_geo`), your competitors in the news (a Bing News search per competitor), the
shop catalogue (Shopify `products.json` or the profile's products), the calendar (`calendar_world.py`: the
full US calendar, or any country's public holidays + global moments + your dates), the occasion pulse (news
about the next occasions) and Pinterest pins for Pinterest plays. A scout that fails says why and returns
nothing; the office never invents.

## Things that are not obvious from the code

- **The board schema sits at the structured-output grammar limit.** Adding a field to `BOARD_SCHEMA` can get
  "compiled grammar is too large". Test any schema change with a small request first.
- **Memory** is `agency/data/memory.json`: the board, the plays and a 30-day history of what was seen when.
  Delete it to start fresh.

## Changing things

Everything about the brand: edit `agency/profile.json` (or re-export from the dashboard). House rules:
`agency/standing_brief.md`.
