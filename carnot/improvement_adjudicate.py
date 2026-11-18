"""Document and repair pilot oracle defects before any candidate evaluation."""

import json
import shutil
from datetime import datetime, timezone
from fractions import Fraction as F

from . import common
from .config import load_config, make_sandbox
from .formatter import render
from .improvement_campaign import ROOT, PILOT, save, verify_protected
from .synth.template import generate


def independent_values(index, shown):
    p = {k: F(v) for k, v in shown.items()}
    if index == 3:
        v, d, n, cap = (p[k] for k in ("V_U", "D0", "N", "LIMIT"))
        fee, tax = p["FEE"] / 100, p["TAX"] / 100
        # Solve the stated debt/equity inequality, then value remaining shares.
        debt = min(p["B_REQ"], (cap * (v - d) - d) / (1 + cap * (1 + fee - tax)))
        equity = v - d - debt * (1 + fee - tax)
        cash = debt * (1 - fee)
        price = (equity + cash) / n
        return {"final": equity / price, "debt_issued": debt,
                "repurchase_price": price, "equity_after": equity}
    circulating = p["MAX_SUPPLY"] * p["CIRC_PCT"] / 100
    before = burned = F(0)
    for month in range(1, 13):
        if month == p["CLIFF"]:
            circulating += p["MAX_SUPPLY"] * p["CLIFF_PCT"] / 100
        elif month > p["CLIFF"]:
            circulating += p["MAX_SUPPLY"] * p["LINEAR_PCT"] / 100
        if month == p["BURN_MONTH"]:
            before = circulating
            burned = circulating * p["BURN_PCT"] / 100
            circulating -= burned
    return {"final": (p["MAX_SUPPLY"] - burned) * p["PRICE"],
            "circ_before_burn": before, "burned_tokens": burned, "circ_end_month_12": circulating}


def repair(index, box):
    directory = PILOT / f"family_{index:02d}"
    if (directory / "adjudication.json").exists():
        return
    archive = directory / "before_adjudication_v1"
    archive.mkdir(exist_ok=True)
    names = ("template.json", "instances.jsonl", "blind_check.json", "blind_check_partial.json",
             "endpoint_check.json", "author_log.json")
    for name in names:
        if not (archive / name).exists():
            shutil.copy2(directory / name, archive / name)
    tpl = json.loads((archive / "template.json").read_text())
    if index == 3:
        old = "    equity_with_cash = V + t * B - f * B - D0\n"
        new = ("    equity_after = V + t * B - f * B - D0 - B\n"
               "    equity_with_cash = equity_after + B * (1 - f)\n")
        assert old in tpl["program"]
        tpl["program"] = tpl["program"].replace(old, new).replace(
            "    equity_after = equity_with_cash - net_proceeds\n", "")
        reason = ("Reference program contradicted the explicit post-repurchase equity definition: "
                  "subtracting net proceeds canceled the fee. Apply the stated equity definition first, "
                  "then add net repurchase cash to derive the self-consistent price. Question unchanged.")
    else:
        old = "Vesting works in whole months:"
        assert old in tpl["question_template"]
        tpl["question_template"] = tpl["question_template"].replace(
            old, "Vesting always uses the initial maximum supply:")
        reason = ("Vesting percentages were ambiguous after the burn reduced maximum supply. "
                  "Specify the initial maximum supply as their fixed base; reference program unchanged.")
    generated = generate(tpl, "fable_r5", 12, box, rules="v4")
    original = list(common.read_jsonl(archive / "instances.jsonl"))
    instances = generated.instances[:4]
    assert [(x.seed, x.params) for x in instances] == [(x["seed"], x["params"]) for x in original]
    for item in generated.instances:
        expected = independent_values(index, item.params)
        assert render(expected["final"], tpl["answer_spec"]).text == item.gold["final_value"]
        for slot in tpl["slots"]:
            key = slot["slot_id"]
            assert render(expected[key], slot["result_spec"]).text == item.gold["slot_values"][key]
    save(directory / "template.json", tpl)
    common.write_jsonl(directory / "instances.jsonl", [
        {"seed": x.seed, "params": x.params, "question": x.question, "gold": x.gold, "manifest": x.manifest}
        for x in instances])
    # Preserve the original check, while allowing the campaign to check the revised data.
    active = directory / "blind_check.json"
    if active.exists():
        active.rename(directory / "blind_check_before_adjudication.json")
    save(directory / "adjudication.json", {
        "at": datetime.now(timezone.utc).isoformat(), "reason": reason,
        "before_candidate_evaluation": True, "seeds_and_parameters_preserved": True,
        "independent_exact_arithmetic_checks": len(generated.instances),
        "original_hashes": {n: common.sha256_file(archive / n) for n in names},
        "revised_hashes": {n: common.sha256_file(directory / n) for n in ("template.json", "instances.jsonl")},
        "requires_fresh_endpoint_and_blind_checks": True})
    print(f"Adjudicated family_{index:02d}; all 12 independent arithmetic checks pass.", flush=True)


def main():
    verify_protected()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 pilot oracle adjudication")
    if (ROOT / "execution_seal.json").exists() or list(PILOT.glob("family_*/evaluation_*.json")):
        raise SystemExit("adjudication must precede all candidate evaluation")
    box = make_sandbox(load_config("configs/r4.json"))
    try:
        for index in (3, 4):
            repair(index, box)
    finally:
        box.close()


if __name__ == "__main__":
    main()
