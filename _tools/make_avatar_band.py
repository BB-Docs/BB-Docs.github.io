#!/usr/bin/env python3
"""Avatar: big tree filling the frame, with the wordmark on a band across the middle.

Everything stays inside the circular-crop safe area (SAFE x radius), including
the band's corners — which are the widest thing in the design.

  make_avatar_band.py <mark.svg> <wordmark.txt> <out.svg>
"""
import re
import sys

SIZE = 1024.0
SAFE = 0.88          # fraction of the circle radius artwork may occupy
BG = "#ffffff"
INK = "#1f1b16"

TREE_H = SIZE * 0.72     # tree is tall+narrow; this is near the safe-circle limit
BAND_W = SIZE * 0.80
BAND_H = SIZE * 0.15
BAND_R = SIZE * 0.026
PAD = SIZE * 0.045       # horizontal padding inside the band
STROKE = 4.0


def half_diag(w, h):
    return ((w / 2) ** 2 + (h / 2) ** 2) ** 0.5


def main():
    mark_path, wm_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    src = open(mark_path, encoding="utf-8").read()
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', src, re.S)
    mx, my, mw, mh = [float(v) for v in m.group(1).split()]
    inner = m.group(2)

    lines = open(wm_path, encoding="utf-8").read().splitlines()
    d = lines[0]
    xmin, ymin, xmax, ymax = [float(v) for v in lines[1].split()]
    tw = xmax - xmin

    # --- tree, centred, as large as the safe circle allows ---
    s = TREE_H / mh
    tw_mark = mw * s
    tree = (f'<g transform="translate({SIZE/2 - tw_mark/2 - mx*s:.2f},'
            f'{SIZE/2 - TREE_H/2 - my*s:.2f}) scale({s:.5f})">{inner}</g>')

    # --- band across the middle ---
    bx, by = (SIZE - BAND_W) / 2, (SIZE - BAND_H) / 2
    band = (f'<rect x="{bx:.2f}" y="{by:.2f}" width="{BAND_W:.2f}" height="{BAND_H:.2f}" '
            f'rx="{BAND_R:.2f}" fill="{BG}" stroke="{INK}" stroke-width="{STROKE}"/>')

    # --- wordmark, fitted inside the band and optically centred ---
    k = (BAND_W - 2 * PAD) / tw
    baseline = SIZE / 2 - ((ymin + ymax) / 2) * k       # centre the ink box on the band
    text = (f'<g transform="translate({SIZE/2 - tw*k/2 - xmin*k:.2f},{baseline:.2f}) '
            f'scale({k:.5f})"><path fill="{INK}" d="{d}"/></g>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE:.0f} {SIZE:.0f}" '
           f'role="img" aria-label="Daily Lesson Notes">'
           f'<title>Daily Lesson Notes</title>'
           f'<rect width="{SIZE:.0f}" height="{SIZE:.0f}" fill="{BG}"/>'
           f'{tree}{band}{text}</svg>\n')
    open(out, "w", encoding="utf-8").write(svg)

    r = (SIZE / 2) * SAFE
    print(f"  tree  {tw_mark:.0f}x{TREE_H:.0f}  half-diag {half_diag(tw_mark, TREE_H):.0f} "
          f"{'✓' if half_diag(tw_mark, TREE_H) <= r else '✗ OVERFLOWS'} (safe {r:.0f})")
    print(f"  band  {BAND_W:.0f}x{BAND_H:.0f}  half-diag {half_diag(BAND_W, BAND_H):.0f} "
          f"{'✓' if half_diag(BAND_W, BAND_H) <= r else '✗ OVERFLOWS'}")
    print(f"  text  {tw*k:.0f} wide, ink {(ymax-ymin)*k:.0f} tall inside a {BAND_H:.0f} band")


if __name__ == "__main__":
    main()
