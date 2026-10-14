---
name: unicode-to-devlys
description: Convert Hindi (Devanagari Unicode / Mangal) text in a .docx into legacy DevLys 010 (Kruti Dev-style ASCII-mapped) encoding, keeping English text, layout, tables, headers/footers and formatting intact. Use whenever the user wants Hindi Word files in DevLys, Kruti Dev, Chanakya-style or "Remington" Hindi font, says Hindi shows as gibberish after changing font to DevLys, or needs a government/court/typing-test document in DevLys 010 - even if they only say "convert this Hindi docx to DevLys".
---

# Unicode Hindi -> DevLys 010 (.docx)

DevLys is an ASCII-mapped font: each glyph (half letters, conjuncts, reph, the pre-base short "ि") sits on an ordinary Latin code point. Changing a run's font to "DevLys 010" without re-encoding yields gibberish, so the text must be re-encoded *and* the font set. DevLys 010 and Kruti Dev 010 share one character map.

## Workflow
1. Locate the source .docx (ask if missing). Never overwrite it; output is `<name>_DevLys.docx`.
2. Run: `python scripts/convert_docx.py input.docx` (options: `-o out.docx`, `--font "DevLys 010"`, `--punct devlys`).
   It edits the XML in place (body, nested tables, headers, footers, footnotes, endnotes, comments, text boxes), splits runs so only U+0900-097F text is re-encoded, copies run formatting, and moves Hindi size/bold/italic (szCs/bCs/iCs) to sz/b/i so the look is unchanged.
3. The script verifies itself: it decodes every DevLys run back to Unicode and compares paragraph by paragraph with the source, and checks that all Latin words/digits are unchanged and outside DevLys runs. Any mismatch is listed - investigate it, don't ignore it.
4. Visual check (recommended): `scripts/render_check.py` draws Unicode beside DevLys using a Kruti Dev 010/DevLys TTF; or alias the font via fontconfig and convert the docx to PDF with LibreOffice. Look for wrong half-letters, reph and short-i placement.
5. Report: output path; conversion status (runs/characters converted); English retained; unsupported items (listed under `unsupported` and `unsupported_elements`: charts/SmartArt text, Devanagari signs with no DevLys glyph, vedic marks).

## Behaviour to know
- Digits, English and punctuation keep their original font by default (`--punct keep`). In DevLys many ASCII keys draw Hindi letters, so converting punctuation is only done on request (`--punct devlys`).
- Devanagari digits and ।, ॥ are converted. Spaces between two Hindi words join the DevLys run.
- A syllable split across two runs (formatting changes mid-word) is converted per run; check such words visually.
- The recipient needs the DevLys 010 font installed; it cannot be embedded here. Hindi looks slightly smaller than Mangal at the same point size - that is the font, not a bug.
- `scripts/devlys_engine.py --selftest` runs 44 checks; `python devlys_engine.py "text"` converts a string, `--reverse` decodes.
