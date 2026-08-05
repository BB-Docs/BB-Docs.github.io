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

have="$(gh release view audio --repo "$REPO" --json assets --jq '.assets[].name' 2>/dev/null | sed 's/\.mp3$//' | sort)"
total=0; withaudio=0
posts="$(git ls-files _posts | sort)"
while IFS= read -r f; do
  total=$((total+1))
  grep -qx "$(basename "$f" .md)" <<<"$have" && withaudio=$((withaudio+1))
done <<<"$posts"

printf "\033[1mAudio:\033[0m %d of %d lessons have narration (%d missing)\n\n" "$withaudio" "$total" "$((total-withaudio))"

show() {  # print ✓/✗ for a post path
  local b; b="$(basename "$1" .md)"
  if grep -qx "$b" <<<"$have"; then printf "  \033[1;32m✓\033[0m %s\n" "$b"
  else printf "  \033[1;31m✗\033[0m %s\n" "$b"; fi
}

case "$MODE" in
  recent)  echo "12 most-recent lessons:"; echo "$posts" | tail -12 | while IFS= read -r f; do show "$f"; done ;;
  missing) echo "Lessons still missing audio:"
           echo "$posts" | while IFS= read -r f; do grep -qx "$(basename "$f" .md)" <<<"$have" || printf "  \033[1;31m✗\033[0m %s\n" "$(basename "$f" .md)"; done ;;
  since)   echo "Lessons since $SINCE:"
           echo "$posts" | while IFS= read -r f; do [[ "$(basename "$f"|cut -c1-10)" > "$SINCE" || "$(basename "$f"|cut -c1-10)" == "$SINCE" ]] && show "$f"; done ;;
esac