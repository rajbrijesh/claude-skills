#!/usr/bin/env python3
"""
Convert Unicode Devanagari in a .docx to DevLys 010 glyph text, in place in the XML.

    python convert_docx.py input.docx [-o output.docx] [--font "DevLys 010"] [--punct keep|devlys]
    python convert_docx.py input.docx --verify output.docx     # verify only

- Never touches the original; default output is <name>_DevLys.docx next to it.
- Walks document.xml, headers, footers, footnotes, endnotes, comments (text boxes and
  nested tables live inside these parts, so every w:p is reached).
- Only Devanagari (U+0900-097F) is re-encoded. English, digits, punctuation keep their
  original runs and fonts. Hindi runs are split from non-Hindi text at fine granularity.
- Formatting is carried over from the original run. Word stores Hindi size/bold/italic in
  the complex-script slots (szCs/bCs/iCs); because DevLys text is Latin-coded, those values
  are copied into sz/b/i so the visible size and weight do not change.
"""
import argparse
import copy
import json
import os
import re
import sys
import zipfile

from lxml import etree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devlys_engine import (convert_segments, devlys_to_unicode, is_devanagari,  # noqa: E402
                           normalize, ZWJ, ZWNJ)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"
q = lambda t: f"{{{W}}}{t}"
PART_RE = re.compile(r"^word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml$")


def has_dev(s):
    return any(is_devanagari(c) for c in s)


def _set_fonts(rpr, font):
    rf = rpr.find(q("rFonts"))
    if rf is None:
        rf = etree.Element(q("rFonts"))
        rpr.insert(0, rf)
    for k in list(rf.attrib):
        del rf.attrib[k]
    for k in ("ascii", "hAnsi", "cs", "eastAsia"):
        rf.set(q(k), font)


def _devlys_rpr(src_rpr, font):
    rpr = copy.deepcopy(src_rpr) if src_rpr is not None else etree.Element(q("rPr"))
    # move complex-script size/bold/italic into the Latin slots, then drop the cs markers
    for cs, lat in (("szCs", "sz"), ("bCs", "b"), ("iCs", "i")):
        c = rpr.find(q(cs))
        if c is not None:
            old = rpr.find(q(lat))
            if old is not None:
                rpr.remove(old)
            new = copy.deepcopy(c)
            new.tag = q(lat)
            rpr.append(new)
    for tag in ("cs", "rtl"):
        e = rpr.find(q(tag))
        if e is not None:
            rpr.remove(e)
    _set_fonts(rpr, font)
    # schema order matters to Word: put rFonts first, keep the rest as is
    rf = rpr.find(q("rFonts"))
    rpr.remove(rf)
    rpr.insert(0, rf)
    return rpr


def _text_run(src_rpr, text, font=None):
    r = etree.Element(q("r"))
    if font:
        r.append(_devlys_rpr(src_rpr, font))
    elif src_rpr is not None:
        r.append(copy.deepcopy(src_rpr))
    t = etree.SubElement(r, q("t"))
    t.text = text
    t.set(f"{{{XML}}}space", "preserve")
    return r


def convert_run(run, font, punct, stats):
    """Return replacement runs for `run`, or None when nothing to convert."""
    ts = [c for c in run if c.tag == q("t")]
    if not any(has_dev(t.text or "") for t in ts):
        return None
    rpr = run.find(q("rPr"))
    out = []
    for child in run:
        if child.tag == q("rPr"):
            continue
        if child.tag != q("t"):
            r = etree.Element(q("r"))
            if rpr is not None:
                r.append(copy.deepcopy(rpr))
            r.append(copy.deepcopy(child))
            out.append(r)
            continue
        txt = child.text or ""
        if not has_dev(txt):
            out.append(_text_run(rpr, txt))
            continue
        for seg in convert_segments(txt, punct=punct):
            if seg.converted:
                out.append(_text_run(rpr, seg.text, font))
                stats["converted_chars"] += len(seg.source)
            else:
                out.append(_text_run(rpr, seg.text))
                stats["unsupported"].update(c for c in seg.text if is_devanagari(c))
    stats["runs_converted"] += 1
    return out


def process_part(xml_bytes, font, punct, stats):
    root = etree.fromstring(xml_bytes)
    for run in list(root.iter(q("r"))):
        new = convert_run(run, font, punct, stats)
        if new is None:
            continue
        parent = run.getparent()
        idx = parent.index(run)
        parent.remove(run)
        for k, r in enumerate(new):
            parent.insert(idx + k, r)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def convert(src, dst, font="DevLys 010", punct="keep"):
    stats = {"runs_converted": 0, "converted_chars": 0, "unsupported": set(), "parts": [], "unsupported_elements": []}
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if PART_RE.match(item.filename):
                before = stats["runs_converted"]
                data = process_part(data, font, punct, stats)
                if stats["runs_converted"] > before:
                    stats["parts"].append(item.filename)
            elif item.filename.endswith(".xml") and item.filename.startswith(("word/charts/", "word/diagrams/")):
                if has_dev(data.decode("utf-8", "ignore")):
                    stats["unsupported_elements"].append(f"{item.filename}: Hindi text in chart/SmartArt left unchanged")
            zout.writestr(item, data)
    stats["unsupported"] = sorted(stats["unsupported"])
    return stats


# ----------------------------- verification -----------------------------

def _paragraph_texts(path, font=None):
    """Per paragraph text; DevLys-font runs decoded back to Unicode when font is given."""
    res = []
    with zipfile.ZipFile(path) as z:
        for n in sorted(z.namelist()):
            if not PART_RE.match(n):
                continue
            root = etree.fromstring(z.read(n))
            for p in root.iter(q("p")):
                buf = []
                for r in p.iter(q("r")):
                    rf = r.find(f"{q('rPr')}/{q('rFonts')}")
                    is_dl = font and rf is not None and rf.get(q("ascii")) == font
                    for t in r.iter(q("t")):
                        s = t.text or ""
                        buf.append(devlys_to_unicode(s) if is_dl else s)
                res.append((n, "".join(buf)))
    return res


def verify(orig, out, font="DevLys 010"):
    a = _paragraph_texts(orig)
    b = _paragraph_texts(out, font)
    problems = []
    if len(a) != len(b):
        problems.append(f"paragraph count differs: {len(a)} vs {len(b)}")
    clean = lambda s: normalize(s).replace(ZWJ, "").replace(ZWNJ, "")
    for (pa, ta), (pb, tb) in zip(a, b):
        if clean(ta) != clean(tb):
            problems.append({"part": pa, "original": ta[:80], "roundtrip": tb[:80]})
    # Every Latin word of the original must survive in a run that is NOT DevLys-fonted.
    def latin_words(path, skip_font=None):
        words = []
        with zipfile.ZipFile(path) as z:
            for n in sorted(z.namelist()):
                if not PART_RE.match(n):
                    continue
                for r in etree.fromstring(z.read(n)).iter(q("r")):
                    rf = r.find(f"{q('rPr')}/{q('rFonts')}")
                    if skip_font and rf is not None and rf.get(q("ascii")) == skip_font:
                        continue
                    for t in r.iter(q("t")):
                        words += re.findall(r"[A-Za-z0-9]+", t.text or "")
        return sorted(words)
    ow, nw = latin_words(orig), latin_words(out, font)
    bad_font = 0 if ow == nw else abs(len(ow) - len(nw)) or 1
    return {"paragraphs": len(a), "mismatches": problems, "english_words_changed": bad_font}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--font", default="DevLys 010")
    ap.add_argument("--punct", choices=["keep", "devlys"], default="keep")
    ap.add_argument("--verify", metavar="OUTPUT", help="only verify OUTPUT against input")
    a = ap.parse_args()

    if a.verify:
        print(json.dumps(verify(a.input, a.verify, a.font), ensure_ascii=False, indent=2))
        return
    out = a.output or re.sub(r"\.docx$", "", a.input, flags=re.I) + "_DevLys.docx"
    if os.path.abspath(out) == os.path.abspath(a.input):
        sys.exit("refusing to overwrite the original file")
    st = convert(a.input, out, a.font, a.punct)
    v = verify(a.input, out, a.font)
    print(json.dumps({"output": out, **st, "verification": v}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
