"""List the numeric tokens that a revision added to or removed from the paper sources.

  python -I paper/working_notes/verify/number_diff.py <old_dir> <new_dir>

Each directory holds main.tex, tables/*.tex and figures/*.tex.  Read-only.
"""

import re
import sys
from collections import Counter
from pathlib import Path

NUM = re.compile(r"(?<![A-Za-z_\\])[-+]?\d[\d,]*(?:\.\d+)?(?:/\d+)?")


def tokens(root: Path) -> Counter:
    out = Counter()
    for path in [root / "main.tex", *sorted((root / "tables").glob("*.tex")), *sorted((root / "figures").glob("*.tex"))]:
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(?m)^%.*$", "", text)  # comment lines
        for m in NUM.finditer(text):
            out[m.group(0).strip("+").rstrip(",")] += 1
    return out


old, new = tokens(Path(sys.argv[1])), tokens(Path(sys.argv[2]))
added = sorted(k for k in new if k not in old)
removed = sorted(k for k in old if k not in new)
print("added   (", len(added), "):", ", ".join(added))
print("removed (", len(removed), "):", ", ".join(removed))
