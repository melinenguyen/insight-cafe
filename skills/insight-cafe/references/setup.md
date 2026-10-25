# Setting up your trial office, step by step

Time: about 30 minutes, most of it filling in the dashboard. Cost: free with a Gemini or OpenRouter key, or about
$1 per report on Claude. Start on your computer; when you like it, open it 24/7 on GitHub (the last section).

## 1. Fill in the profile (the dashboard)
Open `dashboard/index.html` in a browser (double-click it; it works offline and saves as you type). Fill each
step; the left bar shows what's missing. Fields tagged **Full version** are for the full Insight Café; leave
them. Use "Draft the standing brief" when the rest is done, then edit the brief. Export `profile.json`.

## 2. Check and build
```bash
python3 scripts/validate.py profile.json
python3 scripts/scaffold.py --profile profile.json --out ~/Desktop/my-insight-cafe
```

## 3. Your AI key (pick one)
Paste ONE key into `~/Desktop/my-insight-cafe/agency/.env`:

| AI | Line in `.env` | Cost | Get the key |
|---|---|---|---|
| **Gemini** (Google), the free default | `GEMINI_API_KEY=…` | free tier, no card | https://aistudio.google.com/apikey |
| **Open-source models** via OpenRouter | `OPENROUTER_API_KEY=…` | free models, no card | https://openrouter.ai/keys |
| **Claude** (Anthropic), the sharpest | `ANTHROPIC_API_KEY=…` | about $1 a report | https://console.anthropic.com/settings/keys |
| **Ollama**, on your own computer | `AGENCY_AI=ollama` | free, nothing leaves your laptop | install https://ollama.com, then `ollama pull qwen3:8b` |

Good to know about free tiers: they have daily limits (one or two reports a day fit), the free models can change,
and the provider may use what you send to improve its models. The café sends public news and trends plus your
brand profile, never customer data, but don't put secrets in your profile. Use your personal account for the
key, not a work account. The key stays in that file on your computer. Never paste it anywhere else.

More than one key? `AGENCY_AI=gemini` (or `openrouter`, `claude`, `ollama`) picks. `AGENCY_MODEL=…` swaps the
model. Any other OpenAI-compatible service works too: `AGENCY_AI=custom` with `LLM_BASE_URL`, `LLM_API_KEY` and
`LLM_MODEL`. Details in `agency/llm.py`.

## 4. First report
```bash
cd ~/Desktop/my-insight-cafe
python3 -m pip install -r agency/requirements.txt
python3 -m agency.run
```
A few minutes later the office opens in your browser. Run it again whenever you want a fresh report.

## Without the AI
`python3 -m agency.run --scouts` shows what the scouts find right now; `--rebuild` redraws the office from the
last report. Neither spends anything.

## Open 24/7 on GitHub (free)
The café then reports on its own at your report times, and the office lives online behind a passphrase, running on
real time: the clocks, day and night outside the windows, and decor for the occasions on your calendar.

1. **Profile.** In the dashboard's *Schedule & delivery*: your team's time zone, one or two report times, and two
   repo names: `delivery.brain_repo` (private: the code and the café's memory) and `delivery.site_repo` (public:
   the encrypted office page). Export, then scaffold again; this writes `.github/workflows/agency.yml`.
2. **Repos.** Create the private brain repo and push the café folder to it. Create the public site repo (empty is
   fine) and switch on Pages: Settings → Pages → deploy from `main`, root.
3. **Secrets** (brain repo → Settings → Secrets and variables → Actions):

   | Secret | What it is |
   |---|---|
   | `GEMINI_API_KEY` (or `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`) | your AI key, under the same name as in `.env` |
   | `AGENCY_PASSPHRASE` | the office's lock: share it with your team |
   | `PUBLISH_TOKEN` | a fine-grained token with *Contents: read and write* on the site repo, so the run can publish |

   To choose between several keys or swap the model, add *variables* (the tab next to Secrets) named
   `AGENCY_AI` or `AGENCY_MODEL`.

4. **First run.** Actions → your café → Run workflow → slot `morning`. A few minutes later the office is live at
   `https://<owner>.github.io/<site-repo>/`. From then on the workflow checks the clock every hour and brews each
   report at its time.

Cost: free on Gemini or OpenRouter within their daily limits; about $1 per report on Claude (about $30 a month for
one a day). The hourly checks fit in GitHub's free plan. Ollama can't run here: it lives on your computer.
