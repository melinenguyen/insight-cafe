# Setting up your trial office, step by step

Time: about 30 minutes, most of it filling in the dashboard. Cost: about $1 of Claude per report, on your own
Anthropic API key. Start on your computer; when you like it, open it 24/7 on GitHub (the last section).

## 1. Fill in the profile (the dashboard)
Open `dashboard/index.html` in a browser (double-click it; it works offline and saves as you type). Fill each
step; the left bar shows what's missing. Fields tagged **Full version** are for the full Insight Café; leave
them. Use "Draft the standing brief" when the rest is done, then edit the brief. Export `profile.json`.

## 2. Check and build
```bash
python3 scripts/validate.py profile.json
python3 scripts/scaffold.py --profile profile.json --out ~/Desktop/my-insight-cafe
```

## 3. Your Anthropic API key
Create one at https://console.anthropic.com/settings/keys and paste it into
`~/Desktop/my-insight-cafe/agency/.env`:
```
ANTHROPIC_API_KEY=sk-ant-…
```
The key stays in that file on your computer. Never paste it anywhere else.

## 4. First report
```bash
cd ~/Desktop/my-insight-cafe
python3 -m pip install -r agency/requirements.txt
python3 -m agency.run
```
A few minutes later the office opens in your browser. Run it again whenever you want a fresh report.

## Without Claude
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
   | `ANTHROPIC_API_KEY` | your Claude key |
   | `AGENCY_PASSPHRASE` | the office's lock: share it with your team |
   | `PUBLISH_TOKEN` | a fine-grained token with *Contents: read and write* on the site repo, so the run can publish |

4. **First run.** Actions → your café → Run workflow → slot `morning`. A few minutes later the office is live at
   `https://<owner>.github.io/<site-repo>/`. From then on the workflow checks the clock every hour and brews each
   report at its time.

Cost: about $1 of Claude per report (about $30 a month for one a day). The hourly checks fit in GitHub's free plan.
