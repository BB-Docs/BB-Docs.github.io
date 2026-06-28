#!/usr/bin/env bash
#
# publish-lesson — sync lesson .md files from a Google Drive folder to the
# Jekyll site. Converts every .md, publishes any that are NEW or CHANGED
# (deterministic slugs => no duplicates), pushes, and verifies the live pages.
# Never deletes posts whose source disappears (pruning stays manual).
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
REPO="BB-Docs/BB-Docs.github.io"
SITE_URL="https://bb-docs.github.io"
GIT_NAME="pradeepcb"
GIT_EMAIL="pradeepcb@gmail.com"
# shellcheck disable=SC1091
[ -f "$SITE_DIR/_tools/lesson.env" ] && source "$SITE_DIR/_tools/lesson.env"

VERIFY=1; DRYRUN=0; LOCAL_FILE=""
for arg in "$@"; do
  case "$arg" in
    --no-verify) VERIFY=0 ;;
    --dry-run)   DRYRUN=1 ;;
    *.md)        LOCAL_FILE="$arg" ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

say()  { printf "\033[1;34m▸\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }
die()  { printf "\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }

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
  say "Syncing .md files from the Drive folder…"
  rclone copy "${RCLONE_REMOTE}:" --drive-root-folder-id "$DRIVE_FOLDER_ID" \
      --include "*.md" "$SRC" || die "rclone copy failed"
fi

count="$(find "$SRC" -name '*.md' | wc -l | tr -d ' ')"
[ "$count" -gt 0 ] || die "No .md files found."
say "Scanning $count source file(s)…"

# ---- 2. convert each and diff against _posts (no writes yet) ----
cd "$SITE_DIR"
CHANGED=()   # entries: "N <basename>" (new) or "U <basename>" (updated)
while IFS= read -r src; do
  if ! POST="$(python3 _tools/convert.py "$src" --posts-dir "$STAGE" 2>"$TMP/err")"; then
    warn "Skipped $(basename "$src"): $(tr '\n' ' ' < "$TMP/err")"
    continue
  fi
  base="$(basename "$POST")"
  if [ ! -f "_posts/$base" ]; then
    CHANGED+=("N $base")
  elif ! cmp -s "$POST" "_posts/$base"; then
    CHANGED+=("U $base")
  fi
done < <(find "$SRC" -name '*.md' | sort)

if [ "${#CHANGED[@]}" -eq 0 ]; then
  say "Everything is already up to date — nothing to publish."
  exit 0
fi

nnew=0; nupd=0
for e in "${CHANGED[@]}"; do
  tag="${e%% *}"; base="${e#* }"
  if [ "$tag" = "N" ]; then nnew=$((nnew+1)); printf "  \033[1;32mnew\033[0m      %s\n" "$base"
  else                      nupd=$((nupd+1)); printf "  \033[1;33mupdated\033[0m  %s\n" "$base"; fi
done
say "$nnew new, $nupd updated."

if [ "$DRYRUN" -eq 1 ]; then
  say "Dry run — no changes written. Re-run without --dry-run to publish."
  exit 0
fi

# ---- 3. apply, commit & push ----
for e in "${CHANGED[@]}"; do base="${e#* }"; cp "$STAGE/$base" "_posts/$base"; done
say "Committing & pushing…"
git add _posts
git -c user.name="$GIT_NAME" -c user.email="$GIT_EMAIL" \
    commit -qm "Publish lessons: $nnew new, $nupd updated"
git pull --rebase --quiet origin main || true   # replay our commit on any remote changes
git push -q origin main
say "Pushed."

# ---- 4. verify ----
url_for() { local b="${1%.md}"; printf "%s/lessons/%s/%s/%s/%s/" \
            "$SITE_URL" "${b:0:4}" "${b:5:2}" "${b:8:2}" "${b:11}"; }

if [ "$VERIFY" -eq 0 ]; then
  say "Skipping verify. Rebuilds in ~1 min:"
  for e in "${CHANGED[@]}"; do echo "   $(url_for "${e#* }")"; done
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
for e in "${CHANGED[@]}"; do
  u="$(url_for "${e#* }")"; code="000"
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
