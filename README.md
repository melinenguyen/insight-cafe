<p align="center">
  <img src="docs/hero.png" width="100%" alt="The Insight Café: your AI research agency. Fresh insights, served every morning.">
</p>

<p align="center">
  <a href="#-order-in-two-lines"><img alt="Free trial: now open" src="https://img.shields.io/badge/free%20trial-now%20open%20%E2%98%95-2448D8?style=for-the-badge"></a>
  <img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-4A2F20?style=for-the-badge">
  <img alt="About $1 a report" src="https://img.shields.io/badge/about-%241%20a%20report-B9814F?style=for-the-badge">
</p>

<h3 align="center">Less searching. More time to sip your coffee.</h3>

<br>

Hi, I'm **Méline**: a brand marketer, not a developer. 👋

Every morning I asked myself the same three questions. *What's trending? What are my competitors up to? What
should we make next?* By 11:48 I had 47 tabs open, zero answers and a very cold latte.

So I opened a café. ☕

**The Insight Café** is a tiny AI research agency, drawn as an office, with seven specialists who are (obviously)
all named after drinks. They do the digging and serve you **one page**: the answer first, the proof right beside
it, and who should do what next. This is the **free trial**, so four of them are on shift.

<p align="center">
  <img src="docs/preview.gif" width="100%" alt="A peek inside The Insight Café">
  <br>
  <sub>🎬 <a href="https://github.com/melinenguyen/insight-cafe/releases/download/v0.1.0/the-insight-cafe-film.mp4">Watch the full one-minute film, with sound</a></sub>
</p>

## 🥐 Meet the crew

<img src="docs/crew.png" width="100%" alt="The crew: Espresso, Chai, Matcha and Coca on shift; Mocha, Latte and Tonic in the full café">

## 🍽️ What lands on your table

<img src="docs/table.png" width="100%" alt="A trend radar, a competitor watch, scored opportunities and a one-page summary">
<sub>Shown with the full café's social scouts switched on. The trial reads the news, search trends and the calendar.</sub>

Proof and pictures, never vibes:

- 📈 **Trends you can see.** What's rising in the news, in search and around the next holidays, with the stories to prove it.
- 👀 **Competitors, minus the midnight stalking.** What they launched and announced in the news this week, and what you can steal.
- 🎯 **A ranked to-do list.** Every idea scored on fit, momentum, reach, urgency and ease: *do it today*, *this week*, or *politely skip*.
- 📝 **One page.** The answer first, three findings, who does what. Then the best idea is written up as a ready-to-shoot brief: hooks, the plan, references.

Works for any brand, shop or service: skincare, bakeries, gyms, bookshops… If you have competitors and customers, you have a café.

## 🧾 Order in two lines

Got [Claude Code](https://claude.com/claude-code)? Paste these:

```
/plugin marketplace add melinenguyen/insight-cafe
/plugin install insight-cafe@insight-cafe
```

Then just say: **"Set up my Insight Café."**

Claude hands you a little form about your brand, sets up your café and pours your first report. It takes about fifteen
minutes to set up (a little longer if you love filling forms), and each report costs about $1 of Claude on your own
[Anthropic API key](https://console.anthropic.com/settings/keys).

<img src="docs/steps.png" width="100%" alt="1. Tell it about your brand. 2. Your café opens. 3. Sip and read.">

<details>
<summary><b>No Claude Code? Brew it by hand ☕</b></summary>
<br>

You'll need Python 3.10+ and an [Anthropic API key](https://console.anthropic.com/settings/keys).

1. [Download this repo](https://github.com/melinenguyen/insight-cafe/archive/refs/heads/main.zip) and unzip it.
2. Open `skills/insight-cafe/dashboard/index.html` in your browser. Fill in your brand (or press **Load the example**)
   and export `profile.json` into `skills/insight-cafe/`.
3. Set up your café:
   ```bash
   cd skills/insight-cafe
   python3 scripts/scaffold.py --profile profile.json --out ~/Desktop/my-insight-cafe
   ```
4. Paste your API key into `~/Desktop/my-insight-cafe/agency/.env`.
5. Brew your first report:
   ```bash
   cd ~/Desktop/my-insight-cafe
   python3 -m pip install -r agency/requirements.txt
   python3 -m agency.run
   ```

Your office opens in the browser. Run it again whenever you want a fresh pot. (`--scouts` peeks at what the crew
found without spending anything; `--rebuild` redraws the office.)

</details>

## 🔒 The full café (coming soon)

Three rooms are already furnished. They're just waiting for opening day.

<img src="docs/locked.png" width="100%" alt="Mocha's ad studio, Latte's customer voice and Tonic's Slack hand-over, locked">

| | ☕ Free trial | ✨ Full café |
|---|---|---|
| **The crew** | Espresso, Chai, Matcha, Coca | All seven, with **Mocha** (your competitors' ads, then yours) and **Latte** (every review, word for word) |
| **Ideas written up** | The best one | All of them, and **Tonic** slides each one into your team's Slack |
| **Learns your taste** | Not yet | A morning huddle: the crew asks you one question each and remembers your answers |
| **Where it looks** | News, search trends, the calendar, Pinterest | Plus Instagram, TikTok, YouTube, Reddit and a 24/7 ad spy |
| **When it works** | Whenever you press go | Around the clock, two reports a day, one private office for your whole team |

Want a seat on opening day? Follow me on TikTok [@himeline](https://www.tiktok.com/@himeline). ☕

## 🍵 Little FAQ

**Do I need to code?**
Nope. If you can copy and paste two lines, you can run a café.

**What does it cost?**
The café is free. Claude charges about $1 per report, billed to your own Anthropic account. No subscription, no
surprise bill from me.

**Is my brand info safe?**
Everything stays on your computer: your brand profile, your office and your API key.

**Will it post or DM anyone for me?**
Never. The crew only reads public stuff. It doesn't post, like, follow or slide into anyone's DMs.

**Can I make it speak Vietnamese?**
Yes. The setup form is in English and Vietnamese, and your reports can be written in whatever language your team
speaks.

## 🇻🇳 Cho các bác người Việt

The Insight Café là một agency nghiên cứu AI tí hon, được vẽ thành văn phòng với 7 "nhân viên" tên đồ uống. Mỗi
sáng chỉ cần một trang: đang trend gì, đối thủ làm gì, nên làm gì trước, ai làm. Bản dùng thử miễn phí có 4 bạn
đi làm (Espresso, Chai, Matcha, Coca), chạy ngay trên máy các bác. Form thiết lập có tiếng Việt: chọn **VI** là xong.
Chúc các bác ít tab hơn, nhiều cà phê hơn ☕

<br>

<p align="center">
  <sub>Brewed with ☕ by <b>Méline Nguyen</b>, a marketing girlie who explores opportunities and builds brands she loves.<br>
  Follow me on TikTok <a href="https://www.tiktok.com/@himeline">@himeline</a> · The example brands are made up · Built with <a href="https://www.anthropic.com/claude">Claude</a> · <a href="LICENSE">License</a></sub>
</p>
