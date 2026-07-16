#!/usr/bin/env python3
"""Backfill the Telegram channel with every lesson on the site, oldest first.

Posts SILENTLY (disable_notification) so existing members aren't hit with a
burst of notifications, and throttles under Telegram's ~20 msg/min per-chat
limit, honouring 429 retry_after if it still trips.

  seed-telegram.py --dry-run     # show what would be posted, in order
  seed-telegram.py               # actually post
"""
import glob
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = "https://bb-docs.github.io"
DELAY = 4.0          # seconds between posts (~15/min, under the ~20/min cap)
# Trust the same CA bundle curl uses (this environment proxies TLS).
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")


def env():
    cfg = {}
    with open(os.path.join(SITE, "_tools", "lesson.env"), encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r'\s*(\w+)="([^"]*)"', line)
            if m:
                cfg[m.group(1)] = m.group(2)
    return cfg["TELEGRAM_BOT_TOKEN"], cfg["TELEGRAM_CHAT_ID"]


def lessons():
    """Oldest first. Skips '-2' slugs: those are collision-suffixed copies of a
    lesson that exists twice in Drive, so posting them repeats a title."""
    out = []
    for p in sorted(glob.glob(os.path.join(SITE, "_posts", "*.md"))):   # date asc
        base = os.path.basename(p)[:-3]
        if base.endswith("-2"):
            print(f"  – skipping duplicate: {base}")
            continue
        src = open(p, encoding="utf-8").read()
        m = re.search(r'^title:\s*"?(.*?)"?\s*$', src, re.M)
        title = m.group(1) if m else base
        url = f"{SITE_URL}/lessons/{base[0:4]}/{base[5:7]}/{base[8:10]}/{base[11:]}/"
        out.append((base[:10], title, url))
    return out


def post(token, chat, text):
    data = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "disable_notification": "true",
    }).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    try:
        return json.load(urllib.request.urlopen(req, context=CTX, timeout=30))
    except urllib.error.HTTPError as e:
        return json.load(e)


def main():
    dry = "--dry-run" in sys.argv
    token, chat = env()
    items = lessons()
    print(f"{len(items)} lessons, oldest first -> {chat}"
          f"{'  (DRY RUN)' if dry else '  (silent posts)'}\n")
    sent = 0
    for i, (date, title, url) in enumerate(items, 1):
        text = f"📘 {title}\n{url}"
        if dry:
            print(f"  {i:2}. {date}  {title[:58]}")
            continue
        r = post(token, chat, text)
        if not r.get("ok") and r.get("error_code") == 429:
            wait = r.get("parameters", {}).get("retry_after", 30)
            print(f"  rate-limited; waiting {wait}s…")
            time.sleep(wait + 1)
            r = post(token, chat, text)
        if r.get("ok"):
            sent += 1
            print(f"  ✓ {i:2}/{len(items)}  {date}  {title[:52]}")
        else:
            print(f"  ✗ {i:2}/{len(items)}  {date}  {r.get('description')}")
        if i < len(items):
            time.sleep(DELAY)
    if not dry:
        print(f"\nposted {sent}/{len(items)}")


if __name__ == "__main__":
    main()
