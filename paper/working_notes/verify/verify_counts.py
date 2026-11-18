import json, sqlite3, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]  # repository root
def jl(p):
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
# test questions: count and slots
tq = jl(ROOT/"test_questions/test_questions.jsonl")
print("test questions", len(tq), "total slots", sum(len(q["trace_spec"]["slots"]) for q in tq),
      "zero-slot", sum(1 for q in tq if not q["trace_spec"]["slots"]))
dq = {}
for name in ("train","dev","leaderboard"):
    p = ROOT/f"development_files/{name}_questions.jsonl"
    if p.exists():
        rows = jl(p); dq[name]=rows
        print(name, "questions", len(rows), "slots", sum(len(q["trace_spec"]["slots"]) for q in rows))
runs = {"r0t":"20261011T193529Z_r0_test928_S","r1t":"20261012T055828Z_r1_test928_S","r3t":"20261012T133458Z_r3_test928_S",
        "r4t":"20261012T165330Z_r4_test928_S","r0l":"20261011T201016Z_r0_leaderboard580_S","r4l":"20261012T164501Z_r4_leaderboard580_S"}
P = {}
for k,r in runs.items():
    p = ROOT/"runs"/r/"predictions.jsonl"
    if p.exists():
        P[k] = {row["case_id"]: row for row in jl(p)}
        rows = P[k].values()
        print(k, "rows", len(P[k]), "null finals", sum(1 for x in rows if x["final_answer"] is None),
              "steps", sum(len(x["steps"]) for x in rows))
    else:
        print(k, "MISSING", p)
def ndiff(a,b):
    return sum(1 for c in P[a] if P[a][c] != P[b].get(c))
for a,b in (("r3t","r4t"),("r1t","r3t"),("r0t","r1t"),("r0l","r4l")):
    if a in P and b in P: print("rows differing", a, b, ndiff(a,b))
# cache model-id check (read-only)
db = sqlite3.connect(f"file:{(ROOT/'cache/llm_cache.sqlite3').as_posix()}?mode=ro", uri=True)
total = mism = nomodel = 0
for req, resp in db.execute("SELECT request, response FROM calls"):
    total += 1
    rq = json.loads(req); rs = json.loads(resp)
    mu = rs.get("modelUsage") or {}
    if not mu: nomodel += 1; continue
    if rq["model"] not in mu or len(mu) != 1: mism += 1
print("cache rows", total, "model-id mismatches", mism, "rows without modelUsage", nomodel)
