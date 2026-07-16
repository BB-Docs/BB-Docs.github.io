#!/usr/bin/env python3
"""Build square avatar/profile-picture logos that survive a CIRCULAR crop.

Profile pictures (WhatsApp/Telegram/etc.) crop to a circle inscribed in the
square, so all artwork must sit inside that circle — and comfortably inside it,
since platforms zoom slightly. We keep everything within SAFE (a fraction of
the circle's radius).

  make_avatar.py <mark.svg> <out-dir>
"""
import re
import sys
import os

SIZE = 1024.0          # square canvas
SAFE = 0.86            # fraction of the circle radius artwork may occupy
INK = "#1f1b16"
BG = "#ffffff"


def load_mark(path):
    src = open(path, encoding="utf-8").read()
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', src, re.S)
    vb = [float(v) for v in m.group(1).split()]
    return vb, m.group(2)


def load_wm(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    d = lines[0]
    xmin, ymin, xmax, ymax = [float(v) for v in lines[1].split()]
    return d, xmin, ymin, xmax, ymax


def fits_circle(w, h):
    """Half-diagonal of the artwork box must stay inside the safe radius."""
    return ((w / 2) ** 2 + (h / 2) ** 2) ** 0.5 <= (SIZE / 2) * SAFE


def wrap(body, title, bg):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE:.0f} {SIZE:.0f}" '
            f'role="img" aria-label="{title}"><title>{title}</title>'
            f'<rect width="{SIZE:.0f}" height="{SIZE:.0f}" fill="{bg}"/>{body}</svg>\n')


def main():
    mark_path, outdir = sys.argv[1], sys.argv[2]
    (mx, my, mw, mh), inner = load_mark(mark_path)

    def mark(cx, cy, h):
        s = h / mh
        w = mw * s
        return (f'<g transform="translate({cx - w / 2 - mx * s:.2f},{cy - h / 2 - my * s:.2f}) '
                f'scale({s:.5f})">{inner}</g>'), w, h

    # ---- A. mark only: the tree, centred, as large as the safe circle allows ----
    h = SIZE * 0.62
    g, w, hh = mark(SIZE / 2, SIZE / 2, h)
    assert fits_circle(w, hh), "mark overflows the safe circle"
    open(os.path.join(outdir, "avatar.svg"), "w").write(
        wrap(g, "Daily Lesson Notes", BG))
    print(f"A avatar.svg        tree {w:.0f}x{hh:.0f} inside {SIZE:.0f} square (safe ✓)")

    # ---- B. mark + two lines of text, all inside the circle ----
    d1, x1min, y1min, x1max, y1max = load_wm("/tmp/wm1.txt")   # "Daily Lesson"
    d2, x2min, y2min, x2max, y2max = load_wm("/tmp/wm2.txt")   # "Notes"
    tw1, tw2 = x1max - x1min, x2max - x2min

    text_w = SIZE * 0.58               # widest line ("Daily Lesson") spans this
    k = text_w / tw1
    lh = 1.25 * 2000 * k               # baseline-to-baseline, from upem
    # block spans line-1 ink top (y1min) to line-2 ink bottom (lh + y2max)
    th = lh + (y2max - y1min) * k
    mark_h = SIZE * 0.35
    gap = SIZE * 0.04
    block_h = mark_h + gap + th
    top = (SIZE - block_h) / 2

    g2, w2, _ = mark(SIZE / 2, top + mark_h / 2, mark_h)
    base1 = top + mark_h + gap - y1min * k
    body = g2
    body += (f'<g transform="translate({SIZE/2 - tw1*k/2 - x1min*k:.2f},{base1:.2f}) '
             f'scale({k:.5f})"><path fill="{INK}" d="{d1}"/></g>')
    body += (f'<g transform="translate({SIZE/2 - tw2*k/2 - x2min*k:.2f},{base1 + lh:.2f}) '
             f'scale({k:.5f})"><path fill="{INK}" d="{d2}"/></g>')
    ok = fits_circle(max(w2, text_w), block_h)
    open(os.path.join(outdir, "avatar-text.svg"), "w").write(
        wrap(body, "Daily Lesson Notes", BG))
    print(f"B avatar-text.svg   block {max(w2,text_w):.0f}x{block_h:.0f} "
          f"inside safe circle: {'✓' if ok else '✗ OVERFLOWS'}")


if __name__ == "__main__":
    main()
