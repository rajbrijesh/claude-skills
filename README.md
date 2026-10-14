# Claude Skills — राजस्थान सरकारी कामकाज के लिए

Claude (Claude Code, Claude.ai, Cowork) के लिए बनाई गई skills, जो राजस्थान सरकार के दफ़्तरी काम को तेज़ और सटीक बनाती हैं।

## उपलब्ध skills

| Skill | काम |
|---|---|
| [rajkaj-file-noting](skills/rajkaj-file-noting) | पत्रावली (RajKaj e-File या कागज़ी फ़ाइल) पर हिन्दी में टिप्पणी / नोटशीट का प्रारूप तैयार करना |
| [unicode-to-devlys](skills/unicode-to-devlys) | Unicode (Mangal) हिन्दी वाली Word (.docx) फ़ाइल को DevLys 010 / Kruti Dev 010 में बदलना, अंग्रेज़ी और फ़ॉर्मेटिंग जस की तस रखते हुए |

## rajkaj-file-noting

मुख्य पत्र और उसके सभी संलग्नक (टाइप्ड या स्कैन PDF, फ़ोटो, हस्तलिखित पृष्ठ, Word, Excel) पढ़कर यह skill ऐसी टिप्पणी प्रस्तावित करती है जिसे सीधे नोटशीट पर लगाया जा सके।

- हर फ़ाइल की सूची बनाती है और पहचानती है कि कौन-सा पृष्ठ टाइप्ड है, कौन-सा स्कैन, और कौन-सा Kruti Dev / DevLys / Chanakya जैसे पुराने फ़ॉन्ट में है
- हर पृष्ठ पढ़कर तथ्यों का कालक्रम बनाती है
- टिप्पणी इन भागों में: विषय, संदर्भ, प्रकरण की पृष्ठभूमि, विचारणीय बिन्दु, नियम / परिपत्र स्थिति, प्रस्ताव, समापन वाक्य
- हर तथ्य के साथ पृष्ठ या पताका का संदर्भ (पृ.सं. 12/प.व्य., पृ.सं. 3/टि., पताका 'क')
- भाषा सुझावात्मक रहती है ("प्रस्तावित है कि …"), आदेशात्मक नहीं
- कोई क्रमांक, दिनांक, राशि या नियम मनगढ़ंत नहीं; जो जानकारी पत्रावली में नहीं है, वहाँ "[पत्रावली में उपलब्ध नहीं]"
- निर्णय एक से अधिक दिशा में जा सकता हो तो वैकल्पिक टिप्पणियाँ, और कमियों / विरोधाभासों पर अलग से टिप्पणी

### फ़ाइलें

```
skills/rajkaj-file-noting/
├── SKILL.md                    # मुख्य निर्देश
├── references/
│   └── noting-format.md        # टिप्पणी का साँचा, मानक वाक्यांश, समापन वाक्य, काल्पनिक उदाहरण
└── scripts/
    ├── inventory.py            # फ़ाइलों / पृष्ठों की सूची, पुराने फ़ॉन्ट और स्कैन पृष्ठों की पहचान
    └── check_facts.py          # भाषा सुधार के बाद अंक, दिनांक, संदर्भ बदले तो नहीं — इसकी जाँच
```

## unicode-to-devlys

कई सरकारी दफ़्तरों, न्यायालयों और टाइपिंग परीक्षाओं में आज भी DevLys 010 या Kruti Dev 010 फ़ॉन्ट माँगा जाता है। Unicode हिन्दी वाले टेक्स्ट का फ़ॉन्ट सीधे DevLys कर देने से अक्षर बिगड़ जाते हैं, क्योंकि DevLys में हर आकार (आधे अक्षर, संयुक्ताक्षर, रेफ, छोटी इ की मात्रा) एक अलग अंग्रेज़ी कुंजी पर बैठा होता है। यह skill टेक्स्ट को सही ढंग से दोबारा encode करती है और फ़ॉन्ट भी बदलती है।

- मूल फ़ाइल नहीं छेड़ी जाती; नई फ़ाइल `<नाम>_DevLys.docx` बनती है
- केवल हिन्दी (देवनागरी) बदली जाती है; अंग्रेज़ी, अंक और विराम-चिह्न अपने मूल फ़ॉन्ट में रहते हैं
- मुख्य भाग, तालिकाएँ (nested भी), header, footer, footnote, endnote, comment और text box — सब जगह रूपांतरण
- bold, italic और साइज़ वैसे ही रहते हैं
- अपने-आप जाँच: DevLys टेक्स्ट को वापस Unicode में बदलकर हर अनुच्छेद मूल से मिलाया जाता है
- देवनागरी अंक और ।, ॥ भी बदले जाते हैं; जो चिह्न DevLys में नहीं हैं, वे सूची में बताए जाते हैं

```
skills/unicode-to-devlys/
├── SKILL.md
└── scripts/
    ├── devlys_engine.py        # Unicode ⇄ DevLys रूपांतरण इंजन (44 self-tests: --selftest)
    ├── convert_docx.py         # .docx का रूपांतरण और जाँच
    └── render_check.py         # Unicode और DevLys को अगल-बगल चित्र में दिखाकर दृश्य जाँच
```

सीधे कमांड लाइन से भी चलाया जा सकता है:

```
python scripts/convert_docx.py पत्र.docx
python scripts/devlys_engine.py "राजस्थान सरकार"        # jktLFkku ljdkj
python scripts/devlys_engine.py --reverse "jktLFkku"   # राजस्थान
```

ज़रूरतें: Python 3, `lxml`; `render_check.py` के लिए `Pillow` और एक DevLys 010 / Kruti Dev 010 TTF फ़ॉन्ट (फ़ॉन्ट इस repo में शामिल नहीं है)। जिसे फ़ाइल भेजी जाए, उसके कंप्यूटर पर DevLys 010 फ़ॉन्ट इंस्टॉल होना चाहिए।

## इंस्टॉल कैसे करें

**Claude Code — plugin marketplace से**

```
/plugin marketplace add rajbrijesh/claude-skills
/plugin install rajkaj-file-noting@rajbrijesh-skills
/plugin install unicode-to-devlys@rajbrijesh-skills
```

**Claude Code — सीधे कॉपी करके**

`skills/` में से skill का फ़ोल्डर (जैसे `skills/unicode-to-devlys`) `~/.claude/skills/` (सभी प्रोजेक्ट के लिए) या प्रोजेक्ट के `.claude/skills/` में कॉपी करें।

**Claude.ai / Cowork**

skill के फ़ोल्डर की ZIP फ़ाइल बनाकर Claude की settings में custom skill के रूप में अपलोड करें।

## rajkaj-file-noting की ज़रूरतें

- Python 3 और poppler-utils (`pdfinfo`, `pdftotext`, `pdftoppm`)
- वैकल्पिक: `python-docx`, `openpyxl` (Word / Excel फ़ाइलों की सूची के लिए)
- वैकल्पिक skills: स्कैन और हस्तलिखित पृष्ठों के लिए HandwritingOCR की `transcribe` skill, भाषा सुधार के लिए कोई `humanizer` skill, और Word / Excel के लिए `docx` / `xlsx` skills। ये न हों तो Claude पृष्ठों की इमेज स्वयं पढ़ता है।

## गोपनीयता

सरकारी पत्रावलियों में कर्मचारियों, शिकायतकर्ताओं और ठेकेदारों की व्यक्तिगत जानकारी होती है। यह skill टिप्पणी केवल चैट में देती है और पत्रावली की कोई सामग्री सार्वजनिक लिंक या artifact के रूप में प्रकाशित नहीं करती। `noting-format.md` का उदाहरण पूरी तरह काल्पनिक है।

## लाइसेंस

[MIT License](LICENSE) — आप इन skills को उपयोग, कॉपी, संशोधित और आगे वितरित कर सकते हैं, बशर्ते LICENSE की प्रति साथ रहे।

---

## English

**rajkaj-file-noting** drafts Hindi (Devanagari) file notes (टिप्पणी / नोटशीट) on Rajasthan Government files, following state office noting practice for RajKaj e-File or paper files. It reads the main letter and every attachment, builds a chronology, and proposes ready-to-paste notes with page and flag references, alternative notes where the decision can go more than one way, and separate remarks on gaps and inconsistencies. It never invents reference numbers, dates, amounts or rule numbers.

**unicode-to-devlys** converts Hindi (Devanagari Unicode / Mangal) text in a .docx to legacy DevLys 010 / Kruti Dev 010 (ASCII-mapped) encoding, keeping English text, tables, headers/footers and formatting intact. It writes a new `<name>_DevLys.docx`, never overwrites the original, and verifies every paragraph by decoding the output back to Unicode.

Install in Claude Code with `/plugin marketplace add rajbrijesh/claude-skills`, then `/plugin install <skill>@rajbrijesh-skills`, or copy a folder from `skills/` into `~/.claude/skills/`.

Licensed under the [MIT License](LICENSE).
