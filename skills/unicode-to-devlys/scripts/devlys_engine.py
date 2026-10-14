#!/usr/bin/env python3
"""
Unicode Devanagari  <->  DevLys 010 / Kruti Dev 010 (Remington, ASCII-mapped) engine.

DevLys 010 and Kruti Dev 010 share one character map, so the same output works
for both fonts. The legacy fonts are not OpenType: every visible shape (half
letters, conjuncts, the reph, the pre-base short-i) is a separate glyph sitting
on an ordinary Windows-1252 code point. Conversion therefore has to rebuild the
text glyph by glyph, in visual order:

    Unicode (logical order)   र्  +  म  +  ि        ->  "र्मि"
    DevLys  (visual order)    f  +  e  +  Z         ->  "feZ"

The engine parses the text into orthographic syllables (optional reph, a
consonant cluster joined by halants, vowel signs, modifiers) and renders each
syllable with the glyph tables below. Characters it cannot represent are
returned untouched and flagged, so the caller can keep them in the original
Unicode font instead of producing garbage.

Command line:
    python devlys_engine.py "राजस्थान सरकार"            -> jktLFkku ljdkj
    python devlys_engine.py --reverse "jktLFkku"        -> राजस्थान
    python devlys_engine.py --selftest                  -> runs built-in checks
"""
from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass, field

HALANT = "्"
NUKTA = "़"
ZWJ = "‍"
ZWNJ = "‌"
SIGN_I = "ि"  # ि  (pre-base in DevLys)

# --------------------------------------------------------------------------
# Glyph tables (verified by rendering against Kruti Dev 010 / K010.TTF)
# --------------------------------------------------------------------------

# consonant -> (full form, half form or None when the font has no half form)
CONSONANTS: dict[str, tuple[str, str | None]] = {
    "क": ("d", "D"), "ख": ("[k", "["), "ग": ("x", "X"), "घ": ("?k", "?"), "ङ": ("³", None),
    "च": ("p", "P"), "छ": ("N", None), "ज": ("t", "T"), "झ": (">", "÷"), "ञ": ("¥", None),
    "ट": ("V", None), "ठ": ("B", None), "ड": ("M", None), "ढ": ("<", None), "ण": (".k", "."),
    "त": ("r", "R"), "थ": ("Fk", "F"), "द": ("n", None), "ध": ("/k", "/"), "न": ("u", "U"),
    "प": ("i", "I"), "फ": ("Q", "¶"), "ब": ("c", "C"), "भ": ("Hk", "H"), "म": ("e", "E"),
    "य": (";", "¸"), "र": ("j", None), "ल": ("y", "Y"), "ळ": ("G", None), "व": ("o", "O"),
    "श": ("'k", "'"), "ष": ('"k', '"'), "स": ("l", "L"), "ह": ("g", "º"),
}

# Consonants drawn without a vertical stem: subscript-ra is "ª", subscript-ya is "î".
STEMLESS = set("टठडढछ")

# Conjunct ligatures that have their own glyph.  key = consonants joined by halant.
CONJUNCTS: dict[str, tuple[str, str | None]] = {
    "क्ष": ("{k", "{"), "त्र": ("=", "«"), "ज्ञ": ("K", None), "श्र": ("J", None),
    "त्त": ("Ùk", "Ù"),
    "द्द": ("í", None), "द्ध": (")", None), "द्व": ("}", None), "द्य": ("|", None),
    "द्र": ("æ", None), "द्म": ("ù", None),
    "ह्न": ("à", None), "ह्य": ("á", None), "ह्म": ("ã", None), "ह्र": ("ºz", None),
    "क्र": ("Ø", None), "प्र": ("ç", None), "फ्र": ("Ý", None),
    "ट्ट": ("ê", None), "ट्ठ": ("ë", None), "ड्ड": ("ì", None), "ड्ढ": ("ï", None),
    "ट्र": ("Vª", None), "ठ्र": ("Bª", None), "ड्र": ("Mª", None), "ढ्र": ("<ª", None),
    "छ्र": ("Nª", None),
    "ट्य": ("Vî", None), "ठ्य": ("Bî", None), "ड्य": ("Mî", None), "ढ्य": ("<î", None),
    "छ्य": ("Nî", None),
}

# consonant + vowel sign pairs with a dedicated glyph
CV_SPECIAL = {
    ("र", "ु"): "#",   # रु
    ("र", "ू"): ":",   # रू
    ("क", "ृ"): "—",   # कृ  (U+2014)
    ("द", "ृ"): "–",   # दृ  (U+2013)
    ("ह", "ृ"): "â",   # हृ
}

VOWEL_SIGNS = {
    "ा": "k",   # ा
    "ी": "h",   # ी
    "ु": "q",   # ु
    "ू": "w",   # ू
    "ृ": "`",   # ृ
    "े": "s",   # े
    "ै": "S",   # ै
    "ो": "ks",  # ो
    "ौ": "kS",  # ौ
    "ॉ": "kW",  # ॉ
    "ॅ": "W",   # ॅ
}
MODIFIERS = {
    "ं": "a",   # ं
    "ँ": "¡",   # ँ
    "ः": "%",   # ः
}

INDEPENDENT_VOWELS = {
    "अ": "v", "आ": "vk", "इ": "b", "ई": "bZ", "उ": "m", "ऊ": "Å", "ऋ": "_",
    "ए": ",", "ऐ": ",s", "ओ": "vks", "औ": "vkS", "ऑ": "vkW", "ऍ": ",W",
}

OTHER_SIGNS = {
    "।": "A", "॥": "AA", "ऽ": "·", "॰": "ñ",
    "०": "å", "१": "ƒ", "२": "„", "३": "…", "४": "†",
    "५": "‡", "६": "ˆ", "७": "‰", "८": "Š", "९": "‹",
}

REPH = "Z"
REPH_ANUSVARA = "±"   # reph and anusvara in one glyph (avoids the two dots colliding)
SUB_RA, SUB_RA_STEMLESS = "z", "ª"
EXPLICIT_HALANT = "~"
PRE_I = "f"

# ASCII punctuation as DevLys glyphs (only used with punct="devlys").
# Several ASCII keys draw Hindi letters in DevLys ("," is ए, "." is ण्, "-" is .),
# which is why punctuation is normally left in its original font instead.
PUNCT_TO_DEVLYS = {
    ",": "]", ".": "-", "-": "&", "?": "\\", "!": "!", "(": "¼", ")": "½",
    ";": "(", "/": "@", "+": "$", "=": "¾", ":": "%", "{": "¿", "}": "À",
    "‘": "^", "’": "*", "“": "ß", "”": "Þ",
    "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
    "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
}

DEV_START, DEV_END = 0x0900, 0x097F

# Composed nukta letters -> base + nukta (NFC keeps some of them composed).
_NUKTA_DECOMP = {
    "ऩ": "ऩ", "ऱ": "ऱ", "ऴ": "ऴ",
    "क़": "क़", "ख़": "ख़", "ग़": "ग़", "ज़": "ज़",
    "ड़": "ड़", "ढ़": "ढ़", "फ़": "फ़", "य़": "य़",
}


def is_devanagari(ch: str) -> bool:
    return DEV_START <= ord(ch) <= DEV_END


def normalize(text: str) -> str:
    """NFC, then split composed nukta letters so every nukta is a separate mark."""
    text = unicodedata.normalize("NFC", text)
    return "".join(_NUKTA_DECOMP.get(c, c) for c in text)


# --------------------------------------------------------------------------
# Unicode -> DevLys
# --------------------------------------------------------------------------

@dataclass
class _Piece:
    full: str
    half: str | None
    key: str            # unicode consonant(s) this piece stands for
    stemless: bool = False
    joint_after: str | None = None   # 'h', 'zwj', 'zwnj' or None
    sub_ra: bool = False


def _with_nukta(full: str, half: str | None) -> tuple[str, str | None]:
    # For letters drawn as half-form + stem ("[k" = ख) the dot goes before the stem.
    if half and full == half + "k":
        return half + "+k", half + "+"
    return full + "+", (half + "+") if half else None


def _render_cluster(units, joints, final_halant):
    """units: list of (consonant, has_nukta); joints: list of joint types between units."""
    n = len(units)
    pieces: list[_Piece] = []
    i = 0
    while i < n:
        matched = False
        for length in (2,):
            if i + length <= n and all(j == "h" for j in joints[i:i + length - 1]) \
                    and not any(u[1] for u in units[i:i + length]):
                key = HALANT.join(u[0] for u in units[i:i + length])
                if key in CONJUNCTS:
                    full, half = CONJUNCTS[key]
                    pieces.append(_Piece(full, half, key,
                                         joint_after=joints[i + length - 1] if i + length - 1 < len(joints) else None))
                    i += length
                    matched = True
                    break
        if matched:
            continue
        c, nk = units[i]
        full, half = CONSONANTS[c]
        if nk:
            full, half = _with_nukta(full, half)
        pieces.append(_Piece(full, half, c, stemless=(c in STEMLESS and not nk),
                             joint_after=joints[i] if i < len(joints) else None))
        i += 1

    # A final plain र after other consonants is drawn as the subscript-ra stroke.
    if (len(pieces) >= 2 and pieces[-1].key == "र" and pieces[-1].full == "j"
            and pieces[-2].joint_after == "h" and not final_halant):
        pieces.pop()
        pieces[-1].sub_ra = True

    out = []
    for k, p in enumerate(pieces):
        last = k == len(pieces) - 1
        if p.sub_ra:
            glyph = p.full + (SUB_RA_STEMLESS if p.stemless else SUB_RA)
            out.append(glyph + (EXPLICIT_HALANT if last and final_halant else ""))
        elif last:
            out.append(p.full + (EXPLICIT_HALANT if final_halant else ""))
        elif p.joint_after == "zwnj" or p.half is None:
            out.append(p.full + EXPLICIT_HALANT)
        else:
            out.append(p.half)
    return out, pieces


@dataclass
class Segment:
    text: str
    converted: bool          # True: DevLys glyph text; False: original characters
    source: str = ""         # original unicode for converted segments


def _parse(text: str):
    """Yield ('syl', units, joints, final_halant, signs, raw) | ('vow', ch, mods, raw) | ('chr', ch)."""
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in CONSONANTS:
            start = i
            units, joints = [], []
            nk = i + 1 < n and text[i + 1] == NUKTA
            units.append((ch, nk))
            i += 2 if nk else 1
            final_halant = False
            while i < n and text[i] == HALANT:
                j = i + 1
                jt = "h"
                if j < n and text[j] in (ZWJ, ZWNJ):
                    jt = "zwj" if text[j] == ZWJ else "zwnj"
                    j += 1
                if j < n and text[j] in CONSONANTS:
                    nk = j + 1 < n and text[j + 1] == NUKTA
                    joints.append(jt)
                    units.append((text[j], nk))
                    i = j + (2 if nk else 1)
                else:
                    final_halant = True
                    i = j
                    break
            signs = []
            while i < n and (text[i] in VOWEL_SIGNS or text[i] in MODIFIERS or text[i] == SIGN_I
                             or (0x093A <= ord(text[i]) <= 0x094F and text[i] != HALANT)
                             or text[i] in ("॑", "॒", "ॕ", "ॖ", "ॗ", "ॢ", "ॣ")):
                signs.append(text[i])
                i += 1
            yield ("syl", units, joints, final_halant, signs, text[start:i])
        elif ch in INDEPENDENT_VOWELS:
            start = i
            i += 1
            mods = []
            while i < n and (text[i] in MODIFIERS or text[i] in VOWEL_SIGNS or text[i] == NUKTA):
                mods.append(text[i])
                i += 1
            yield ("vow", ch, mods, text[start:i])
        else:
            yield ("chr", ch)
            i += 1


def _render_syllable(units, joints, final_halant, signs):
    """Return DevLys glyph string, or None if something in it has no DevLys glyph."""
    units, joints = list(units), list(joints)
    reph = False
    if len(units) >= 2 and units[0] == ("र", False) and joints[0] == "h":
        reph = True
        units, joints = units[1:], joints[1:]

    pre_i = False
    vowel_glyphs = []
    mods = []
    special_cv = None
    for s in signs:
        if s == SIGN_I:
            pre_i = True
        elif s in VOWEL_SIGNS:
            last_c, last_nk = units[-1]
            if (len(units) == 1 or s == "ृ") and not last_nk and not final_halant \
                    and (last_c, s) in CV_SPECIAL and special_cv is None \
                    and not (len(units) >= 2 and last_c == "र"):
                special_cv = CV_SPECIAL[(last_c, s)]
            else:
                vowel_glyphs.append(VOWEL_SIGNS[s])
        elif s in MODIFIERS:
            mods.append(MODIFIERS[s])
        else:
            return None  # unsupported sign (vedic, short e/o of other scripts, ...)

    body_pieces, pieces = _render_cluster(units, joints, final_halant)
    if special_cv is not None:
        if pieces[-1].key == units[-1][0] and not pieces[-1].sub_ra:
            body_pieces[-1] = special_cv          # e.g. "कृ" -> "—", "रु" -> "#"
        else:                                     # merged into a ligature: plain sign
            sign = next(s for s in signs if s in VOWEL_SIGNS)
            vowel_glyphs.insert(0, VOWEL_SIGNS[sign])
    body = "".join(body_pieces)

    glyph = (PRE_I if pre_i else "") + body + "".join(vowel_glyphs)
    if reph:
        if mods and mods[0] == "a":
            glyph += REPH_ANUSVARA + "".join(mods[1:])
        else:
            glyph += REPH + "".join(mods)
    else:
        glyph += "".join(mods)
    return glyph


def _render_vowel(ch, mods):
    glyph = INDEPENDENT_VOWELS[ch]
    if ch == "ई" and mods and mods[0] == "ं":
        return "b±" + "".join(MODIFIERS.get(m, "") for m in mods[1:])  # ईं
    out = glyph
    for m in mods:
        if m in MODIFIERS:
            out += MODIFIERS[m]
        else:
            return None
    return out


def convert_segments(text: str, punct: str = "keep", join_spaces: bool = True) -> list[Segment]:
    """
    Split `text` into segments. Devanagari is converted to DevLys glyph text;
    everything else (Latin, digits, punctuation, symbols) is returned unchanged
    with converted=False so it can keep its original font.

    punct="devlys": ASCII punctuation and digits that sit inside Hindi text are
    converted to their DevLys glyphs too, giving one continuous DevLys run.
    join_spaces: spaces between two converted pieces join the DevLys segment
    (fewer runs, natural word spacing).
    """
    text = normalize(text)
    raw: list[Segment] = []

    def push(t, conv, src=""):
        if raw and raw[-1].converted == conv:
            raw[-1].text += t
            raw[-1].source += src
        else:
            raw.append(Segment(t, conv, src))

    for item in _parse(text):
        kind = item[0]
        if kind == "syl":
            _, units, joints, fh, signs, src = item
            g = _render_syllable(units, joints, fh, signs)
            push(g, True, src) if g is not None else push(src, False)
        elif kind == "vow":
            _, ch, mods, src = item
            g = _render_vowel(ch, mods)
            push(g, True, src) if g is not None else push(src, False)
        else:
            ch = item[1]
            if ch in OTHER_SIGNS:
                push(OTHER_SIGNS[ch], True, ch)
            elif ch in (ZWJ, ZWNJ):
                continue  # invisible joiners carry no glyph in DevLys
            elif ch in VOWEL_SIGNS:            # stray sign with no consonant
                push(VOWEL_SIGNS[ch], True, ch)
            elif ch in MODIFIERS:
                push(MODIFIERS[ch], True, ch)
            else:
                push(ch, False)

    # Split unconverted segments into single characters so spaces / punctuation
    # between Hindi words can be absorbed into the DevLys run.
    flat: list[Segment] = []
    for s in raw:
        if s.converted:
            flat.append(s)
        else:
            flat.extend(Segment(c, False) for c in s.text)

    def neighbour_converted(idx, step):
        j = idx + step
        while 0 <= j < len(flat):
            s = flat[j]
            if s.converted:
                return True
            if s.text == " " or (punct == "devlys" and s.text in PUNCT_TO_DEVLYS):
                j += step
                continue
            return False
        return False

    for idx, s in enumerate(flat):
        if s.converted:
            continue
        absorbable = (join_spaces and s.text == " ") or (punct == "devlys" and s.text in PUNCT_TO_DEVLYS)
        if not absorbable:
            continue
        before, after = neighbour_converted(idx, -1), neighbour_converted(idx, 1)
        if s.text == " ":
            if before and after:
                s.converted, s.source = True, " "
        elif s.text.isdigit():
            if before or after:
                s.text, s.converted, s.source = PUNCT_TO_DEVLYS[s.text], True, s.text
        else:
            if before or after:
                s.source = s.text
                s.text, s.converted = PUNCT_TO_DEVLYS[s.text], True

    merged: list[Segment] = []
    for s in flat:
        if merged and merged[-1].converted == s.converted:
            merged[-1].text += s.text
            merged[-1].source += s.source
        else:
            merged.append(Segment(s.text, s.converted, s.source))
    return merged


def unicode_to_devlys(text: str, punct: str = "keep") -> str:
    """Convenience: whole string, unconvertible characters passed through."""
    return "".join(s.text for s in convert_segments(text, punct=punct))


def unsupported_chars(text: str) -> list[str]:
    """Devanagari characters in `text` that stay unconverted."""
    bad = []
    for s in convert_segments(text):
        if not s.converted:
            bad.extend(c for c in s.text if is_devanagari(c))
    return sorted(set(bad))


# --------------------------------------------------------------------------
# DevLys -> Unicode  (used to verify the conversion by round trip)
# --------------------------------------------------------------------------

def _build_reverse_tokens():
    t = {}
    for c, (full, half) in CONSONANTS.items():
        t.setdefault(full, ("C", c))
        if half:
            t.setdefault(half, ("H", c))
        nf, nh = _with_nukta(full, half)
        t.setdefault(nf, ("C", c + NUKTA))
        if nh:
            t.setdefault(nh, ("H", c + NUKTA))
    for key, (full, half) in CONJUNCTS.items():
        t[full] = ("C", key)
        if half:
            t[half] = ("H", key)
    for (c, v), g in CV_SPECIAL.items():
        t[g] = ("CV", c + v)
    for s, g in VOWEL_SIGNS.items():
        t[g] = ("V", s)
    for s, g in MODIFIERS.items():
        t[g] = ("M", s)
    for v, g in INDEPENDENT_VOWELS.items():
        t[g] = ("IV", v)
    t["b±"] = ("IV", "ईं")
    for s, g in OTHER_SIGNS.items():
        t[g] = ("O", s)
    t[REPH] = ("REPH", "")
    t[REPH_ANUSVARA] = ("REPHA", "")
    t[SUB_RA] = ("SUBR", "")
    t[SUB_RA_STEMLESS] = ("SUBR", "")
    t[EXPLICIT_HALANT] = ("HAL", "")
    t[PRE_I] = ("I", "")
    t["+"] = ("N", "")
    return t


_REV = _build_reverse_tokens()
_REV_KEYS = sorted(_REV, key=len, reverse=True)
_REV_RE = re.compile("|".join(re.escape(k) for k in _REV_KEYS))


def devlys_to_unicode(glyphs: str) -> str:
    """Decode DevLys glyph text produced by this engine back to Unicode."""
    out: list[str] = []
    pending_i = False
    cluster_start = 0
    in_cluster = False      # previous token left the cluster open (half form / halant)
    attachable = False      # right after a base consonant (nukta / subscript may follow)

    def flush_i():
        nonlocal pending_i
        if pending_i:
            out.append(SIGN_I)
            pending_i = False

    pos = 0
    while pos < len(glyphs):
        m = _REV_RE.match(glyphs, pos)
        if not m:
            flush_i() if attachable else None
            out.append(glyphs[pos])
            pos += 1
            in_cluster = attachable = False
            continue
        tok = m.group(0)
        pos = m.end()
        kind, val = _REV[tok]
        if kind in ("N", "SUBR") and (attachable or (kind == "N" and out)):
            if kind == "N":
                prev = out[-1]
                out[-1] = prev[:-1] + NUKTA + HALANT if prev.endswith(HALANT) else prev + NUKTA
            else:
                out.append(HALANT + "र")
            continue
        if attachable:
            flush_i()
        attachable = False
        if kind == "H":
            if not in_cluster:
                cluster_start = len(out)
            out.append(val + HALANT)
            in_cluster = True
        elif kind in ("C", "CV"):
            if not in_cluster:
                cluster_start = len(out)
            out.append(val)
            in_cluster = False
            attachable = kind == "C"
            if kind == "CV":
                flush_i()
        elif kind == "HAL":
            out.append(HALANT)
            in_cluster = True
        elif kind == "I":
            pending_i = True
        elif kind in ("REPH", "REPHA"):
            flush_i()
            out.insert(cluster_start, "र" + HALANT)
            if kind == "REPHA":
                out.append("ं")
            in_cluster = False
        else:
            flush_i()
            out.append(val)
            in_cluster = False
    flush_i()
    text = "".join(out)
    # a halant left dangling before a space came from a final explicit halant
    return text


def roundtrip_ok(text: str) -> tuple[bool, str, str]:
    """Convert to DevLys and back; compare with the normalized source (joiners dropped)."""
    want = normalize(text).replace(ZWJ, "").replace(ZWNJ, "")
    got_parts = []
    for s in convert_segments(text):
        got_parts.append(devlys_to_unicode(s.text) if s.converted else s.text)
    got = "".join(got_parts)
    return got == want, want, got


# --------------------------------------------------------------------------

_SELFTEST = {
    "राजस्थान सरकार": "jktLFkku ljdkj",
    "कार्यालय": "dk;kZy;",
    "निर्माण": "fuekZ.k",
    "प्रिय": "fç;",
    "क्रिया": "fØ;k",
    "हिन्दी": "fgUnh",
    "हिंदी": "fganh",
    "पंचायती राज विभाग": "iapk;rh jkt foHkkx",
    "अभियंता": "vfHk;ark",
    "अभियन्ता": "vfHk;Urk",
    "ग्रामीण": "xzkeh.k",
    "कृषि": "—f\"k",
    "दृष्टि": "–f\"V",
    "गृह": "x`g",
    "रुपये": "#i;s",
    "रूप": ":i",
    "पढ़ाई": "i<+kbZ",
    "ऑफिस": "vkWfQl",
    "श्रीमान्": "Jheku~",
    "ट्रेन": "Vªsu",
    "द्वारा": "}kjk",
    "उद्यान": "m|ku",
    "ब्रह्म": "czã",
    "चिह्न": "fpà",
    "शुद्ध": "'kq)",
    "इन्द्र": "bUæ",
    "स्त्री": "L=h",
    "क्षेत्र": "{ks=",
    "ज्ञान": "Kku",
    "राष्ट्र": "jk\"Vª",
    "तत्त्व": "rÙo",
    "उद्देश्य": "mís';",
    "सिद्धि": "flf)",
    "अर्थ": "vFkZ",
    "पूर्व": "iwoZ",
    "सूर्य": "lw;Z",
    "हृदय": "ân;",
    "विद्वान": "fo}ku",
    "संस्कृत": "laL—r",
    "कार्यों": "dk;ks±",
    "ईंट": "b±V",
    "जगत्": "txr~",
    "१२३": "ƒ„…",
    "धर्म।": "/keZA",
}


def _selftest() -> int:
    fails = 0
    for src, want in _SELFTEST.items():
        got = unicode_to_devlys(src)
        ok, w, back = roundtrip_ok(src)
        status = "ok " if got == want and ok else "FAIL"
        if status == "FAIL":
            fails += 1
        print(f"{status} {src} -> {got!r} (want {want!r}) roundtrip={'ok' if ok else back}")
    print(f"{len(_SELFTEST) - fails}/{len(_SELFTEST)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)
    if args[0] == "--selftest":
        sys.exit(_selftest())
    if args[0] == "--reverse":
        print(devlys_to_unicode(" ".join(args[1:])))
    else:
        punct = "keep"
        if args[0] == "--punct-devlys":
            punct, args = "devlys", args[1:]
        print(unicode_to_devlys(" ".join(args), punct=punct))
