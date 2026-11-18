"""Read-only: draw a stratified sample of TRAIN templates and print each next to its
FinChain (pinned 146eaa8) counterpart for manual comparison. No FinChain code is executed.
Usage: python -I finchain_pairs.py FINCHAIN_TEMPLATES_DIR DEV_DIR [--show N1,N2,...]"""
import ast
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

root, D = Path(sys.argv[1]), Path(sys.argv[2])
src = {}
for p in sorted(root.rglob("*.py")):
    text = p.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name.startswith("template_"):
            src[(p.parent.name, p.stem, n.name[len("template_"):])] = ast.get_source_segment(text, n)

man = [json.loads(l) for l in (D / "train_manifest.jsonl").open(encoding="utf-8")]
qs = {r["case_id"]: r for r in map(json.loads, (D / "train_questions.jsonl").open(encoding="utf-8"))}
gold = {r["case_id"]: r for r in map(json.loads, (D / "train_gold.jsonl").open(encoding="utf-8"))}
by_t = defaultdict(list)
for r in man:
    by_t[r["template_id"]].append(r)

named = defaultdict(list)
for t, rows in by_t.items():
    _, dom, top, name, diff, _ = t.split(".")
    if (dom, top, name) in src:
        named[dom].append((diff, t))
rng = random.Random(2026)
diff_cycle = ["basic", "intermediate", "advanced"]
sample = []
for i, dom in enumerate(sorted(named)):
    want = diff_cycle[i % 3]
    pool = sorted(t for d, t in named[dom] if d == want) or sorted(t for d, t in named[dom])
    sample.append(rng.choice(pool))
print("name-matched templates per domain:", {d: len(v) for d, v in sorted(named.items())})
print("SAMPLE:")
for i, t in enumerate(sample):
    print(i, t)

if "--show" in sys.argv:
    idx = [int(x) for x in sys.argv[sys.argv.index("--show") + 1].split(",")]
    for i in idx:
        t = sample[i]
        _, dom, top, name, diff, _ = t.split(".")
        rows = sorted(by_t[t], key=lambda r: r["case_id"])
        print("\n" + "#" * 100 + f"\n[{i}] {t}")
        for r in rows[:2]:
            q = qs[r["case_id"]]
            print("--- TRAIN", r["case_id"])
            print(q["question"])
            print("answer_spec:", json.dumps(q["answer_spec"]))
            print("slots:", [(s["slot_id"], s["description"], s["result_spec"].get("unit"), s["result_spec"].get("rounding")) for s in q["trace_spec"]["slots"]])
            print("gold:", gold[r["case_id"]]["final_value"], gold[r["case_id"]]["slot_values"])
        print("--- FINCHAIN", dom, top, "template_" + name)
        print(src[(dom, top, name)][:3500])
