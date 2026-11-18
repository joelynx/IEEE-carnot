import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]  # repository root
def jl(p): return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
Q = {r["case_id"]: r for r in jl(ROOT/"development_files/train_questions.jsonl")}
G = {r["case_id"]: r for r in jl(ROOT/"development_files/train_gold.jsonl")}
M = {r["case_id"]: r for r in jl(ROOT/"development_files/train_manifest.jsonl")}
tuning = set(json.load(open(ROOT/"splits/splits_v1.json", encoding="utf-8"))["splits"]["tuning"])
def show(tid, n=1, maxlen=900):
    ids = sorted(c for c in tuning if M[c]["template_id"] == tid)[:n]
    for c in ids:
        q = Q[c]; print("=== ", tid, c)
        print(q["question"][:maxlen])
        print("answer_spec:", q["answer_spec"])
        for s in q["trace_spec"]["slots"]:
            print("  slot", s["slot_id"], "|", s["description"], "|", s["result_spec"], "| gold", G[c]["slot_values"].get(s["slot_id"]))
        print("gold final:", G[c]["final_value"])
show("fp.personal_finance.taxcalc.standard_deduction.basic.v1")
show("fp.investment_analysis.rar.two_asset_perfect_correlation_sd.basic.v1")
show("fp.risk_management.sensitivity_analysis.portfolio_single_factor.basic.v1")
show("fp.investment_analysis.ci.interest_from_known_total.intermediate.v1")
# predictions in runs (tuning data only)
def preds(run, tid, slot=None):
    p = ROOT/"runs"/run/"cases.jsonl"
    for r in jl(p):
        c = r["case_id"]
        if M.get(c, {}).get("template_id") != tid: continue
        row = r["row"]
        fin = row["final_answer"]["value"] if row["final_answer"] else None
        steps = {s["slot_id"]: s["value"] for s in row["steps"]}
        print(run[:30], c, "fac", r["fac"], "pred final", fin, "gold", G[c]["final_value"],
              ("| %s pred %s gold %s" % (slot, steps.get(slot), G[c]["slot_values"].get(slot))) if slot else "")
print("--- e_base taxcalc wrong finals")
for r in jl(ROOT/"runs/20261012T102730Z_e_base_tuning-noex_H/cases.jsonl"):
    if r["fac"] == 0:
        c = r["case_id"]; row = r["row"]
        fin = row["final_answer"]["value"] if row["final_answer"] else None
        print(c, M[c]["template_id"], "pred", fin, "gold", G[c]["final_value"], "slots gold", G[c]["slot_values"])
print("--- R0 tuning-eval S variance/sign/multiplier")
preds("20261011T184257Z_r0_tuning-eval_S", "fp.investment_analysis.rar.two_asset_perfect_correlation_sd.basic.v1", "variance_trace")
preds("20261011T184257Z_r0_tuning-eval_S", "fp.risk_management.sensitivity_analysis.portfolio_single_factor.basic.v1", "factor_ratio_trace")
preds("20261011T184257Z_r0_tuning-eval_S", "fp.investment_analysis.ci.interest_from_known_total.intermediate.v1", "growth_multiplier_trace")
print("--- dimensionless gold values in train (sample of distinct template/slot)")
seen=set()
for c,q in Q.items():
    for s in q["trace_spec"]["slots"]:
        if s["result_spec"].get("unit")=="dimensionless" and (M[c]["template_id"],s["slot_id"]) not in seen:
            seen.add((M[c]["template_id"],s["slot_id"])); print(M[c]["template_id"].split(".")[-3], s["slot_id"], s["description"][:50], "gold", G[c]["slot_values"][s["slot_id"]])
    if q["answer_spec"].get("unit")=="dimensionless" and (M[c]["template_id"],"final") not in seen:
        seen.add((M[c]["template_id"],"final")); print(M[c]["template_id"].split(".")[-3], "FINAL", "gold", G[c]["final_value"])
print("n dimensionless train fields (template,slot) distinct:", len(seen))
