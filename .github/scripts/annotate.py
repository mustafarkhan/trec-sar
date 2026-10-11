#!/usr/bin/env python3
"""Emit a file's tail as a single GitHub Actions annotation (readable via the API without log downloads).

python3 annotate.py notice "Title" file.log [lines] [grep-regex]
"""

import re
import sys

level, title, path = sys.argv[1], sys.argv[2], sys.argv[3]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 60
pattern = re.compile(sys.argv[5]) if len(sys.argv) > 5 else None
try:
    with open(path, errors="replace") as fh:
        lines = fh.read().splitlines()
except FileNotFoundError:
    lines = [f"(missing {path})"]
if pattern:
    lines = [ln for ln in lines if pattern.search(ln)]
text = "\n".join(ln[:240] for ln in lines[-n:]) or "(empty)"
text = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
print(f"::{level} title={title}::{text}")
