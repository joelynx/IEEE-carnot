"""Count the questions whose worked examples differ between S- and H-mode (questions of the primary-example templates)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]  # repository root
splits = json.load(open(ROOT/"splits/splits_v1.json", encoding="utf-8"))["splits"]
template = {}
for line in (ROOT/"development_files/train_manifest.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        row = json.loads(line); template[row["case_id"]] = row["template_id"]
exemplars = json.load(open(ROOT/"exemplars/r0_exemplars.json", encoding="utf-8"))["exemplars"]
primary = {e["template_id"] for e in exemplars if e["role"] == "primary"}
exemplar_cases = {e["case_id"] for e in exemplars}
tuning_eval = splits["tuning-eval"]
tuning_noex = [c for c in splits["tuning"] if c not in exemplar_cases]
print("tuning-eval", len(tuning_eval), "differ", sum(template[c] in primary for c in tuning_eval))
print("tuning-noex", len(tuning_noex), "differ", sum(template[c] in primary for c in tuning_noex))
