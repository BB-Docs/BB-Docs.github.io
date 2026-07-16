#!/usr/bin/env python3
"""Final avatar: cream tree knocked out of a solid teal disc, "Lesson Notes" beneath.

Everything is checked against the circular-crop safe area. Unlike a bounding-box
half-diagonal, this measures each element's true worst-case distance from the
centre, which is what a circular crop actually cares about.

  make_avatar_disc.py <mark.svg> <wordmark.txt> <out.svg>
"""
import re
import sys

SIZE = 1024.0
CX = CY = SIZE / 2
SAFE_R = (SIZE / 2) * 0.88

TEAL = "#0f8b91"
CREAM = "#faf8f4"

TREE_H = SIZE * 0.58
TREE_CY = SIZE * 0.42        # nudged up to leave room for the wordmark
TEXT_W = SIZE * 0.48
TEXT_CY = SIZE * 0.785


def corner_dist(cx, cy, w, h):
    """Worst-case distance from canvas centre to a box's corners."""
    return max(((cx + sx * w / 2 - CX) ** 2 + (cy + sy * h / 2 - CY) ** 2) ** 0.5
               for sx in (-1, 1) for sy in (-1, 1))


def main():
    mark_path, wm_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    src = open(mark_path, encoding="utf-8").read()
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', src, re.S)
    mx, my, mw, mh = [float(v) for v in m.group(1).split()]
    inner = m.group(2)
    # flatten the teal gradient to solid cream so it knocks out of the disc
    inner = re.sub(r'stop-color="[^"]*"', f'stop-color="{CREAM}"', inner)

    lines = open(wm_path, encoding="utf-8").read().splitlines()
    d = lines[0]
    xmin, ymin, xmax, ymax = [float(v) for v in lines[1].split()]
    tw, th = xmax - xmin, ymax - ymin

    s = TREE_H / mh
    tree_w = mw * s
    tree = (f'<g transform="translate({CX - tree_w/2 - mx*s:.2f},'
            f'{TREE_CY - TREE_H/2 - my*s:.2f}) scale({s:.5f})">{inner}</g>')

    k = TEXT_W / tw
    text_h = th * k
    baseline = TEXT_CY - ((ymin + ymax) / 2) * k
    text = (f'<g transform="translate({CX - tw*k/2 - xmin*k:.2f},{baseline:.2f}) '
            f'scale({k:.5f})"><path fill="{CREAM}" d="{d}"/></g>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE:.0f} {SIZE:.0f}" '
           f'role="img" aria-label="Daily Lesson Notes">'
           f'<title>Daily Lesson Notes</title>'
           f'<rect width="{SIZE:.0f}" height="{SIZE:.0f}" fill="{TEAL}"/>'
           f'{tree}{text}</svg>\n')
    open(out, "w", encoding="utf-8").write(svg)

    dt = corner_dist(CX, TREE_CY, tree_w, TREE_H)
    dx = corner_dist(CX, TEXT_CY, tw * k, text_h)
    print(f"  tree  {tree_w:.0f}x{TREE_H:.0f} @cy {TREE_CY:.0f}  furthest {dt:.0f} "
          f"{'✓' if dt <= SAFE_R else '✗ OVERFLOWS'} (safe {SAFE_R:.0f})")
    print(f"  text  {tw*k:.0f}x{text_h:.0f} @cy {TEXT_CY:.0f}  furthest {dx:.0f} "
          f"{'✓' if dx <= SAFE_R else '✗ OVERFLOWS'}")


if __name__ == "__main__":
    main()
