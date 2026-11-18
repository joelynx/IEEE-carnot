"""Resumable, bounded R5 pilot. Only training data and new synthetic questions.

Actions: freeze, preflight, author, check, evaluate. Every model-calling action
shares the existing global run lock. No Test or historical lockbox evaluation.
"""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from . import common, exemplars, splits
from .config import load_config, make_sandbox, solver_options, system_prompt_path
from .llm_client import ClaudeCLI, LLMError
from .solver import Solver, load_system_prompt
from .synth.author import parse, topic_examples
from .synth.template import generate, body_limits, TemplateError
from .synth.crosscheck import field_verdicts
from .campaign_integrity import require_preflight, require_family_checks, require_evaluation_identity
from finreason_task1.scoring import score_case

ROOT = common.ROOT / "experiments/improvement_20261020"
PILOT = ROOT / "pilot"
AUTHOR = "claude-fable-5-1"
DESIGNS = [
    ("accounting_and_financial_reporting", "balance_sheets", "intermediate", "Asset impairment with a reversal ceiling and a balance-sheet leverage covenant."),
    ("accounting_and_financial_reporting", "income_statements", "advanced", "Weighted shares, contingent issuance and sequential diluted EPS eligibility."),
    ("corporate_finance", "wacc", "intermediate", "Target financing weights with a capped interest tax shield and flotation costs."),
    ("corporate_finance", "capital_structure", "advanced", "Debt-funded recapitalization with transaction fees, a covenant limit and a self-consistent repurchase price."),
    ("crypto_finance", "tokenomics", "intermediate", "Vesting unlocks, circulating-supply burns and a fully diluted valuation with explicit timing."),
    ("crypto_finance", "defi", "advanced", "Collateral liquidation after an oracle shock, a close-factor cap and a liquidation fee; solve required collateral."),
    ("finance_regulation", "compliance", "intermediate", "Scenario-defined tiered compliance remediation cost with a threshold and a capped credit."),
    ("finance_regulation", "basel", "advanced", "Scenario-defined risk-weighted capital including capped deductions and the minimum equity injection meeting two constraints."),
    ("financial_markets", "forex_trading", "intermediate", "Partly hedged foreign invoice with inverse currency quotation, fees and a signed domestic-cost change."),
    ("financial_markets", "bond_pricing", "advanced", "Amortizing principal with changing coupons, settlement timing and a call-price comparison."),
    ("financial_ratios", "effratio", "intermediate", "Cash released by receivable and inventory changes net of payable financing, with consistent day conventions."),
    ("financial_ratios", "levratio", "advanced", "Minimum equity cash injection and debt repayment under two interacting balance-sheet covenants."),
    ("fintech", "payment_technologies", "intermediate", "Marginal payment processing fee tiers, refunds and a capped monthly rebate."),
    ("fintech", "robo_advisors", "advanced", "Rebalance to a target weight after withdrawals while proportional transaction costs change total assets."),
    ("investment_analysis", "npv", "intermediate", "Staged investment and working-capital release with explicit beginning-versus-end timing."),
    ("investment_analysis", "rar", "advanced", "Two-asset risk target with a hedge, signed correlation and variance in percentage-point squared units."),
    ("mergers_and_acquisitions", "synergies_and_cost_savings", "intermediate", "Savings ramp, one-time integration costs, tax effects and cumulative break-even."),
    ("mergers_and_acquisitions", "deal_structure", "advanced", "Mixed cash/share consideration with a price collar, assumed debt and a contingent earnout."),
    ("personal_finance", "loanrepay", "intermediate", "Partial prepayment with a fee and offset-account interest; calculate the resulting loan cash cost."),
    ("personal_finance", "saveretire", "advanced", "Growing deposits, inflation-adjusted target and a withdrawal at an explicit intra-plan time."),
    ("risk_management", "sensitivity_analysis", "intermediate", "Signed two-factor value shocks with an interaction term and a loss-magnitude final output."),
    ("risk_management", "var", "advanced", "Hedged portfolio variance plus a scenario-defined piecewise capital charge and a risk limit."),
    ("sustainable_finance", "carbon_credits", "intermediate", "Vintage-restricted carbon-credit eligibility, integer purchases and resale of surplus."),
    ("sustainable_finance", "green_bonds", "advanced", "Coupon step-up triggered by emissions performance, baseline recalculation and explicit payment dates."),
]


def save(path, value):
    common.write_bytes_atomic(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def verify_protected():
    record = json.loads((ROOT / "baseline_audit.json").read_text())
    for path, expected in record["protected"].items():
        if common.sha256_file(common.ROOT / path) != expected:
            raise RuntimeError(f"protected baseline changed: {path}")


class StrictCLI(ClaudeCLI):
    def _response(self, payload, key, cached):
        response = super()._response(payload, key, cached)
        if response.model_id != self.model:
            raise LLMError(f"model identity mismatch: requested {self.model}, received {response.model_id}")
        return response


def freeze():
    path = ROOT / "preregistration.json"
    if path.exists():
        raise SystemExit("preregistration exists; do not overwrite")
    verify_protected()
    d = common.data()
    topics = {(r["domain_id"], r["topic_id"]) for r in d.manifest.values()}
    assignments = []
    for i, (domain, topic, difficulty, mechanism) in enumerate(DESIGNS):
        assert (domain, topic) in topics, (domain, topic)
        assignments.append({"index": i, "domain_id": domain, "topic_id": topic, "difficulty": difficulty,
                            "mechanism": mechanism, "panel": "development_pilot", "instances": 4})
    watched = ["configs/r4.json", "configs/r5p.json", "carnot/prompts/pot_system_v1.txt",
               "carnot/prompts/pot_system_v2.txt", "carnot/prompts/synth_author_v4.txt",
               "carnot/solver.py", "carnot/config.py", "carnot/improvement_campaign.py",
               "carnot/synth/template.py", "experiments/improvement_20261020/PROTOCOL.md"]
    save(path, {"at": datetime.now(timezone.utc).isoformat(), "status": "frozen_before_model_calls",
                "assignments": assignments, "hashes": {p: common.sha256_file(common.ROOT / p) for p in watched},
                "author": AUTHOR, "author_effort": "high", "checker": AUTHOR, "checker_effort": "medium",
                "checker_limitations": "Blind independent calls, same model family; not independent human adjudication.",
                "max_author_repairs": 2, "checks_per_family": 4, "candidate_samples": 5,
                "confirmation_opened": False, "fac_noninferiority_margin": 0.001})
    print("Frozen 24-family development pilot and R4/R5-P recipes.", flush=True)


def preflight():
    config = load_config("configs/r4.json")
    model = StrictCLI(config["model"], "medium")
    box = make_sandbox(config)
    cid = splits.load()["tuning-eval"][0]
    d = common.data()
    assert d.source[cid] == "train"
    examples = json.loads((common.ROOT / config["exemplars"]).read_text())
    solver = Solver(model, box, load_system_prompt(system_prompt_path(config)), config["max_retries"],
                    **solver_options(config, "novel"))
    try:
        outcome = solver.solve(d.questions[cid], exemplars.select(examples, d.template(cid), "H"),
                               1, 10000, exclude_template=d.template(cid))
        score = score_case(d.questions[cid], d.gold[cid], outcome["row"])
        save(ROOT / "preflight.json", {"case_id": cid, "llm": model.describe(), "sandbox": box.info,
                                     "fac": score.fac, "matched_slots": score.matched_slots,
                                     "total_slots": score.total_slots, "outcome": outcome})
        print(json.dumps({"preflight_fac": score.fac, "slots": [score.matched_slots, score.total_slots],
                          "backend": model.describe(), "sandbox": box.info}), flush=True)
        if not score.fac or score.matched_slots != score.total_slots:
            raise RuntimeError("training smoke failed; investigate before campaign")
    finally:
        box.close()


def author_one(a):
    directory = PILOT / f"family_{a['index']:02d}"
    if (directory / "instances.jsonl").exists():
        return {"family": a["index"], "status": "already_generated"}
    llm, box = StrictCLI(AUTHOR, "high"), make_sandbox(load_config("configs/r4.json"))
    system = (common.ROOT / "carnot/prompts/synth_author_v4.txt").read_text()
    prompt = json.dumps(a) + f"\nCharacter limit: {body_limits('max')[a['difficulty']]}\n"
    prompt += "Existing tuning templates, for avoiding structural duplication:\n"
    for e in topic_examples(a["domain_id"], a["topic_id"]):
        prompt += json.dumps({"question": e["question"], "difficulty": e["difficulty"]}) + "\n"
    base, attempts = prompt, []
    try:
        for attempt in range(3):
            response = llm.complete(system, prompt, tag=f"r5pilot-author-{a['index']}-{attempt}")
            record = {"cache_key": response.key, "cached": response.cached, "model": response.model_id,
                      "usage": response.usage, "cost_equivalent_usd": response.cost_equivalent_usd}
            attempts.append(record)
            try:
                tpl = parse(response.text)
                for k in ("domain_id", "topic_id", "difficulty"):
                    if tpl.get(k) != a[k]:
                        raise TemplateError(f"wrong assignment {k}")
                # Twelve seeded instantiations test parameter variation, four enter the pilot.
                generated = generate(tpl, "fable_r5", 12, box, rules="v4")
            except TemplateError as exc:
                record["error"] = str(exc)
                save(directory / "author_log.json", {"assignment": a, "attempts": attempts, "status": "repair"})
                prompt = base + "\nPrevious draft:\n" + response.text + "\nValidation error:\n" + str(exc) + "\nReturn a corrected complete JSON template."
                continue
            save(directory / "template.json", tpl)
            common.write_jsonl(directory / "instances.jsonl", [
                {"seed": i.seed, "params": i.params, "question": i.question, "gold": i.gold,
                 "manifest": i.manifest} for i in generated.instances[:4]])
            save(directory / "author_log.json", {"assignment": a, "attempts": attempts, "status": "generated",
                                                "parameter_draws_validated": 12, "rejected_draws": generated.errors,
                                                "template_sha256": common.sha256_file(directory / "template.json")})
            return {"family": a["index"], "status": "generated"}
        return {"family": a["index"], "status": "failed"}
    finally:
        box.close()


def check_one(directory):
    output = directory / "blind_check.json"
    if output.exists():
        previous = json.loads(output.read_text())
        if previous["instances_sha256"] != common.sha256_file(directory / "instances.jsonl"):
            raise RuntimeError(f"{directory.name}: stale blind check")
        return {"family": directory.name, "all_agree": previous["all_agree"]}
    config = load_config("configs/r4.json")
    llm, box = StrictCLI(AUTHOR, "medium"), make_sandbox(config)
    # No author program, parameters, gold or existing examples are supplied to the checker.
    system = load_system_prompt(common.ROOT / "carnot/prompts/pot_system_v2.txt")
    solver = Solver(llm, box, system, 2, hints="v2", echo=True)
    checks = []
    try:
        for item in common.read_jsonl(directory / "instances.jsonl"):
            outcome = solver.solve(item["question"], [], 1, 0)
            texts = outcome["samples"][0]["texts"]
            verdicts = field_verdicts(item["question"], item["gold"], texts)
            checks.append({"case_id": item["question"]["case_id"], "verdicts": verdicts, "outcome": outcome})
            save(directory / "blind_check_partial.json", checks)
        record = {"family": directory.name, "all_agree": all(all(c["verdicts"].values()) for c in checks),
                  "checks": checks, "instances_sha256": common.sha256_file(directory / "instances.jsonl")}
        save(output, record)
        return {"family": directory.name, "all_agree": record["all_agree"]}
    finally:
        box.close()


def evaluate_one(job):
    config_name, directory = job
    output = directory / f"evaluation_{config_name}.json"
    config = load_config(f"configs/{config_name}.json")
    instances_hash = require_family_checks(directory)
    system_hash = common.sha256_file(system_prompt_path(config, "novel"))
    if output.exists():
        prior = json.loads(output.read_text())
        require_evaluation_identity(prior, config["_sha256"], system_hash, instances_hash)
        return {"family": directory.name, "config": config_name, "scores": prior["scores"]}
    checked = json.loads((directory / "blind_check.json").read_text())
    if not checked["all_agree"]:
        raise RuntimeError(f"{directory.name}: unresolved blind-check disagreement")
    config = load_config(f"configs/{config_name}.json")
    settings = config["routing"]["novel"]
    llm, box = StrictCLI(settings["model"], settings["effort"]), make_sandbox(config)
    examples = exemplars.select(json.loads((common.ROOT / config["exemplars"]).read_text()), None, "H")
    solver = Solver(llm, box, load_system_prompt(system_prompt_path(config, "novel")), 2,
                    **solver_options(config, "novel"))
    scores, cases = Counter(), []
    try:
        for item in common.read_jsonl(directory / "instances.jsonl"):
            outcome = solver.solve(item["question"], examples, settings["n_samples"])
            score = score_case(item["question"], item["gold"], outcome["row"])
            scores.update({"cases": 1, "correct_final": score.fac, "matched_slots": score.matched_slots,
                           "total_slots": score.total_slots})
            cases.append({"case_id": item["question"]["case_id"], "fac": score.fac,
                          "matched_slots": score.matched_slots, "total_slots": score.total_slots, "outcome": outcome})
            save(directory / f"evaluation_{config_name}_partial.json", cases)
        save(output, {"config": config_name, "config_sha256": config["_sha256"],
                      "system_sha256": common.sha256_file(system_prompt_path(config, "novel")),
                      "llm": llm.describe(), "scores": dict(scores), "cases": cases,
                      "instances_sha256": common.sha256_file(directory / "instances.jsonl")})
        return {"family": directory.name, "config": config_name, "scores": dict(scores)}
    finally:
        box.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "preflight", "author", "check", "evaluate"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()
    verify_protected()
    lock = common.RunLock(common.RUNS_DIR / ".run.lock", "R5 campaign " + args.action)
    if args.action == "freeze":
        freeze()
        return
    prereg = json.loads((ROOT / "preregistration.json").read_text())
    if args.action == "preflight":
        preflight()
        return
    if not (ROOT / "preflight.json").exists():
        raise SystemExit("training smoke must succeed first")
    require_preflight(json.loads((ROOT / "preflight.json").read_text()))
    if args.action == "author":
        jobs, worker = prereg["assignments"], author_one
    else:
        directories = sorted(p.parent for p in PILOT.glob("family_*/instances.jsonl"))
        if args.action == "check":
            jobs, worker = directories, check_one
        else:
            if len(directories) != len(prereg["assignments"]):
                raise SystemExit("pilot generation incomplete")
            seal = json.loads((ROOT / "execution_seal.json").read_text())
            for path, expected in seal["hashes"].items():
                if common.sha256_file(common.ROOT / path) != expected:
                    raise SystemExit(f"frozen comparison implementation changed: {path}")
            for directory in directories:
                require_family_checks(directory)
            jobs = [(c, p) for p in directories for c in ("r4", "r5p")]
            worker = evaluate_one
    if args.limit:
        jobs = jobs[:args.limit]
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(worker, job) for job in jobs]
        try:
            for future in as_completed(futures):
                print(json.dumps(future.result()), flush=True)
        except BaseException:
            for future in futures:
                future.cancel()
            raise


if __name__ == "__main__":
    main()
