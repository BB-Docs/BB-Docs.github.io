#!/usr/bin/env bash
#
# audio-status — show which lessons have narration audio and which don't.
# Audio lives as MP3s on the 'audio' GitHub Release; this compares that list
# to the posts on the site.
#
#   audio-status                 # summary + the 12 most-recent lessons
#   audio-status --missing       # list every lesson still missing audio
#   audio-status --since 2026-08-01
#
set -uo pipefail
SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SITE_DIR"
REPO="BB-Docs/BB-Docs.github.io"

MODE="recent"; SINCE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --missing) MODE="missing" ;;
    --since)   MODE="since"; SINCE="$2"; shift ;;
    *) echo "usage: audio-status [--missing] [--since YYYY-MM-DD]" >&2; exit 2 ;;
  esac; shift
done

# Source of truth for "has narration" is the committed `audio: true` front-matter
# flag — it's what the site uses to render a player, and add-audio.sh stamps it
# only AFTER the MP3 is generated and uploaded. That avoids a race where re-reading
# the release listing lags a just-finished publish and reports a false "missing".
flagged() { grep -qE '^audio:[[:space:]]*true' "$1"; }

# The release asset list is fetched only as an integrity check (flag set but MP3
# actually absent = a broken player link).
have="$(gh release view audio --repo "$REPO" --json assets --jq '.assets[].name' 2>/dev/null | sed 's/\.mp3$//' | sort)"

total=0; withaudio=0; broken=""
posts="$(git ls-files _posts | sort)"
while IFS= read -r f; do
  total=$((total+1))
  if flagged "$f"; then
    withaudio=$((withaudio+1))
    b="$(basename "$f" .md)"
    grep -qx "$b" <<<"$have" || broken="$broken$b\n"
  fi
done <<<"$posts"

printf "\033[1mAudio:\033[0m %d of %d lessons have narration (%d missing)\n\n" "$withaudio" "$total" "$((total-withaudio))"

if [ -n "$broken" ]; then
  printf "\033[1;33m⚠ flag set but MP3 not on release (broken player):\033[0m\n"
  printf "$broken" | sed 's/^/  /'
  echo
fi

show() {  # print ✓/✗ for a post path
  if flagged "$1"; then printf "  \033[1;32m✓\033[0m %s\n" "$(basename "$1" .md)"
  else printf "  \033[1;31m✗\033[0m %s\n" "$(basename "$1" .md)"; fi
}

case "$MODE" in
  recent)  echo "12 most-recent lessons:"; echo "$posts" | tail -12 | while IFS= read -r f; do show "$f"; done ;;
  missing) echo "Lessons still missing audio:"
           echo "$posts" | while IFS= read -r f; do flagged "$f" || printf "  \033[1;31m✗\033[0m %s\n" "$(basename "$f" .md)"; done ;;
  since)   echo "Lessons since $SINCE:"
           echo "$posts" | while IFS= read -r f; do [[ "$(basename "$f"|cut -c1-10)" > "$SINCE" || "$(basename "$f"|cut -c1-10)" == "$SINCE" ]] && show "$f"; done ;;
esac