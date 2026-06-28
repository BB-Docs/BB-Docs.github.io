#!/usr/bin/env bash
#
# publish-lesson — pull the newest lesson .md from a Google Drive folder,
# convert it to a Jekyll post, and push it live to GitHub Pages.
#
# Usage:
#   publish-lesson                 # newest .md from the configured Drive folder
#   publish-lesson path/to.md      # convert a local file instead of Drive
#   publish-lesson --no-verify     # skip waiting for the Pages build
#
# One-time setup: see _tools/lesson.env.example and run `rclone config` once.
#
set -euo pipefail

SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ---- config (defaults; override in _tools/lesson.env) ----
RCLONE_REMOTE="gdrive"          # name of the rclone remote you created
DRIVE_FOLDER_ID=""              # ID of the shared Drive folder holding lessons
REPO="BB-Docs/BB-Docs.github.io"
SITE_URL="https://bb-docs.github.io"
GIT_NAME="pradeepcb"
GIT_EMAIL="pradeepcb@gmail.com"
# shellcheck disable=SC1091
[ -f "$SITE_DIR/_tools/lesson.env" ] && source "$SITE_DIR/_tools/lesson.env"

VERIFY=1
LOCAL_FILE=""
for arg in "$@"; do
  case "$arg" in
    --no-verify) VERIFY=0 ;;
    *.md)        LOCAL_FILE="$arg" ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

say() { printf "\033[1;34m▸\033[0m %s\n" "$*"; }
die() { printf "\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---- 1. get the source markdown ----
if [ -n "$LOCAL_FILE" ]; then
  [ -f "$LOCAL_FILE" ] || die "File not found: $LOCAL_FILE"
  SRC="$LOCAL_FILE"
  say "Using local file: $(basename "$SRC")"
else
  command -v rclone >/dev/null || die "rclone not installed (brew install rclone)"
  [ -n "$DRIVE_FOLDER_ID" ] || die "DRIVE_FOLDER_ID not set — see _tools/lesson.env.example"
  say "Finding newest .md in Drive folder…"
  NEWEST="$(rclone lsf "${RCLONE_REMOTE}:" \
      --drive-root-folder-id "$DRIVE_FOLDER_ID" \
      --files-only --include "*.md" --format "tp" --separator $'\t' \
      | sort -r | head -1 | cut -f2-)"
  [ -n "$NEWEST" ] || die "No .md files found in the Drive folder."
  say "Newest: $NEWEST"
  rclone copyto "${RCLONE_REMOTE}:${NEWEST}" "$TMP/$NEWEST" \
      --drive-root-folder-id "$DRIVE_FOLDER_ID"
  SRC="$TMP/$NEWEST"
fi

# ---- 2. convert to a Jekyll post ----
say "Converting…"
POST="$(cd "$SITE_DIR" && python3 _tools/convert.py "$SRC")"
[ -f "$SITE_DIR/$POST" ] || die "Conversion failed (no post written)."
say "Wrote $POST"

# Compute the live URL from the post filename: _posts/YYYY-MM-DD-slug.md
base="$(basename "$POST" .md)"
y="${base:0:4}"; mo="${base:5:2}"; d="${base:8:2}"; slug="${base:11}"
LESSON_URL="${SITE_URL}/lessons/${y}/${mo}/${d}/${slug}/"

# ---- 3. commit & push ----
cd "$SITE_DIR"
if git diff --quiet --exit-code -- "$POST" && ! git status --porcelain | grep -q "$POST"; then
  say "No changes (lesson already published) — nothing to push."
  exit 0
fi
say "Committing & pushing…"
git pull --rebase --quiet origin main || true
git add "$POST"
git -c user.name="$GIT_NAME" -c user.email="$GIT_EMAIL" \
    commit -qm "Add lesson: $base"
git push -q origin main
say "Pushed."

# ---- 4. wait for the Pages build & verify ----
if [ "$VERIFY" -eq 0 ]; then
  say "Skipping verify. Site rebuilds in ~1 min: $LESSON_URL"
  exit 0
fi
HEAD="$(git rev-parse HEAD)"
say "Waiting for the Pages build of THIS commit…"
for i in $(seq 1 30); do
  info="$(gh api "repos/${REPO}/pages/builds/latest" --jq '.status+" "+(.commit // "-")' 2>/dev/null || echo '? -')"
  st="${info%% *}"; sha="${info##* }"
  if [ "$sha" = "$HEAD" ]; then
    [ "$st" = "built" ]   && break
    [ "$st" = "errored" ] && die "Pages build errored: $(gh api "repos/${REPO}/pages/builds/latest" --jq '.error.message')"
  fi
  sleep 12
done

# The page can lag a few seconds behind a "built" status (CDN) — poll for it.
say "Checking the live page…"
code="000"
for i in $(seq 1 15); do
  code="$(curl -s -o "$TMP/live.html" -w '%{http_code}' "$LESSON_URL")"
  [ "$code" = "200" ] && break
  sleep 8
done
leftover="$(grep -c '!!!' "$TMP/live.html" 2>/dev/null || true)"
if [ "$code" = "200" ] && [ "${leftover:-0}" = "0" ]; then
  printf "\033[1;32m✓ Live:\033[0m %s\n" "$LESSON_URL"
else
  die "Verify failed (HTTP $code, leftover '!!!' markers: ${leftover:-?}): $LESSON_URL"
fi
