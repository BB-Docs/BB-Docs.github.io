#!/usr/bin/env python3
"""Small Telegram channel helper for the lessons channel.

Reads the token from _tools/lesson.env (never prints it). Finds message ids by
lesson date via the channel's PUBLIC web preview (the Bot API can't list
history), and can delete or edit messages.

  telegram_util.py find   YYYY-MM-DD      # print message ids whose lesson URL is that date
  telegram_util.py delete <id> [<id>...]  # delete messages
  telegram_util.py edit   <id> <text>     # replace a message's text
"""
import html
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = ssl.create_default_context(cafile="/etc/ssl/cert.pem")   # this env proxies TLS


def env():
    cfg = {}
    with open(os.path.join(SITE, "_tools", "lesson.env"), encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r'\s*(\w+)="([^"]*)"', line)
            if m:
                cfg[m.group(1)] = m.group(2)
    return cfg["TELEGRAM_BOT_TOKEN"], cfg["TELEGRAM_CHAT_ID"]


def api(token, method, **params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data)
    try:
        return json.load(urllib.request.urlopen(req, context=CTX, timeout=30))
    except urllib.error.HTTPError as e:
        return json.load(e)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, context=CTX, timeout=30).read().decode("utf-8", "replace")


def all_posts(username):
    """Every (id, text) in the channel, via paged web preview. Oldest first."""
    seen, before = {}, ""
    for _ in range(50):                     # hard page cap
        url = f"https://t.me/s/{username}" + (f"?before={before}" if before else "")
        src = fetch(url)
        found = re.findall(
            r'data-post="' + re.escape(username) +
            r'/(\d+)".*?<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
            src, re.S)
        if not found:
            break
        new = False
        for pid, body in found:
            pid = int(pid)
            if pid not in seen:
                seen[pid] = re.sub(r'<[^>]+>', '', html.unescape(re.sub(r'<br\s*/?>', '\n', body)))
                new = True
        if not new:
            break
        before = min(int(p) for p, _ in found)
        if before <= 1:
            break
    return sorted(seen.items())


def main():
    token, chat = env()
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]

    if cmd == "find":
        date = sys.argv[2]                                  # YYYY-MM-DD
        path = "/lessons/" + date.replace("-", "/") + "/"
        user = chat.lstrip("@")
        ids = [str(pid) for pid, text in all_posts(user) if path in text]
        print(" ".join(ids))

    elif cmd == "delete":
        for mid in sys.argv[2:]:
            r = api(token, "deleteMessage", chat_id=chat, message_id=mid)
            print(f"  {'✓ deleted' if r.get('ok') else '✗'} {mid}"
                  + ("" if r.get("ok") else f": {r.get('description')}"))

    elif cmd == "edit":
        mid, text = sys.argv[2], sys.argv[3]
        r = api(token, "editMessageText", chat_id=chat, message_id=mid, text=text)
        print(f"  {'✓ edited' if r.get('ok') else '✗'} {mid}"
              + ("" if r.get("ok") else f": {r.get('description')}"))

    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
