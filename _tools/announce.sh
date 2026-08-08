#!/usr/bin/env bash
#
# announce — post new lessons to the Telegram channel AFTER their pages are
# live, so Telegram fetches a proper link-preview card. Run DETACHED by
# publish-lesson (survives closing the window and a slow/flaky deploy).
#
#   announce <post-basename> [<post-basename> …]   # basenames without .md
#
set -uo pipefail
SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SITE_DIR"

SITE_URL="https://bb-docs.github.io"
TELEGRAM_BOT_TOKEN=""; TELEGRAM_CHAT_ID=""
# shellcheck disable=SC1091
[ -f _tools/lesson.env ] && source _tools/lesson.env
[ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ] || exit 0

url_for() { local b="$1"; printf "%s/lessons/%s/%s/%s/%s/" \
            "$SITE_URL" "${b:0:4}" "${b:5:2}" "${b:8:2}" "${b:11}"; }

for b in "$@"; do
  url="$(url_for "$b")"
  # Wait (up to ~6 min) for the page to deploy so the preview card is populated;
  # post anyway if it never comes up (better a cardless post than none).
  for _ in $(seq 1 45); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' "$url")" = "200" ] && break
    sleep 8
  done
  title="$(grep -m1 '^title:' "_posts/$b.md" | sed -e 's/^title:[[:space:]]*//' -e 's/^"//' -e 's/"$//')"
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=📘 ${title}
${url}" >/dev/null
  sleep 4          # stay under Telegram's ~20 msg/min per-chat cap
done
