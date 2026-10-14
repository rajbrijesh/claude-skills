---
name: "rajkaj-file-noting"
description: Draft Hindi file notes (टिप्पणी / नोटशीट) on a Rajasthan Government पत्रावली, following state office noting practice for RajKaj e-File or paper files. Reads the main letter and every attachment (typed or scanned PDFs, phone photos, handwritten pages, Word, Excel), transcribes scans with the transcribe skill, builds a chronology, and proposes ready-to-paste notes with page and flag references, alternative notes where the decision can go more than one way, and separate remarks on gaps. Use this whenever the user shares a file, letter, dak or bundle of documents and asks for a note or noting, टिप्पणी, नोटशीट, फ़ाइल नोट, पत्रावली पर नोट, इस फ़ाइल पर नोट लिखो, टिप्पणी प्रस्तावित करो, draft a note on this file, put up the file, or asks what to write on a file, even without the word note. All output is in Hindi (Devanagari).
---

# RajKaj File Noting (राजकाज टिप्पणी)

This skill turns a government file — the main letter plus all its attachments — into suggested file notes (टिप्पणी) the user can paste onto the notesheet in RajKaj e-File or write on a paper file.

**All output is in Hindi, in Devanagari script.** These instructions are in English only for clarity. The notes, the document list and the remarks for the user are all written in Hindi. Rajasthan Government files are noted in Hindi, so an English, Hinglish or Roman-Hindi draft is useless to the user: they would have to retype it. Keep English only where the source itself uses it (a scheme name, a reference number with Latin letters, an English letter being summarised).

The user is typically an engineer or officer in a Rajasthan department who will sign or forward the note. They know noting practice well. What they need from you is speed and accuracy: every page read, every fact traceable to a page, nothing invented.

## Workflow

### 1. Take inventory

List every file with its name, page count and type: typed / scanned / handwritten / photo / table / Word / Excel. Run the bundled script on all the files to do this quickly:

```bash
python <skill-dir>/scripts/inventory.py <file1> <file2> ...
```

It reports page counts, whether each PDF page has a usable text layer, and flags pages that look like legacy Hindi fonts (see step 2). You will show the user a short Hindi version of this list at the end, so they can see nothing was skipped.

### 2. Read every page

Pick the reading path per file:

- **Typed PDF with a Unicode text layer**: extract with `pdftotext -layout`. This is free and exact.
- **Legacy-font PDFs**: many Rajasthan office documents are typed in Kruti Dev, DevLys or Chanakya fonts. Their text layer extracts as Latin gibberish (e.g. `jktLFkku ljdkj` for राजस्थान सरकार). The inventory script flags these. Do not trust that text: treat those pages as images.
- **Scanned PDFs, photos, handwritten pages, and anything flagged above**: use the **transcribe** skill (HandwritingOCR). Extract tables with its `tables` action. Each page costs the user a credit, so do not send pages that already have a good text layer, and follow that skill's rule of asking before submitting more than 5 files.
- **After OCR, spot-check**: render one or two pages (`pdftoppm -r 150 -png -f N -l N file.pdf page`) and look at them with Read. If the Devanagari OCR is poor, read the page images yourself instead.
- **If transcribe is not connected or fails**: read the page images yourself, and say so in the remarks for the user.
- **Word files**: docx skill. **Excel files**: xlsx skill.

Look at the page images, not just the extracted text, wherever there are handwritten minutes, stamps, receipt numbers (आवक क्रमांक/दिनांक) or signatures. OCR often drops these, yet an officer's handwritten "प्रस्तुत करें" or "जाँच करावें" on a letter is often the most decisive line in the file.

Read every page. For a long file, work in batches of 10–20 pages and keep a running facts file in your scratchpad (`facts.md`) as you go. Facts from page 3 are easy to lose by page 80, and the note must not depend on memory.

**Page references.** A Rajasthan पत्रावली has a correspondence side (पत्र-व्यवहार भाग, cited as पृ.सं. 12/प.व्य.) and a notesheet side (टिप्पणी भाग, cited as पृ.सं. 3/टि.). Flags (पताका 'क', 'ख') mark papers put up for reference. If a page shows a file page number (usually handwritten in a corner), use it. If it does not, cite the PDF page instead, labelled clearly as (PDF पृ. 7), and tell the user in the remarks to replace these with file page numbers. Never guess a file page number.

### 3. Extract the facts

For each letter or document, record: number (क्रमांक), date, sender, recipient, subject, gist and page. Also record amounts, sanctions, deadlines, and names with designations. Then sort everything into a chronology.

Copy reference numbers, dates, amounts and names character for character. Officers check these against the file, and one wrong digit makes the whole note untrustworthy.

### 4. Analyse

Answer these for yourself before drafting:

- What is the core issue?
- What action is expected from this office, and by when? Compare any deadline with today's date.
- Which documents are missing or incomplete?
- Where do facts contradict each other? Check dates, names, amounts and lengths across documents. Re-add any totals in code rather than trusting the document's arithmetic.
- Which rules or circulars apply?

**Rules and circulars.** Cite one only if it is in the file, or you know it with certainty. Where the user's memory or project files hold summaries of rules (for example ग्रामीण कार्य निर्देशिका-2025, RTPP Rules 2013, राजस्थान सेवा नियम, CCA Rules 1958), read the relevant one before citing. Otherwise write "नियम-स्थिति का परीक्षण आवश्यक". A wrong rule number in a note does more harm than an honest gap, because it can carry through to an order.

### 5. Draft the note

Read `references/noting-format.md` before drafting. It has the template, standard phrases by purpose, closing lines, and a worked example. The skill drafts the note only; it does not draft a letter to go with it.

The note has these parts, in order:

- विषय
- संदर्भ (letter number and date)
- प्रकरण की पृष्ठभूमि — in chronological order, with a page or flag reference for every fact
- विचारणीय बिन्दु
- नियम / परिपत्र स्थिति
- प्रस्ताव
- A closing line that fits the case, e.g. "अवलोकनार्थ एवं आवश्यक आदेशार्थ प्रस्तुत है।"
- Space for signature, name, designation and date

Write in a proposing, non-directive voice: the note puts facts and a proposal before the officer who decides, so it says "प्रस्तावित है कि …" or "… उचित प्रतीत होता है", never an instruction such as "भिजवाएँ" or "सुनिश्चित करें". `references/noting-format.md` section 7 has the forms to use.

Number the paragraphs continuously (1, 2, 3 …) across these sections, as in normal noting practice. Leave the signature block (name, designation, date) as placeholders; the officer fills it in when signing.

### 6. Humanize

Save the draft notes to a file, then run them through the **humanizer** skill. AI drafts tend to read stiff and repetitive, and humanizer smooths that out. Noting has a fixed vocabulary that officers expect, though, so give humanizer these constraints:

- Improve only the flow of the Hindi. Do not change facts, numbers, dates, reference numbers, names of rules, or technical and legal terms.
- Keep standard noting phrases such as "अवलोकनार्थ प्रस्तुत", "पत्रावली पर उपलब्ध", "प्रस्तावित है".
- Keep the text in Hindi and in formal register. Nothing colloquial.
- Keep the proposing, non-directive voice. Do not turn "प्रस्तावित है कि …" into a command, and do not add instructions to the reader.

Then confirm nothing factual moved:

```bash
python <skill-dir>/scripts/check_facts.py draft.txt humanized.txt
```

It lists any number, date or reference token that was added, dropped or changed. Fix every difference it reports by restoring the original token.

### 7. Final check

Check every reference number, date, amount, name and page reference in the final text against the source pages or your facts file. Check that every sentence is in Hindi, apart from English the source itself uses.

## Output layout in chat

Give everything in Hindi, in this order:

1. **One line** saying what the file is about.
2. **पठित दस्तावेज़** — a compact list of the files read: name, pages, and how each was read (text / OCR / image).
3. **The note(s)** — written as ordinary paragraphs in the chat reply, not inside a code block. Keep the text free of markdown symbols (no `**`, `#`, bullets) so it still copies cleanly into the RajKaj e-File note editor; use the numbered paragraphs of the template. When there are alternative notes, put a plain label line (e.g. "विकल्प 1 : …") before each.
4. **आपके ध्यान हेतु** — remarks for the user only, not part of the note, as short Hindi bullets:
   - illegible or doubtful portions, with file name and page
   - missing attachments and incomplete information
   - factual inconsistencies
   - points the user must decide personally
   - any page references given as PDF page numbers that need replacing

## Rules that never bend

- **Never invent** a letter number, date, amount, name or rule number. Where information is not in the file, write "[पत्रावली में उपलब्ध नहीं]". A note goes up the chain and can become an order; a made-up fact in it is far worse than a visible gap.
- Mark illegible text as **[अपठनीय]** and uncertain readings with **(?)**.
- **Keep the file confidential.** Government files carry personal data of employees, complainants and contractors. Never publish any part of a file or a note as an artifact or a shareable link; give it in chat, or as a file only when asked.
