#!/usr/bin/env python3
"""Build the 1200x630 social card used as og:image.

  make_ogimage.py <lockup.svg> <out.svg>
"""
import re
import sys

W, H = 1200.0, 630.0
BG = "#faf8f4"          # site --bg
LINE = "#e7e1d6"        # site --line


def main():
    lockup_path, out = sys.argv[1], sys.argv[2]
    src = open(lockup_path, encoding="utf-8").read()
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', src, re.S)
    vx, vy, vw, vh = [float(v) for v in m.group(1).split()]
    inner = m.group(2)

    # Fit the lockup to ~72% of the card width, centred.
    target_w = W * 0.72
    s = target_w / vw
    w, h = vw * s, vh * s
    tx = (W - w) / 2 - vx * s
    ty = (H - h) / 2 - vy * s

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'role="img" aria-label="Daily Lesson Notes">'
        f'<title>Daily Lesson Notes</title>'
        f'<rect width="{W:.0f}" height="{H:.0f}" fill="{BG}"/>'
        f'<rect x="0" y="0" width="{W:.0f}" height="8" fill="{LINE}"/>'
        f'<g transform="translate({tx:.2f},{ty:.2f}) scale({s:.5f})">{inner}</g>'
        f'</svg>\n'
    )
    open(out, "w", encoding="utf-8").write(svg)
    print(f"lockup {w:.0f}x{h:.0f} centred on {W:.0f}x{H:.0f} card")


if __name__ == "__main__":
    main()
