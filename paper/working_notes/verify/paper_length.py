"""Length of the paper as submitted for review and as it is now.

  python -I paper/working_notes/verify/paper_length.py

Read-only.  Two measures: whitespace-separated tokens of main.tex, and whitespace-separated
tokens of the text that pdftotext extracts from the PDF (skipped when pdftotext is missing).
These are the figures quoted in paper/VERIFICATION.md (sections 9.4 and 10.6) and in the
response to the reviews.
"""

import shutil
import subprocess
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
PDF_NAME = "carnot_finreason2026_task1_working_notes.pdf"

for label, folder in (("submitted for review", PAPER / "archive" / "submitted_20261102"), ("current", PAPER)):
    source = (folder / "main.tex").read_text(encoding="utf-8")
    start, end = source.index("\\begin{abstract}") + len("\\begin{abstract}"), source.index("\\end{abstract}")
    line = f"{label}: main.tex {len(source.split())} tokens, abstract {len(source[start:end].split())}"
    if shutil.which("pdftotext"):
        text = subprocess.run(["pdftotext", "-enc", "UTF-8", str(folder / PDF_NAME), "-"],
                              capture_output=True, encoding="utf-8", check=True).stdout
        pages = [page for page in text.split("\f") if page.strip()]
        line += f"; PDF text {len(text.split())} tokens on {len(pages)} pages"
    print(line)
