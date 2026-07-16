#!/usr/bin/env python3
"""Compose the Kabbalah Media tree mark + an outlined "Daily Lesson Notes"
wordmark into logo lockups.

  make_logo.py <mark.svg> <wordmark.txt> <out-dir>

wordmark.txt: line 1 = svg path data, line 2 = "xmin ymin xmax ymax" ink bounds.
Text is already outlined, so the result needs no fonts.
"""
import re
import sys
import os

INK = "#1f1b16"   # site --ink


def load_mark(path):
    src = open(path, encoding="utf-8").read()
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', src, re.S)
    vb = [float(v) for v in m.group(1).split()]
    return vb, m.group(2)


def main():
    mark_path, wm_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    (mx, my, mw, mh), mark_inner = load_mark(mark_path)
    lines = open(wm_path, encoding="utf-8").read().splitlines()
    d = lines[0]
    xmin, ymin, xmax, ymax = [float(v) for v in lines[1].split()]
    tw, th = xmax - xmin, ymax - ymin

    def wordmark(k, tx, ty):
        """Place the outlined text so its ink starts at (tx,ty) top-left."""
        return (f'<g transform="translate({tx - xmin * k:.2f},{ty - ymin * k:.2f}) '
                f'scale({k:.5f})"><path fill="{INK}" d="{d}"/></g>')

    def mark(tx, ty, s=1.0):
        return (f'<g transform="translate({tx - mx * s:.2f},{ty - my * s:.2f}) '
                f'scale({s:.5f})">{mark_inner}</g>')

    def wrap(w, h, body, title):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
                f'role="img" aria-label="{title}"><title>{title}</title>{body}</svg>\n')

    TITLE = "Daily Lesson Notes"

    # ---- A. horizontal lockup: mark left, wordmark right, vertically centred ----
    # Text ink height ~45% of mark height (matches the current header proportions).
    kA = (mh * 0.45) / th
    gap = mh * 0.18
    twA, thA = tw * kA, th * kA
    wA = mw + gap + twA
    bodyA = mark(0, 0) + wordmark(kA, mw + gap, (mh - thA) / 2)
    open(os.path.join(outdir, "logo-lockup.svg"), "w").write(wrap(wA, mh, bodyA, TITLE))

    # ---- B. stacked: mark on top, wordmark centred beneath ----
    wB = 1400.0
    kB = wB / tw
    thB = th * kB
    gapB = mh * 0.10
    hB = mh + gapB + thB
    bodyB = mark((wB - mw) / 2, 0) + wordmark(kB, 0, mh + gapB)
    open(os.path.join(outdir, "logo-stacked.svg"), "w").write(wrap(wB, hB, bodyB, TITLE))

    print(f"A horizontal : {wA:.0f} x {mh:.0f}  (aspect {wA/mh:.2f})")
    print(f"B stacked    : {wB:.0f} x {hB:.0f}  (aspect {wB/hB:.2f})")


if __name__ == "__main__":
    main()
