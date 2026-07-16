#!/usr/bin/env python3
"""Avatar concepts that share the BB tree mark but NOT the band-across-the-middle
composition.

  A badge   — tree centred, wordmark curved along the bottom arc, hairline ring
  B disc    — tree knocked out of a solid teal disc, no text at all
  C plinth  — tree above a hairline rule, letterspaced small caps beneath
  D ring    — tree centred, wordmark curved along the TOP arc, date-style dots

  make_avatar_variants.py <mark.svg> <font.ttf> <out-dir>
"""
import math
import os
import re
import sys

import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.misc.transform import Transform

SIZE = 1024.0
CX = CY = SIZE / 2
SAFE = 0.88
INK = "#1f1b16"
CREAM = "#faf8f4"
TEAL = "#0f8b91"
WHITE = "#ffffff"


# ---------- type helpers ----------
class Type:
    def __init__(self, font_path):
        with open(font_path, "rb") as fh:
            data = fh.read()
        self.face = hb.Face(data)
        self.hbfont = hb.Font(self.face)
        self.upem = self.face.upem
        self.tt = TTFont(font_path)
        self.order = self.tt.getGlyphOrder()
        self.gs = self.tt.getGlyphSet()

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hbfont, buf)
        return [(self.order[i.codepoint], p.x_advance)
                for i, p in zip(buf.glyph_infos, buf.glyph_positions)]

    def straight(self, text, tracking=0.0):
        """Outlined path for a run of text; returns (d, advance_width, bounds)."""
        glyphs = self.shape(text)
        pen = SVGPathPen(self.gs)
        bp = BoundsPen(self.gs)
        x = 0.0
        for name, adv in glyphs:
            t = Transform(1, 0, 0, -1, x, 0)
            self.gs[name].draw(TransformPen(pen, t))
            self.gs[name].draw(TransformPen(bp, t))
            x += adv + tracking
        return pen.getCommands(), x - tracking, bp.bounds

    def on_arc(self, text, k, radius, top=False, fill=INK):
        """Set text along a circle, reading left->right.

        Bottom arc: pos (sin t, cos t) from centre, tangent angle -t.
        Top arc:    pos (sin t, -cos t),            tangent angle +t.
        (Reusing one formula with a sign flip walks the glyphs backwards.)
        """
        glyphs = self.shape(text)
        total = sum(a for _, a in glyphs) * k
        span = total / radius                      # radians subtended
        out = []
        cum = 0.0
        for name, adv in glyphs:
            t = -span / 2 + ((cum + adv / 2) * k) / radius
            if top:
                px = CX + radius * math.sin(t)
                py = CY - radius * math.cos(t)
                rot = math.degrees(t)
            else:
                px = CX + radius * math.sin(t)
                py = CY + radius * math.cos(t)
                rot = -math.degrees(t)
            pen = SVGPathPen(self.gs)
            self.gs[name].draw(TransformPen(pen, Transform(1, 0, 0, -1, 0, 0)))
            d = pen.getCommands()
            if d.strip():
                out.append(
                    f'<g transform="translate({px:.2f},{py:.2f}) rotate({rot:.2f}) '
                    f'scale({k:.5f}) translate({-adv/2:.1f},0)">'
                    f'<path fill="{fill}" d="{d}"/></g>')
            cum += adv
        return "".join(out), span


# ---------- mark helpers ----------
def load_mark(path):
    src = open(path, encoding="utf-8").read()
    m = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', src, re.S)
    vb = [float(v) for v in m.group(1).split()]
    return vb, m.group(2)


def place_mark(vb, inner, cx, cy, h):
    mx, my, mw, mh = vb
    s = h / mh
    w = mw * s
    return (f'<g transform="translate({cx - w/2 - mx*s:.2f},{cy - h/2 - my*s:.2f}) '
            f'scale({s:.5f})">{inner}</g>'), w


def solid(inner, colour):
    """Recolour the gradient-filled mark to a flat colour."""
    out = re.sub(r'stop-color="[^"]*"', f'stop-color="{colour}"', inner)
    return out


def wrap(body, bg):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE:.0f} {SIZE:.0f}" '
            f'role="img" aria-label="Daily Lesson Notes">'
            f'<title>Daily Lesson Notes</title>'
            f'<rect width="{SIZE:.0f}" height="{SIZE:.0f}" fill="{bg}"/>{body}</svg>\n')


def check(name, w, h):
    r = (SIZE / 2) * SAFE
    hd = ((w / 2) ** 2 + (h / 2) ** 2) ** 0.5
    print(f"  {name:<8} artwork {w:.0f}x{h:.0f} half-diag {hd:.0f} "
          f"{'✓' if hd <= r else '✗ OVERFLOWS'} (safe {r:.0f})")


def main():
    mark_path, font_path, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    vb, inner = load_mark(mark_path)
    T = Type(font_path)

    # ---- A. badge: tree + wordmark curved along the bottom, hairline ring ----
    tree, tw = place_mark(vb, inner, CX, CY - SIZE * 0.045, SIZE * 0.52)
    R = SIZE * 0.375
    arc, span = T.on_arc("DAILY LESSON NOTES", 0.052, R, top=False)
    ring = (f'<circle cx="{CX}" cy="{CY}" r="{SIZE*0.455:.1f}" fill="none" '
            f'stroke="{INK}" stroke-width="3" opacity="0.35"/>')
    open(f"{outdir}/v-badge.svg", "w").write(wrap(tree + ring + arc, CREAM))
    check("badge", SIZE * 0.91, SIZE * 0.91)

    # ---- B. disc: flat cream tree knocked out of a teal disc ----
    disc = f'<circle cx="{CX}" cy="{CY}" r="{SIZE/2:.0f}" fill="{TEAL}"/>'
    knock, _ = place_mark(vb, solid(inner, CREAM), CX, CY, SIZE * 0.66)
    open(f"{outdir}/v-disc.svg", "w").write(wrap(disc + knock, TEAL))
    check("disc", SIZE * 0.36, SIZE * 0.66)

    # ---- C. plinth: tree above a hairline rule, letterspaced caps beneath ----
    d, adv, bounds = T.straight("DAILY LESSON NOTES", tracking=190)
    xmin, ymin, xmax, ymax = bounds
    kw = (SIZE * 0.60) / (xmax - xmin)
    tree2, _ = place_mark(vb, inner, CX, CY - SIZE * 0.085, SIZE * 0.56)
    rule_y = CY + SIZE * 0.175
    rule = (f'<line x1="{CX - SIZE*0.22:.0f}" y1="{rule_y:.0f}" x2="{CX + SIZE*0.22:.0f}" '
            f'y2="{rule_y:.0f}" stroke="{INK}" stroke-width="2.5" opacity="0.35"/>')
    baseline = rule_y + SIZE * 0.072
    caps = (f'<g transform="translate({CX - (xmax-xmin)*kw/2 - xmin*kw:.2f},{baseline:.2f}) '
            f'scale({kw:.5f})"><path fill="{INK}" d="{d}"/></g>')
    open(f"{outdir}/v-plinth.svg", "w").write(wrap(tree2 + rule + caps, CREAM))
    check("plinth", SIZE * 0.60, SIZE * 0.72)

    # ---- D. ring: wordmark curved along the TOP, tree below ----
    tree3, _ = place_mark(vb, inner, CX, CY + SIZE * 0.05, SIZE * 0.56)
    arc2, _ = T.on_arc("DAILY LESSON NOTES", 0.050, SIZE * 0.38, top=True)
    open(f"{outdir}/v-ring.svg", "w").write(wrap(tree3 + arc2, WHITE))
    check("ring", SIZE * 0.86, SIZE * 0.86)


if __name__ == "__main__":
    main()
