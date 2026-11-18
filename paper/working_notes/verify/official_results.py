"""Read the official Task 1 test results (copy saved 2 November 2026) and derive the seen-stratum FAC."""
import json
from fractions import Fraction
from pathlib import Path
d = json.loads((Path(__file__).parent/"official_test_results_20261028.json").read_text(encoding="utf-8"))
print({k: v for k, v in d.items() if not isinstance(v, list)})
rows = d["results"] if "results" in d else next(v for v in d.values() if isinstance(v, list))
me = next(r for r in rows if r["team"] == "carnot")
print("carnot", me, "of", len(rows), "teams")
print("hidden FAC 1.000000:", sum(Fraction(r["hidden_fac"]) == 1 for r in rows))
seen = 2*Fraction(me["combined_fac"]) - Fraction(me["hidden_fac"])
print("derived seen FAC", float(seen), "(each published key is rounded to 6 dp, so +/- 1.5e-6)")
