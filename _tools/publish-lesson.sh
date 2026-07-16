#!/usr/bin/env bash
#
# publish-lesson — sync lesson .md files from a Google Drive folder to the
# Jekyll site. Converts every .md, publishes any post that is NEW or CHANGED
# (deterministic slugs => no duplicates), pushes, and verifies the live pages.
#
# If two source files resolve to the SAME slug+date (a genuine collision), the
# "primary" file keeps the clean slug and the other(s) get a suffix derived
# from a session marker in the filename (workshop/pm/afternoon/evening) or -2,
# so no lesson is ever silently overwritten. Never deletes posts whose source
# disappears (pruning stays manual).
#
# Usage:
#   publish-lesson                 # sync ALL .md from the Drive folder
#   publish-lesson path/to.md      # sync a single local file
#   publish-lesson --dry-run       # show what would change; no commit/push
#   publish-lesson --no-verify     # push without waiting for the Pages build
#
set -euo pipefail

SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---- config (defaults; override in _tools/lesson.env) ----
RCLONE_REMOTE="gdrive"
DRIVE_FOLDER_ID=""
DRIVE_SUBDIR="MkDocs"          # subfolder (within the shared folder) holding lesson .md files; "" = root
REPO="BB-Docs/BB-Docs.github.io"
SITE_URL="https://bb-docs.github.io"
GIT_NAME="pradeepcb"
GIT_EMAIL="pradeepcb@gmail.com"
# Telegram auto-post (optional). Set both in _tools/lesson.env to enable.
TELEGRAM_BOT_TOKEN=""          # from @BotFather
TELEGRAM_CHAT_ID=""            # e.g. @your_channel  (bot must be a channel admin)
# shellcheck disable=SC1091
[ -f "$SITE_DIR/_tools/lesson.env" ] && source "$SITE_DIR/_tools/lesson.env"

VERIFY=1; DRYRUN=0; REBUILD=0; LOCAL_FILE=""
for arg in "$@"; do
  case "$arg" in
    --no-verify) VERIFY=0 ;;
    --dry-run)   DRYRUN=1 ;;
    --rebuild)   REBUILD=1 ;;
    *.md)        LOCAL_FILE="$arg" ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

say()  { printf "\033[1;34m▸\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }

# A filename carries a "secondary session" marker => not the primary of a clash.
has_qual() {
  case "$(basename "$1" | tr '[:upper:]' '[:lower:]')" in
    *workshop*|*-pm*|*_pm*|*afternoon*|*evening*) return 0 ;;
    *) return 1 ;;
  esac
}
# Suffix to disambiguate a colliding slug, from the filename's session marker.
qualifier() {
  case "$(basename "$1" | tr '[:upper:]' '[:lower:]')" in
    *workshop*)          echo "workshop" ;;
    *-pm*|*_pm*|*\ pm*)  echo "pm" ;;
    *afternoon*)         echo "afternoon" ;;
    *evening*)           echo "evening" ;;
    *)                   echo "2" ;;
  esac
}

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
SRC="$TMP/src"; STAGE="$TMP/stage"; mkdir -p "$SRC" "$STAGE"

# ---- 1. gather source markdown ----
if [ -n "$LOCAL_FILE" ]; then
  [ -f "$LOCAL_FILE" ] || die "File not found: $LOCAL_FILE"
  cp "$LOCAL_FILE" "$SRC/"
  say "Source: local file $(basename "$LOCAL_FILE")"
else
  command -v rclone >/dev/null || die "rclone not installed (brew install rclone)"
  [ -n "$DRIVE_FOLDER_ID" ] || die "DRIVE_FOLDER_ID not set — see _tools/lesson.env.example"
  say "Syncing .md files from the Drive folder (${DRIVE_SUBDIR:-root})…"
  rclone copy "${RCLONE_REMOTE}:${DRIVE_SUBDIR}" --drive-root-folder-id "$DRIVE_FOLDER_ID" \
      --max-depth 1 --include "*.md" "$SRC" || die "rclone copy failed"
fi

count="$(find "$SRC" -name '*.md' | wc -l | tr -d ' ')"
[ "$count" -gt 0 ] || die "No .md files found."
say "Scanning $count source file(s)…"

# ---- 2. convert each into its own staging dir (unique paths) ----
cd "$SITE_DIR"
if [ "$REBUILD" -eq 1 ] && [ -z "$LOCAL_FILE" ]; then
  say "Rebuild: clearing all existing posts (recreated from Drive below)…"
  find _posts -maxdepth 1 -name '*.md' -delete
fi
idx=0
while IFS= read -r src; do
  # Companion vocabulary/glossary files are reference material, not lessons.
  case "$(basename "$src" | tr '[:upper:]' '[:lower:]')" in
    *vocabulary*|*glossary*)
      say "Skipping companion (not a lesson): $(basename "$src")"; continue ;;
  esac
  d="$STAGE/$idx"; mkdir -p "$d"
  if ! POST="$(python3 _tools/convert.py "$src" --posts-dir "$d" 2>"$TMP/err")"; then
    warn "Skipped $(basename "$src"): $(tr '\n' ' ' < "$TMP/err")"; continue
  fi
  B_BASE[$idx]="$(basename "$POST")"; B_STAGE[$idx]="$POST"; B_SRC[$idx]="$src"
  idx=$((idx + 1))
done < <(find "$SRC" -name '*.md' | sort)
N=$idx
[ "$N" -gt 0 ] || die "No convertible .md files."

# ---- 3. assign final slugs (primaries first so they keep the clean slug) ----
order=""
for ((k = 0; k < N; k++)); do has_qual "${B_SRC[$k]}" || order="$order $k"; done
for ((k = 0; k < N; k++)); do has_qual "${B_SRC[$k]}" && order="$order $k"; done

claimed=""
CHG_TAG=(); CHG_FINAL=(); CHG_STAGE=()
for k in $order; do
  base="${B_BASE[$k]}"; stage="${B_STAGE[$k]}"; src="${B_SRC[$k]}"
  final="$base"
  if printf ' %s ' $claimed | grep -qF " $final "; then
    sfx="$(qualifier "$src")"; final="${base%.md}-$sfx.md"; n=2
    while printf ' %s ' $claimed | grep -qF " $final "; do
      final="${base%.md}-$sfx-$n.md"; n=$((n + 1))
    done
    warn "Slug collision on ${base%.md} — publishing $(basename "$src") as ${final%.md}"
  fi
  claimed="$claimed $final"
  if [ ! -f "_posts/$final" ]; then
    CHG_TAG+=("N"); CHG_FINAL+=("$final"); CHG_STAGE+=("$stage")
  elif ! cmp -s "$stage" "_posts/$final"; then
    CHG_TAG+=("U"); CHG_FINAL+=("$final"); CHG_STAGE+=("$stage")
  fi
done

M=${#CHG_FINAL[@]}
if [ "$M" -eq 0 ]; then
  say "Everything is already up to date — nothing to publish."
  exit 0
fi

nnew=0; nupd=0
for ((j = 0; j < M; j++)); do
  if [ "${CHG_TAG[$j]}" = "N" ]; then
    nnew=$((nnew + 1)); printf "  \033[1;32mnew\033[0m      %s\n" "${CHG_FINAL[$j]}"
  else
    nupd=$((nupd + 1)); printf "  \033[1;33mupdated\033[0m  %s\n" "${CHG_FINAL[$j]}"
  fi
done
say "$nnew new, $nupd updated."

if [ "$DRYRUN" -eq 1 ]; then
  say "Dry run — no changes written. Re-run without --dry-run to publish."
  exit 0
fi

# ---- 4. apply, commit & push ----
for ((j = 0; j < M; j++)); do cp "${CHG_STAGE[$j]}" "_posts/${CHG_FINAL[$j]}"; done
say "Committing & pushing…"
git add -A _posts
if git diff --cached --quiet -- _posts; then
  say "No net changes — the site already matches Drive exactly."
  exit 0
fi
msg="Publish lessons: $nnew new, $nupd updated"
[ "$REBUILD" -eq 1 ] && msg="Rebuild all lessons from Drive ($M posts)"
git -c user.name="$GIT_NAME" -c user.email="$GIT_EMAIL" commit -qm "$msg"
git pull --rebase --quiet origin main || true   # replay our commit on any remote changes
git push -q origin main
say "Pushed."

# ---- 5. verify ----
url_for() { local b="${1%.md}"; printf "%s/lessons/%s/%s/%s/%s/" \
            "$SITE_URL" "${b:0:4}" "${b:5:2}" "${b:8:2}" "${b:11}"; }

# Post the message to a Telegram channel (no-op unless token + chat id are set).
telegram_notify() {
  [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ] || return 0
  local code
  code="$(curl -s -o "$TMP/tg.json" -w '%{http_code}' \
      -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=$1" || echo 000)"
  if [ "$code" = "200" ]; then
    printf "\033[1;32m   ✓ posted to Telegram\033[0m\n"
  else
    warn "Telegram post failed (HTTP $code): $(tr -d '\n' < "$TMP/tg.json" | cut -c1-200)"
  fi
}

# Print + copy a paste-ready share message, and auto-post it to Telegram.
share_message() {
  local newest="" f title url msg
  for ((f = 0; f < M; f++)); do
    if [ -z "$newest" ] || [[ "${CHG_FINAL[$f]}" > "$newest" ]]; then newest="${CHG_FINAL[$f]}"; fi
  done
  [ -n "$newest" ] || return 0
  title="$(grep -m1 '^title:' "_posts/$newest" | sed -e 's/^title:[[:space:]]*//' -e 's/^"//' -e 's/"$//')"
  url="$(url_for "$newest")"
  msg="📘 ${title}
${url}"
  printf "\n\033[1;36m📣 Share message (newest lesson):\033[0m\n%s\n" "$msg"
  if command -v pbcopy >/dev/null 2>&1; then
    printf '%s' "$msg" | pbcopy
    printf "\033[0;36m   ✓ copied to clipboard — paste into your WhatsApp Channel\033[0m\n"
  fi
  telegram_notify "$msg"
}

if [ "$VERIFY" -eq 0 ]; then
  say "Skipping verify. Rebuilds in ~1 min:"
  for ((j = 0; j < M; j++)); do echo "   $(url_for "${CHG_FINAL[$j]}")"; done
  share_message
  exit 0
fi

HEAD="$(git rev-parse HEAD)"
say "Waiting for the Pages build of this commit…"
for i in $(seq 1 30); do
  info="$(gh api "repos/${REPO}/pages/builds/latest" --jq '.status+" "+(.commit // "-")' 2>/dev/null || echo '? -')"
  st="${info%% *}"; sha="${info##* }"
  if [ "$sha" = "$HEAD" ]; then
    [ "$st" = "built" ]   && break
    [ "$st" = "errored" ] && die "Pages build errored: $(gh api "repos/${REPO}/pages/builds/latest" --jq '.error.message')"
  fi
  sleep 12
done

say "Checking live pages…"
ok=1
for ((j = 0; j < M; j++)); do
  u="$(url_for "${CHG_FINAL[$j]}")"; code="000"
  for i in $(seq 1 15); do
    code="$(curl -s -o "$TMP/live.html" -w '%{http_code}' "$u")"
    [ "$code" = "200" ] && break
    sleep 8
  done
  leftover="$(grep -c '!!!' "$TMP/live.html" 2>/dev/null || true)"
  if [ "$code" = "200" ] && [ "${leftover:-0}" = "0" ]; then
    printf "\033[1;32m  ✓\033[0m %s\n" "$u"
  else
    printf "\033[1;31m  ✗ (HTTP %s, leftover '!!!': %s)\033[0m %s\n" "$code" "${leftover:-?}" "$u"; ok=0
  fi
done
[ "$ok" -eq 1 ] && printf "\033[1;32m✓ All published lessons are live.\033[0m\n" \
                || die "Some lessons failed verification."
share_message
