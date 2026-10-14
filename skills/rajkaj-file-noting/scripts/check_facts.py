#!/usr/bin/env python3
"""
Check that rewriting a note (e.g. with the humanizer skill) did not change any
fact-bearing token: numbers, dates, amounts, reference numbers, page and flag
references.

Usage:
    python check_facts.py before.txt after.txt

Exit code 0 when every token matches, 1 when something was added, dropped or
changed. Devanagari digits and ASCII digits are kept distinct on purpose: the
note should reproduce figures exactly as the source wrote them.
"""

import re
import sys
from collections import Counter
from pathlib import Path

# Any run that contains at least one digit (ASCII or Devanagari), together with
# the joining characters used in dates, amounts and reference numbers.
TOKEN = re.compile(
    r"[\wऀ-ॿ./()\-–,:]*[0-9०-९][\wऀ-ॿ./()\-–,:]*"
)
# Flag references like पताका 'क'
FLAG = re.compile(r"पताका\s*['‘’\"]?\s*([क-ह])")
STRIP = ".,:;()–-"


def tokens(text):
    found = Counter()
    for t in TOKEN.findall(text):
        t = t.strip(STRIP)
        if t:
            found[t] += 1
    for f in FLAG.findall(text):
        found[f"पताका '{f}'"] += 1
    return found


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    before = tokens(Path(sys.argv[1]).read_text(encoding="utf-8"))
    after = tokens(Path(sys.argv[2]).read_text(encoding="utf-8"))

    dropped = before - after
    added = after - before
    if not dropped and not added:
        print(f"OK: all {sum(before.values())} fact tokens unchanged.")
        sys.exit(0)

    if dropped:
        print("DROPPED or CHANGED (in before, missing after):")
        for t, n in sorted(dropped.items()):
            print(f"  {t}" + (f"  x{n}" if n > 1 else ""))
    if added:
        print("ADDED (in after, not in before):")
        for t, n in sorted(added.items()):
            print(f"  {t}" + (f"  x{n}" if n > 1 else ""))
    print("\nRestore the original tokens in the rewritten text, then run again.")
    sys.exit(1)


if __name__ == "__main__":
    main()
