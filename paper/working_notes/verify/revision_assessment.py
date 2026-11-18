"""Read-only checks supporting the independent review-revision assessment.

No model calls, sandbox executions, or writes. Uses train/development gold,
paper sources, and pdftotext if available. Run from any working directory.
"""

import json
import re
import shutil
import subprocess
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PAPER = ROOT / "paper" / "working_notes"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


for label, folder in (("submitted", PAPER / "archive" / "submitted_20261102"), ("revised", PAPER)):
    source = (folder / "main.tex").read_text(encoding="utf-8")
    counts = {"source_whitespace_tokens": len(source.split())}
    for name, pattern in (
        ("protocol", r"\\section\{Evaluation Methodology\}.*?(?=\\section\{Results\})"),
        ("post_submission", r"\\section\{Post-Submission Investigations\}.*?(?=\\section\{Limitations)"),
        ("abstract", r"\\begin\{abstract\}(.*?)\\end\{abstract\}"),
    ):
        match = re.search(pattern, source, re.S)
        counts[name + "_source_tokens"] = len(match.group().split()) if match else None
    if shutil.which("pdftotext"):
        result = subprocess.run(
            ["pdftotext", "-enc", "UTF-8", str(folder / "carnot_finreason2026_task1_working_notes.pdf"), "-"],
            capture_output=True, encoding="utf-8", check=True,
        )
        counts["pdf_whitespace_tokens"] = len(result.stdout.split())
        counts["pdf_page_tokens"] = [len(page.split()) for page in result.stdout.split("\f") if page.strip()]
    print(label, json.dumps(counts))

counts = Counter()
examples = []
for split in ("train", "dev"):
    data = ROOT / "development_files"
    questions = read_jsonl(data / f"{split}_questions.jsonl")
    gold = {row["case_id"]: row for row in read_jsonl(data / f"{split}_gold.jsonl")}
    for question in questions:
        row = gold[question["case_id"]]
        fields = [(question["answer_spec"], row["final_value"])] + [
            (slot["result_spec"], row["slot_values"][slot["slot_id"]])
            for slot in question["trace_spec"]["slots"]
        ]
        for spec, value in fields:
            if spec["type"] != "decimal" or spec["rounding"]["mode"] != "exact":
                continue
            counts["exact_fields"] += 1
            if "/" in value:
                counts["fraction_strings"] += 1
                continue
            rational = Fraction(value)
            nearest = float(value)
            if Fraction(repr(nearest)) == rational:
                continue
            counts["decimal_repr_mismatches"] += 1
            binary_exact = Fraction(nearest) == rational
            counts["mismatches_exactly_representable_as_binary64"] += binary_exact
            places = len(value.partition(".")[2])
            fixed = format(nearest, f".{places}f")
            fixed_matches = Fraction(fixed) == rational
            counts["mismatches_recovered_by_fixed_decimal_rendering"] += fixed_matches
            if split == "train" and (binary_exact or fixed_matches) and len(examples) < 3:
                examples.append({"gold": value, "repr": repr(nearest), "binary_exact": binary_exact,
                                 "fixed": fixed, "fixed_matches": fixed_matches})
print("float_bound_audit", json.dumps(dict(counts), sort_keys=True))
print("training_value_counterexamples", json.dumps(examples))
