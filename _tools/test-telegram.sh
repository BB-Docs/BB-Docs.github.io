#!/usr/bin/env bash
#
# test-telegram.sh — verify the Telegram bot + channel wiring.
# Reads the token from _tools/lesson.env and never prints it.
#
#   bash _tools/test-telegram.sh          # check bot + channel + admin rights
#   bash _tools/test-telegram.sh --send   # also post a real test message
#
set -uo pipefail
SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TELEGRAM_BOT_TOKEN=""; TELEGRAM_CHAT_ID=""
# shellcheck disable=SC1091
[ -f "$SITE_DIR/_tools/lesson.env" ] && source "$SITE_DIR/_tools/lesson.env"

ok()   { printf "  \033[1;32m✓\033[0m %s\n" "$*"; }
bad()  { printf "  \033[1;31m✗\033[0m %s\n" "$*"; }
info() { printf "\033[1;34m▸\033[0m %s\n" "$*"; }

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}"

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  bad "TELEGRAM_BOT_TOKEN is empty in _tools/lesson.env — paste the @BotFather token there."
  exit 1
fi
if [ -z "$TELEGRAM_CHAT_ID" ]; then
  bad "TELEGRAM_CHAT_ID is empty — set it to \"@your_channel\" (public) or the numeric -100… id."
  exit 1
fi

# 1. Is the token valid?
info "Checking the bot token…"
if ! curl -s "$API/getMe" -o /tmp/tg_me.json; then bad "network error"; exit 1; fi
if [ "$(python3 -c 'import json;print(json.load(open("/tmp/tg_me.json"))["ok"])' 2>/dev/null)" != "True" ]; then
  bad "Token rejected: $(python3 -c 'import json;print(json.load(open("/tmp/tg_me.json")).get("description",""))' 2>/dev/null)"
  echo "     → Re-copy the token from @BotFather (format: 123456789:AA…)."
  exit 1
fi
ok "Bot: @$(python3 -c 'import json;print(json.load(open("/tmp/tg_me.json"))["result"]["username"])')"

# 2. Can the bot see the channel?
info "Checking the channel…"
curl -s "$API/getChat" --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" -o /tmp/tg_chat.json
if [ "$(python3 -c 'import json;print(json.load(open("/tmp/tg_chat.json"))["ok"])' 2>/dev/null)" != "True" ]; then
  bad "Can't read channel: $(python3 -c 'import json;print(json.load(open("/tmp/tg_chat.json")).get("description",""))' 2>/dev/null)"
  echo "     → Usually means the bot isn't an admin of the channel yet, or the chat id is wrong."
  echo "       Channel → Administrators → Add Admin → your bot → enable 'Post Messages'."
  exit 1
fi
ok "Channel: $(python3 -c 'import json;d=json.load(open("/tmp/tg_chat.json"))["result"];print(d.get("title",""), "(", d.get("type",""), ")")')"

# 3. Optionally post for real.
if [ "${1:-}" = "--send" ]; then
  info "Posting a test message…"
  code=$(curl -s -o /tmp/tg_send.json -w '%{http_code}' -X POST "$API/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=✅ Daily Lesson Notes is connected. Lessons will post here automatically.")
  if [ "$code" = "200" ]; then
    ok "Test message posted — check your channel."
  else
    bad "Send failed (HTTP $code): $(python3 -c 'import json;print(json.load(open("/tmp/tg_send.json")).get("description",""))' 2>/dev/null)"
    echo "     → The bot needs the 'Post Messages' admin right in the channel."
    exit 1
  fi
else
  echo
  info "Looks wired up. Run with --send to post a real test message."
fi
