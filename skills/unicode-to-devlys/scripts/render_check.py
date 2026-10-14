#!/usr/bin/env python3
"""
Visual check: draw each Unicode line (left, in a Unicode Devanagari font) next to
its DevLys conversion (right, drawn with a DevLys / Kruti Dev 010 TTF). Wrong
glyph mapping is obvious at a glance.

    python render_check.py --devlys-font K010.TTF --unicode-font NotoSansDevanagari.ttf \
        --out check.png  "राजस्थान सरकार" "कार्यालय आदेश"
    python render_check.py ... --from-docx original.docx --limit 40

DevLys 010 and Kruti Dev 010 use the same character map, so either TTF works.
Needs Pillow; Pillow built with libraqm shapes the Unicode side correctly.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont, features

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devlys_engine import convert_segments  # noqa: E402


def lines_from_docx(path, limit):
    import zipfile
    import re
    from xml.etree import ElementTree as ET
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    out = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)]
        for n in names:
            root = ET.fromstring(z.read(n))
            for p in root.iter(W + "p"):
                t = "".join(x.text or "" for x in p.iter(W + "t")).strip()
                if any(0x0900 <= ord(c) <= 0x097F for c in t):
                    out.append(t[:90])
                if len(out) >= limit:
                    return out
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lines", nargs="*")
    ap.add_argument("--devlys-font", required=True)
    ap.add_argument("--unicode-font", required=True)
    ap.add_argument("--from-docx")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--size", type=int, default=30)
    ap.add_argument("--out", default="render_check.png")
    a = ap.parse_args()

    lines = list(a.lines)
    if a.from_docx:
        lines += lines_from_docx(a.from_docx, a.limit)
    if not lines:
        sys.exit("nothing to render")

    raqm = features.check("raqm")
    uf = ImageFont.truetype(a.unicode_font, a.size,
                            layout_engine=ImageFont.Layout.RAQM if raqm else ImageFont.Layout.BASIC)
    df = ImageFont.truetype(a.devlys_font, int(a.size * 1.25), layout_engine=ImageFont.Layout.BASIC)

    rows = []
    for ln in lines:
        segs = convert_segments(ln)
        # unconverted pieces (English, digits, punctuation) are drawn with the unicode font
        rows.append((ln, segs))

    def width(font, s):
        return font.getlength(s) if s else 0

    colw = int(max(max(width(uf, ln) for ln, _ in rows),
                   max(sum(width(df if s.converted else uf, s.text) for s in segs) for _, segs in rows))) + 40
    rh = int(a.size * 2.4)
    img = Image.new("RGB", (colw * 2 + 20, rh * len(rows) + 10), "white")
    d = ImageDraw.Draw(img)
    for i, (ln, segs) in enumerate(rows):
        y = 5 + i * rh
        d.line([(0, y + rh - 2), (img.width, y + rh - 2)], fill=(225, 225, 225))
        d.text((10, y + 4), ln, font=uf, fill="black")
        x = colw + 20
        for s in segs:
            f = df if s.converted else uf
            d.text((x, y + 4), s.text, font=f, fill=(140, 0, 0) if s.converted else (0, 0, 160))
            x += width(f, s.text)
    d.line([(colw + 10, 0), (colw + 10, img.height)], fill=(180, 180, 180))
    img.save(a.out)
    print(f"wrote {a.out} ({len(rows)} lines; raqm shaping={'on' if raqm else 'OFF - unicode side may look wrong'})")


if __name__ == "__main__":
    main()
