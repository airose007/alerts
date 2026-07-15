# hack-monitor

Polls DeFi exploit feeds every ~10 min via GitHub Actions and sends a **Telegram alert** for each new
incident. Free to run. No server needed.

## Sources
- **DefiLlama** hacks API (`api.llama.fi/hacks`) — reliable, curated hours-to-days after the event; has the $ amount.
- **rekt.news** RSS — one post per major hack, with the writeup.
- **Cointelegraph** hacks RSS (`/tag/hacks`) — fast crypto-press coverage of incidents.
- **CryptoPanic** news (optional, needs a free token) — extra news feed, keyword-filtered (`hack/exploit/drained/...`).

Each source is deduped independently, so the same incident from two feeds only alerts once per feed.

> Latency reality: the *fastest* reports are the security firms' X accounts (PeckShield, Cyvers, BlockSec),
> which need the paid X API or a bridge. These free sources are reliable but not sub-minute. See "Adding sources".

## One-time setup (~10 min)

1. **Create a Telegram bot**: message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the **bot token**.
2. **Get your chat id**: message [@userinfobot](https://t.me/userinfobot) → it replies with your numeric **Id**.
   Then send any message to your new bot once (so it's allowed to DM you).
3. **Create a PUBLIC GitHub repo** (public = unlimited free Actions minutes) and push these files:
   ```
   monitor.py
   .github/workflows/monitor.yml
   README.md
   ```
4. **Add repo secrets** (Settings → Secrets and variables → Actions → New repository secret):
   - `TG_BOT_TOKEN` = your bot token
   - `TG_CHAT_ID`   = your numeric chat id
   - `CRYPTOPANIC_TOKEN` = (optional) free token from cryptopanic.com/developers/api
5. **Enable Actions** (Actions tab → enable), then open the `hack-monitor` workflow → **Run workflow** once.
   - First run **seeds** state (marks current incidents as seen) and sends "✅ Hack monitor is live" — it does
     NOT blast historical hacks.
   - After that, every run alerts only on genuinely new incidents from the last 7 days.

That's it. It now runs every 10 minutes on its own.

## Adding sources (incl. real-time X)
Each source is a function in `monitor.py` returning `[{id, title, url, ts}]`. To add one, write a function
and append it to `SOURCES`. For real-time firm alerts:
- **X API** (basic tier ~$100/mo): pull recent tweets from `@PeckShieldAlert`, `@CyversAlerts`,
  `@BlockSecTeam`, filter for hack keywords, return them as items.
- Or a Twitter→Telegram bridge / RSS service if you prefer no code.

## Notes
- State lives in `seen.json`, kept in the **GitHub Actions cache** between runs (not committed to the repo, so
  there's no git-push race). It's `.gitignore`d. If you ever want a clean reseed, delete the cache under
  Actions → Caches, or just let it re-seed.
- Tune `RECENT_DAYS` (default 7) and the cron interval in `monitor.yml` to taste.
- Keep the repo public OR watch your Actions minutes on a private repo (a 10-min cron ≈ 4,300 min/mo).
