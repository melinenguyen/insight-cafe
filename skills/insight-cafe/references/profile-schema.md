# The brand profile (`profile.json`)

One file holds everything an office needs to know about a brand. The setup dashboard
(`dashboard/index.html`) writes it; `scripts/scaffold.py` turns it into an office. Every prompt, scout,
watchlist and room reads from it — nothing brand-specific lives in code.

**The trial reads part of it.** These fields belong to the full Insight Café; the trial ignores them and the
dashboard shows them locked: `competitors.instagram_watch`, all of `creative`, `sources.youtube_searches`,
`sources.voice_queries`, `sources.voice_peer_queries`, `sources.listen_plan`, `sources.reviews`,
`sources.mentions_feed`, `content.instagram_hashtags`, `content.tiktok_hashtags`, every Slack id,
`schedule.reports`, `schedule.adspy_every_min`, `schedule.quiet_hours` and all of `delivery`.

`*` = required. Everything else has a sensible default or is simply skipped when empty.
`profiles/example-us-skincare.json` is a complete example (a made-up brand).

## agency — the office itself
| Field | Type | Meaning |
|---|---|---|
| `name`* | text | The agency's name, shown on the office ("The Insight Café"). |
| `tagline` | text | Under the name ("Your AI research agency"). |
| `office_city`* | text | Where the office is drawn and whose clock it keeps ("New York", "Ho Chi Minh City", "London"). |
| `office_neighbourhood` | text | Optional flavour ("SoHo"). |
| `office_tz`* | IANA tz | The office's clock, sky and decor ("America/New_York"). |
| `scene` | `newyork` \| `city` | `newyork` draws the Empire State, Chrysler and Brooklyn Bridge; `city` draws a generic skyline. |
| `report_language` | text | The language every report is written in ("English (US)", "Tiếng Việt", "Bahasa Indonesia"). |
| `crew` | list | The seven AI staff. Each: `id`, `name`, `role`, `job`, `question` (asked at the huddle), `look` (drawing: `hair`, `top`, `skin`, `acc`, optional `hairColor`). Defaults to the standard crew: Coca (brief), Espresso (culture & occasions), Chai (brand watch), Mocha (creative strategy), Latte (customer voice), Matcha (opportunities), Tonic (plays). Rename freely; keep the ids. |

## brand — who we are
| Field | Type | Meaning |
|---|---|---|
| `name`* | text | Full brand name. |
| `short`* | text | What the team calls it in a sentence ("Fernlight"). |
| `website` | url | Main site. |
| `category`* | text | What it sells, in the market's words ("Natural skincare", "Specialty coffee"). |
| `one_liner`* | text | One sentence: what it is and why it exists. |
| `benefit` | text | The brand benefit / promise. |
| `signature` | text | The visual or verbal red thread every asset carries. |
| `price_position` | text | "Premium ($32–$88)", "Mass", "Luxury"… |
| `voice.tone`* | text | How it sounds. |
| `voice.banned_words` | list | Words never used. |
| `voice.no_exclamation_marks` | bool | |
| `look`* | text | What on-brand pictures look like (light, materials, framing, palette). The ad curator scores every competitor picture against this. |
| `look_avoid` | text | What scores low (e.g. "high-key studio light, floating product, discount banners"). |

## business — how it makes money
`model` (DTC, marketplace, retail, B2B, subscription, service…), `channels` (list: "Shopify", "Amazon US",
"Shopee VN", "Sephora"…), `season_focus` (what this quarter is about), `goals` (text), `kpis` (list).

## market — where it competes
| Field | Meaning |
|---|---|
| `country`* | ISO code ("US", "VN", "GB", "SG", "AU"…). Sets the holiday calendar. |
| `language`* | BCP-47 ("en-US", "vi-VN"). Used for news and YouTube searches. |
| `currency`* | "USD", "VND"… |
| `bing_mkt` | News market for Bing News ("en-US", "vi-VN", "en-GB"). Defaults to `language`. |
| `trends_geo` | Google Trends geo. Defaults to `country`. |
| `youtube_region` | Defaults to `country`. |
| `calendar` | "US" uses the full US calendar (holidays, retail moments, heritage months, decor); any other country uses public holidays for that country plus the global moments below. |
| `global_moments` | list of: `valentines`, `womens_day`, `mothers_day`, `fathers_day`, `black_friday`, `cyber_monday`, `singles_day` (11.11), `double_12` (12.12), `christmas`, `new_year`, `lunar_new_year`, `mid_autumn`, `diwali`, `eid`, `ramadan`, `halloween`. |

## audience
`personas` — list of `{name*, description*}`. The strategy desk tags every opportunity to one.
`insights` — free text: what you already know about them.

## products and offers
`products` — list of `{name*, price, key, url, asin, hero}`. `hero: true` marks the products to push.
`catalog.shopify_domain` — if set, the live catalogue (prices, stock, images) is read from Shopify.
`offers.rules`* — the one offer scheme the agency may use. `offers.never` — list.
`claims_never` — claims no copy may make.

## competitors
`peers` — like-minded brands you position beside (their ads are the reference library):
list of `{name*, domain*, foreplay_id}`. `performance` — direct competitors whose paid creative you
benchmark (same shape). `foreplay_id` is filled by `scripts/scaffold.py --resolve-foreplay` from the
domain. `instagram_watch` — Instagram handles whose posts the brand watch reads. `also_watch` — other
names the brand watch looks for in the news.

## content
`pillars` (list), `categories` (list — what an opportunity can be about), `platforms` (list),
`formats` (list), `instagram_hashtags` (≤12, fixed — Instagram allows 30 unique hashtags a week),
`tiktok_hashtags` (list).

## creative
`angles` (id → line; the arguments your ads make), `concepts` (id → name; the containers they're shot in),
`doctrine` (how you test), `production_rules`. Defaults to a general evergreen library.

## sources
| Field | Meaning |
|---|---|
| `news_feeds` | `{name: rss_url}` or the name of a default pack (`default:us-beauty-culture`). |
| `news_queries` | Bing News searches in the market language — the simplest way to cover any market ("skincare Vietnam", "mỹ phẩm"). |
| `youtube_searches` | What's trending in your world on YouTube. |
| `voice_queries` | Review videos whose comments the listening desk reads. |
| `voice_peer_queries` | `{query: brand}` — review videos about like-minded brands (their audience's words). |
| `listen_plan` | For the optional Mac gatherer (Agent Reach): `{youtube: [...], instagram: [handles]}`. |
| `reviews.judgeme_shop` | `xxx.myshopify.com` if the store uses Judge.me (public review feed). |
| `reviews.amazon_domain` | "www.amazon.com", "www.amazon.co.uk"… |
| `reviews.amazon_ours` / `amazon_peers` | `{asin, name}` / `{asin, brand, name}`. |
| `mentions_feed` | Optional JSON feed of your own brand mentions. |

## calendar
`occasions` — your own dates: `{date YYYY-MM-DD, name, note}`. Notes are rules for that date
("Content only — do not sell").

## team — the humans
`lead` — `{name*, role, slack_id}`: the person the huddle asks. `members` — the people plays go to:
`{name*, slack_id, owns*, lanes* (list)}`. Each lane is a kind of work ("Social media",
"Earned media & PR", "Ads creative (UGC & creators)"). `slack_team` — workspace id for deep links.

## schedule
`team_tz`* (the team's time zone), `reports` (list of "HH:MM" in team time, default 06:30 and 18:30),
`adspy_every_min` (default 110), `quiet_hours` ([22, 6] — no Slack between).

## delivery
`brain_repo`* ("owner/repo", private: code + memory), `site_repo`* ("owner/repo", public: the encrypted
office on GitHub Pages), `site_url`, `dispatch_mode` (`preview` sends every ticket to the lead first;
`live` sends to the team).

## standing_brief
Markdown: the house rules every desk follows (the season's message, offer, pillars weighting, visual
rules, claims, who does what). The dashboard drafts it from the fields above; edit freely.
