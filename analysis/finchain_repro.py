"""Read-only reproduction check on TRAIN only. FinChain formulas (pinned 146eaa8) are transcribed,
not executed, with FinChain's own float + round(x, 2) intermediate convention, and compared with
competition gold. Usage: python -I finchain_repro.py DEV_DIR"""
import json
import re
import sys
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path

D = Path(sys.argv[1])
man = [json.loads(l) for l in (D / "train_manifest.jsonl").open(encoding="utf-8")]
qs = {r["case_id"]: r for r in map(json.loads, (D / "train_questions.jsonl").open(encoding="utf-8"))}
gold = {r["case_id"]: r for r in map(json.loads, (D / "train_gold.jsonl").open(encoding="utf-8"))}


def cases(tid):
    return [qs[r["case_id"]] for r in man if r["template_id"] == tid]


def q2(x):  # render a FinChain float result the way gold renders a 2-dp final
    return str(Decimal(repr(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def eq_exact(fin_value, gold_text):
    g = Fraction(*map(int, gold_text.split("/"))) if "/" in gold_text else Fraction(Decimal(gold_text))
    return Fraction(Decimal(repr(fin_value))) == g


def report(name, rows):
    fm = sum(r[0] for r in rows)
    sm = sum(r[1] for r in rows)
    st = sum(r[2] for r in rows)
    print(f"{name}: final match {fm}/{len(rows)}; slot match {sm}/{st}")
    for r in rows:
        if not r[0] or r[1] < r[2]:
            print("    mismatch example:", r[3])
            break


NUMS = re.compile(r"-?\d+(?:\.\d+)?")

# 1) Lintner smoothing: target=round(eps*payout,2); new=round(last+adj*(target-last),2); total=round(new*shares,2)
rows = []
for q in cases("fp.corporate_finance.div_policies.dividend_lintner_smoothing.intermediate.v1"):
    eps, pay, last, adj, shares = map(float, NUMS.findall(q["question"])[:5])
    target = round(eps * (pay / 100), 2)
    new = round(last + (adj / 100) * (target - last), 2)
    total = round(new * shares, 2)
    g = gold[q["case_id"]]
    slots_ok = [eq_exact(target, g["slot_values"]["trace_1"]), eq_exact(new, g["slot_values"]["trace_2"])]
    rows.append((q2(total) == g["final_value"], sum(slots_ok), 2, (q2(total), g["final_value"], target, new, g["slot_values"])))
report("dividend_lintner_smoothing", rows)

# 2) DCF 3yr Gordon: FinChain rounds PV(FCFs), PV(TV), EV, net debt, equity to 2 dp
rows = []
for q in cases("fp.mergers_and_acquisitions.valuation_methods.dcf_3yr_gordon_to_equity.advanced.v1"):
    t = q["question"]
    f1, f2, f3 = map(float, re.search(r"are ([\d.]+), ([\d.]+), and ([\d.]+) USD million", t).groups())
    r = float(re.search(r"discount rate is ([\d.]+) percent", t).group(1)) / 100
    g_ = float(re.search(r"terminal growth rate is ([\d.]+) percent", t).group(1)) / 100
    debt = float(re.search(r"total debt is ([\d.]+) USD million", t).group(1))
    cash = float(re.search(r"cash is ([\d.]+) USD million", t).group(1))
    pv = round(f1 / (1 + r) + f2 / (1 + r) ** 2 + f3 / (1 + r) ** 3, 2)
    tv = f3 * (1 + g_) / (r - g_)
    pv_tv = round(tv / (1 + r) ** 3, 2)
    ev = round(pv + pv_tv, 2)
    eq = round(ev - round(debt - cash, 2), 2)
    g = gold[q["case_id"]]
    slots_ok = [eq_exact(tv, g["slot_values"]["trace_1"]), eq_exact(ev, g["slot_values"]["trace_2"])]
    rows.append((q2(eq) == g["final_value"], sum(slots_ok), 2, (q2(eq), g["final_value"], tv, ev, g["slot_values"])))
report("dcf_3yr_gordon_to_equity", rows)

# 3) Dual operational savings: FinChain rounds each saving and the total to 2 dp
rows = []
for q in cases("fp.sustainable_finance.sustainability_reporting.dual_operational_savings.intermediate.v1"):
    t = q["question"]
    ec = float(re.search(r"energy cost (\d+) USD", t).group(1))
    er = float(re.search(r"energy cost \d+ USD.*?reduced by ([\d.]+) percent", t).group(1))
    wc = float(re.search(r"waste-management cost (\d+) USD", t).group(1))
    wr = float(re.search(r"waste-management cost \d+ USD.*?reduced by ([\d.]+) percent", t).group(1))
    es = round(ec * (er / 100), 2)
    ws = round(wc * (wr / 100), 2)
    tot = round(es + ws, 2)
    g = gold[q["case_id"]]
    slots_ok = [eq_exact(es, g["slot_values"]["energy_savings_trace"]), eq_exact(ws, g["slot_values"]["waste_savings_trace"])]
    rows.append((q2(tot) == g["final_value"], sum(slots_ok), 2, (q2(tot), g["final_value"], es, ws, g["slot_values"])))
report("dual_operational_savings", rows)
