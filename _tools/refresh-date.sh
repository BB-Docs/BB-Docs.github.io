#!/usr/bin/env bash
#
# refresh-date — delete and recreate all lessons for one date from Drive,
# and refresh that date's posts in the Telegram channel.
#
# For the given date it: records the current channel post(s), removes the
# date's posts from git, re-runs publish-lesson (which recreates them from
# Drive and announces the fresh ones), then deletes the old channel post(s).
# A lesson whose Drive source was removed simply disappears (nothing to recreate).
#
# Usage:
#   refresh-date 2026-07-22
#   refresh-date 2026-07-22 --no-telegram   # only refresh the website
#   refresh-date 2026-07-22 --dry-run        # show what would change; do nothing
#
set -euo pipefail
SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DATE=""; DRYRUN=0; TELEGRAM=1
for a in "$@"; do
  case "$a" in
    --dry-run)     DRYRUN=1 ;;
    --no-telegram) TELEGRAM=0 ;;
    [0-9]*-[0-9]*-[0-9]*) DATE="$a" ;;
    *) echo "Unknown argument: $a" >&2; exit 2 ;;
  esac
done
[[ "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || {
  echo "usage: refresh-date YYYY-MM-DD [--no-telegram] [--dry-run]" >&2; exit 2; }

say() { printf "\033[1;34m▸\033[0m %s\n" "$*"; }
cd "$SITE_DIR"

posts="$(git ls-files "_posts/${DATE}-"'*' || true)"
say "Refreshing $DATE"
if [ -n "$posts" ]; then
  echo "$posts" | sed 's|_posts/|   post: |'
else
  echo "   (no posts for $DATE currently in git — will publish if the source exists in Drive)"
fi

old_ids=""
if [ "$TELEGRAM" -eq 1 ]; then
  old_ids="$(python3 _tools/telegram_util.py find "$DATE" 2>/dev/null || true)"
  [ -n "$old_ids" ] && echo "   channel posts to replace: $old_ids" \
                    || echo "   channel posts to replace: (none found)"
fi

if [ "$DRYRUN" -eq 1 ]; then
  say "Dry run — nothing changed."
  exit 0
fi

# 1. remove the date's posts from git (skip the commit if there were none)
if [ -n "$posts" ]; then
  echo "$posts" | xargs git rm -q
  git -c user.name="pradeepcb" -c user.email="pradeepcb@gmail.com" \
      commit -qm "refresh $DATE: remove posts (recreated from Drive next)"
fi

# 2. recreate from Drive (+ announce the fresh post to Telegram, if enabled)
say "Recreating from Drive…"
if [ "$TELEGRAM" -eq 1 ]; then
  bash _tools/publish-lesson.sh
else
  bash _tools/publish-lesson.sh --no-telegram
fi

# 3. delete the OLD channel posts (done last, so the fresh one is already up)
if [ "$TELEGRAM" -eq 1 ] && [ -n "$old_ids" ]; then
  say "Removing the old channel post(s)…"
  # shellcheck disable=SC2086
  python3 _tools/telegram_util.py delete $old_ids
fi

say "Done."
