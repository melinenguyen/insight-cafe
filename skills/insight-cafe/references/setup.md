# Setting up your trial office, step by step

Time: about 30 minutes, most of it filling in the dashboard. Cost: about $1 of Claude per report, on your own
Anthropic API key. Nothing is published; the office lives in a folder on your computer.

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
