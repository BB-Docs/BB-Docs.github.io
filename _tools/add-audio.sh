#!/usr/bin/env bash
#
# add-audio — generate narration MP3s, upload them to the 'audio' GitHub
# Release, and stamp `audio: true` into each post's front matter.
#
#   add-audio                 # backfill every post that has no audio yet
#   add-audio _posts/x.md …   # only these posts (skips ones already done)
#   add-audio --force …       # regenerate even if already done (for edits)
#
set -uo pipefail          # NOT -e: one failure must not abort the whole batch
SITE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SITE_DIR"
export SSL_CERT_FILE=/etc/ssl/cert.pem     # edge-tts must trust this env's TLS proxy

REPO="BB-Docs/BB-Docs.github.io"
RELEASE="audio"
GIT_NAME="pradeepcb"; GIT_EMAIL="pradeepcb@gmail.com"

say()  { printf "\033[1;34m▸\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }

FORCE=0; ARGS=()
for a in "$@"; do
  case "$a" in --force) FORCE=1 ;; *.md) ARGS+=("$a") ;; *) echo "bad arg: $a" >&2; exit 2 ;; esac
done

# Build the work list.
targets=()
if [ "${#ARGS[@]}" -gt 0 ]; then
  for p in "${ARGS[@]}"; do
    [ -f "$p" ] || { warn "not found: $p"; continue; }
    if [ "$FORCE" -eq 0 ] && grep -q '^audio:' "$p"; then continue; fi
    targets+=("$p")
  done
else
  for p in _posts/*.md; do
    grep -q '^audio:' "$p" || targets+=("$p")
  done
fi

[ "${#targets[@]}" -gt 0 ] || { say "Nothing to do — every requested post already has audio."; exit 0; }
say "Generating audio for ${#targets[@]} lesson(s)…"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
done=0
for post in "${targets[@]}"; do
  base="$(basename "$post" .md)"
  printf "  \033[0;36m…\033[0m %s\n" "$base"
  if ! python3 _tools/make_audio.py "$post" "$TMP/$base.mp3" >/dev/null 2>"$TMP/err"; then
    warn "  generate failed: $(tr '\n' ' ' <"$TMP/err" | cut -c1-160)"; continue
  fi
  if ! gh release upload "$RELEASE" "$TMP/$base.mp3" --repo "$REPO" --clobber >/dev/null 2>&1; then
    warn "  upload failed for $base"; continue
  fi
  # stamp audio:true into the front matter (first closing delimiter)
  python3 - "$post" <<'PY'
import sys
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
if "\naudio:" not in s.split("---",2)[1]:
    s=s.replace("\n---\n","\naudio: true\n---\n",1)
    open(p,"w",encoding="utf-8").write(s)
PY
  rm -f "$TMP/$base.mp3"        # keep temp small during long backfills
  done=$((done+1))
  printf "  \033[1;32m✓\033[0m %s\n" "$base"
done

say "Generated $done/${#targets[@]}. Committing front-matter flags…"
git add _posts
if git diff --cached --quiet; then
  say "No new stamps to commit."
else
  git -c user.name="$GIT_NAME" -c user.email="$GIT_EMAIL" commit -qm "Add audio to $done lesson(s)"
  git pull --rebase --quiet origin main || true
  git push -q origin main && say "Pushed."
fi
