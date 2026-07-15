#!/usr/bin/env python3
"""
Hack monitor: polls exploit feeds, sends a Telegram alert on each NEW incident.
State is kept in seen.json (committed back to the repo by the workflow).

Env / GitHub Secrets:
  TG_BOT_TOKEN       (required)  Telegram bot token from @BotFather
  TG_CHAT_ID         (required)  your Telegram chat id (from @userinfobot)
  CRYPTOPANIC_TOKEN  (optional)  free CryptoPanic API token -> faster news coverage
"""
import os, json, time, hashlib, urllib.request, urllib.parse

TG_TOKEN  = os.environ.get("TG_API_KEY") or os.environ["TG_BOT_TOKEN"]  # accepts either secret name
TG_CHAT   = os.environ["TG_CHAT_ID"]
SEEN_FILE = "seen.json"
RECENT_DAYS = 7                    # only alert on incidents dated within this window
UA = {"User-Agent": "Mozilla/5.0 (hack-monitor)"}

def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

def tg_send(text):
    data = urllib.parse.urlencode({
        "chat_id": TG_CHAT, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=data)
    urllib.request.urlopen(req, timeout=30).read()

# ---------- sources: each returns [{id, title, url, ts}] ----------
def src_defillama():
    out = []
    for h in http_json("https://api.llama.fi/hacks"):
        ts = int(h.get("date") or 0)
        name = h.get("name", "?")
        amt = h.get("amount")
        amt_s = f"${amt:,.0f}" if isinstance(amt, (int, float)) else "?"
        chains = ",".join(h.get("chain") or [])
        tech = h.get("technique") or h.get("classification") or ""
        title = f"\U0001F6A8 <b>{name}</b> — {amt_s}\nChain: {chains}\n{tech}\n(source: DefiLlama)"
        hid = "defillama:" + hashlib.md5(f"{name}|{ts}".encode()).hexdigest()[:12]
        out.append({"id": hid, "title": title, "url": "https://defillama.com/hacks", "ts": ts})
    return out

def src_cryptopanic():
    tok = os.environ.get("CRYPTOPANIC_TOKEN")
    if not tok:
        return []
    data = http_json(f"https://cryptopanic.com/api/v1/posts/?auth_token={tok}&public=true&kind=news")
    KW = ("hack", "exploit", "drain", "stolen", "rekt", "attack", "vulnerab", "breach", "exploited")
    out = []
    for p in data.get("results", []):
        title = p.get("title", "")
        if not any(k in title.lower() for k in KW):
            continue
        try:
            ts = int(time.mktime(time.strptime(p["published_at"][:19], "%Y-%m-%dT%H:%M:%S")))
        except Exception:
            ts = int(time.time())
        out.append({"id": "cp:" + str(p.get("id")),
                    "title": f"\U0001F4F0 {title}\n(source: CryptoPanic news)",
                    "url": p.get("url", ""), "ts": ts})
    return out

# add more source functions here (e.g. an X/Twitter source once you have API access)
SOURCES = [src_defillama, src_cryptopanic]

def main():
    cutoff = time.time() - RECENT_DAYS * 86400
    items = []
    for fn in SOURCES:
        try:
            items += fn()
        except Exception as e:
            print("source error:", fn.__name__, e)

    first_run = not os.path.exists(SEEN_FILE)
    seen = set() if first_run else set(json.load(open(SEEN_FILE)))

    if first_run:
        # seed state so we don't blast every historical incident on the first run
        for i in items:
            seen.add(i["id"])
        json.dump(sorted(seen), open(SEEN_FILE, "w"))
        try:
            tg_send("✅ Hack monitor is live. You'll get an alert on each new incident.")
        except Exception as e:
            print("tg start error:", e)
        print("seeded", len(seen), "ids")
        return

    new = [i for i in items if i["ts"] >= cutoff and i["id"] not in seen]
    for i in sorted(new, key=lambda x: x["ts"]):
        try:
            tg_send(i["title"] + (f"\n{i['url']}" if i["url"] else ""))
            print("alerted:", i["id"])
            time.sleep(1)
        except Exception as e:
            print("tg error:", e)

    # mark ALL current ids seen so future backfills of old entries don't re-alert
    for i in items:
        seen.add(i["id"])
    json.dump(sorted(seen), open(SEEN_FILE, "w"))
    print("done. new alerts:", len(new))

if __name__ == "__main__":
    main()
