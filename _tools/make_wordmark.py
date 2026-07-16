#!/usr/bin/env python3
"""Shape a string in a font (HarfBuzz) and emit outlined SVG path data.

Text-as-outlines means the logo renders identically everywhere with no font
dependency — the right thing for a logo file.

Usage: make_wordmark.py <font.ttf> "<text>" > paths.txt
Prints: <path d> on line 1, then "width height" (in font units) on line 2.
"""
import sys
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform


def main():
    font_path, text = sys.argv[1], sys.argv[2]

    # --- shape (gives glyph ids + kerned positions) ---
    with open(font_path, "rb") as fh:
        data = fh.read()
    face = hb.Face(data)
    hb_font = hb.Font(face)
    upem = face.upem
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)

    # --- outline each shaped glyph at its position ---
    tt = TTFont(font_path)
    glyph_order = tt.getGlyphOrder()
    glyph_set = tt.getGlyphSet()

    pen_out = SVGPathPen(glyph_set)
    x = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = glyph_order[info.codepoint]
        # y is flipped: font y-up -> svg y-down
        t = Transform(1, 0, 0, -1, x + pos.x_offset, pos.y_offset)
        tpen = TransformPen(pen_out, t)
        glyph_set[name].draw(tpen)
        x += pos.x_advance
        # (y_advance is 0 for horizontal text)

    d = pen_out.getCommands()

    # Tight ink bounds, in the same flipped space as the emitted path.
    from fontTools.pens.boundsPen import BoundsPen
    bp = BoundsPen(glyph_set)
    x2 = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = glyph_order[info.codepoint]
        t = Transform(1, 0, 0, -1, x2 + pos.x_offset, pos.y_offset)
        glyph_set[name].draw(TransformPen(bp, t))
        x2 += pos.x_advance
    xmin, ymin, xmax, ymax = bp.bounds

    sys.stdout.write(d + "\n")
    print(f"{xmin} {ymin} {xmax} {ymax}")
    sys.stderr.write(
        f"upem={upem} advance={x} ink_bbox=({xmin:.0f},{ymin:.0f},{xmax:.0f},{ymax:.0f}) "
        f"ink_w={xmax-xmin:.0f} ink_h={ymax-ymin:.0f}\n")


if __name__ == "__main__":
    main()
