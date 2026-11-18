"""Regenerate every number the Working Notes may use, from the raw logs, data and cache.

  python -I paper/build_facts.py            # writes paper/facts.json and paper/TABLES.md
  python -I paper/build_facts.py --check    # recompute and compare with the stored paper/facts.json

Every value carries its source (file and key).  Rules enforced here, so the paper
cannot break them by accident:
  * lockbox runs are reported as aggregates only (no case-level detail);
  * test runs are reported as package facts only (hashes, completeness, routes),
    never statistics computed from test answers;
  * case-level error analysis comes from tuning runs only.
Read-only: nothing outside paper/ is written.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from carnot import common, splits  # noqa: E402
from carnot.routing import NoveltyRouter  # noqa: E402

OUT_JSON = ROOT / "paper" / "facts.json"
OUT_MD = ROOT / "paper" / "TABLES.md"


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def src(path: str, key: str = "") -> str:
    return f"{path}{'#' + key if key else ''}"


# ---------------------------------------------------------------- data
def data_facts() -> dict:
    d = common.data()
    s = splits.load()
    router = NoveltyRouter()
    manifest = d.manifest
    train, dev = d.ids("train"), d.ids("dev")
    gold_ids = train + dev
    templates = {manifest[c]["template_id"] for c in gold_ids}
    topics = {(manifest[c]["domain_id"], manifest[c]["topic_id"]) for c in gold_ids}
    domains = {manifest[c]["domain_id"] for c in gold_ids}
    tdiff = Counter(manifest[next(c for c in gold_ids if manifest[c]["template_id"] == t)]["difficulty"] for t in templates)
    answer_types, rounding, slot_counts, fields = Counter(), Counter(), Counter(), Counter()
    for c in train:
        q = d.questions[c]
        a = q["answer_spec"]
        answer_types[a["type"]] += 1
        rounding[("enum" if a["type"] == "enum" else a["rounding"]["mode"])] += 1
        slot_counts[len(q["trace_spec"]["slots"])] += 1
    for c in gold_ids:
        q = d.questions[c]
        for spec in [q["answer_spec"]] + [sl["result_spec"] for sl in q["trace_spec"]["slots"]]:
            fields["enum" if spec["type"] == "enum" else spec["rounding"]["mode"]] += 1
    routes = {name: sum(router.is_novel(d.questions[c]) for c in ids)
              for name, ids in (("train", train), ("dev", dev), ("leaderboard", d.ids("leaderboard")), ("test", d.ids("test")),
                                ("lockbox", s["lockbox"]), ("tuning-eval", s["tuning-eval"]))}
    release = json.loads((common.DEV_DIR / "release_manifest.json").read_text(encoding="utf-8"))
    test_release = json.loads((common.TEST_DIR / "test_release_manifest.json").read_text(encoding="utf-8"))
    return {
        "_source": "development_files/*.jsonl, test_questions/*.jsonl (the organiser downloads), splits/splits_v1.json",
        "questions": {"train": len(train), "dev": len(dev), "leaderboard": len(d.ids("leaderboard")), "test": len(d.ids("test"))},
        "templates_seen": len(templates), "topics": len(topics), "domains": len(domains),
        "templates_by_difficulty": dict(sorted(tdiff.items())),
        "train_answer_types": dict(answer_types), "train_final_rounding": dict(rounding),
        "train_slot_count_distribution": {str(k): v for k, v in sorted(slot_counts.items())},
        "train_slot_instances": sum(k * v for k, v in slot_counts.items()),
        "gold_fields_train_dev": dict(fields), "gold_fields_total": sum(fields.values()),
        "routing_novel_counts": routes,
        "test_seen_route": len(d.ids("test")) - routes["test"],
        "splits": {name: len(ids) for name, ids in s.items()},
        "release_ids": {"development": release.get("release_id") or release.get("dataset_version"),
                        "test": test_release.get("release_id") or test_release.get("test_release_id")},
        "release_manifest_sha256": common.verify_release(),
    }


# ---------------------------------------------------------------- runs
def run_facts() -> dict:
    runs = {}
    for r in jl(ROOT / "experiments" / "log.jsonl"):
        score = (r.get("score") or {}).get("scores") or {}
        usage = r.get("usage") or {}
        entry = {
            "config": r["config"], "config_sha256": r["config_sha256"], "split": r["split"], "mode": r["mode"],
            "n_cases": r["n_cases"], "complete": r["complete"], "failures": r.get("failures"),
            "sample_offset": r.get("sample_offset"), "limit": r.get("limit"),
            "fresh_calls": r.get("fresh_calls"), "cached_calls": r.get("cached_calls"),
            "thinking_tokens": usage.get("thinking_tokens"), "output_tokens": usage.get("output_tokens"),
            "cost_equivalent_usd": round(usage.get("cost_equivalent_usd", 0.0), 4),
            "cli_version": (r.get("llm") or {}).get("cli_version"), "model": (r.get("llm") or {}).get("model"),
            "effort": (r.get("llm") or {}).get("effort"),
            "routing": ({k: v for k, v in r["routing"].items() if k in ("rule", "forced", "novel_settings", "by_route")}
                        if r.get("routing") else None),
            "conventions": r.get("conventions"),
            "_source": src("experiments/log.jsonl", r["run_id"]),
        }
        if r["split"] == "test928":
            entry["package"] = {"archive_sha256": r.get("archive_sha256"), "predictions_sha256": r.get("predictions_sha256"),
                                "package_ok": r.get("package_ok")}
            entry["note"] = "test run: package facts only; no statistic from test answers"
        elif r["split"] == "leaderboard580":
            entry["package"] = {"archive_sha256": r.get("archive_sha256"), "predictions_sha256": r.get("predictions_sha256")}
        else:
            entry["seen_fac"] = score.get("seen_fac")
            entry["seen_checkpoint"] = score.get("seen_checkpoint")
            entry["micro"] = (r.get("micro") or {}).get("fac")
            if r["split"] != "lockbox":
                entry["failure_categories"] = r.get("failure_categories")
            else:
                entry["note"] = "lockbox: aggregates only"
        runs[r["run_id"]] = entry
    return runs


def sigma_facts(runs: dict) -> dict:
    ids = ["20261011T184257Z_r0_tuning-eval_S", "20261011T203538Z_r0_tuning-eval_S_rep1", "20261011T204616Z_r0_tuning-eval_S_rep2"]
    fac = [float(runs[i]["seen_fac"]) for i in ids]
    ckpt = [float(runs[i]["seen_checkpoint"]) for i in ids]
    return {"runs": ids, "seen_fac": fac, "seen_checkpoint": ckpt,
            "sigma_fac": statistics.stdev(fac), "sigma_checkpoint": statistics.stdev(ckpt),
            "_source": "experiments/log.jsonl (three R0 tuning-eval replicates with fresh samples; sample std, n-1)"}


def comparison_facts() -> list[dict]:
    out = []
    for c in jl(ROOT / "experiments" / "comparisons.jsonl"):
        out.append({"a": c["a"], "b": c["b"], "split": c["split"], "scheme": c["scheme"], "replicates": c["replicates"],
                    "changed_cases": c["changed_cases"],
                    **{k: {f: c[k][f] for f in ("a", "b", "delta", "delta_exact", "ci95", "sigma_run", "improved", "tied", "worse", "non_inferior")}
                       for k in ("fac", "checkpoint")},
                    "_source": src("experiments/comparisons.jsonl", c.get("recorded_at", ""))})
    return out


# ---------------------------------------------------------------- submissions, lockbox, pre-registration
def submission_facts() -> dict:
    reg = jl(ROOT / "submissions" / "registry.jsonl")
    packaged = [e for e in reg if "event" not in e]
    receipts = [e for e in reg if e.get("event") == "upload_receipt"]
    portal = [e for e in reg if e.get("event") == "portal_response"]
    test_receipts = sorted((e for e in receipts if e["phase"] == "test"), key=lambda e: e["accepted_at"])
    uploaded = {e["archive_sha256"] for e in receipts}
    return {
        "receipts": [{k: e[k] for k in ("phase", "config", "run_id", "archive_sha256", "predictions_jsonl_sha256", "receipt_id", "accepted_at")} for e in receipts],
        "latest_test": {k: test_receipts[-1][k] for k in ("config", "run_id", "archive_sha256", "receipt_id", "accepted_at")},
        "packaged_not_uploaded": sorted({(e["config"], e["split"], e["archive_sha256"]) for e in packaged
                                         if e["archive_sha256"] not in uploaded and e["split"] == "test928"}),
        "development_portal_responses": [
            {"config": next((r["config"] for r in receipts if r["archive_sha256"] == e["archive_sha256"]), None),
             "archive_sha256": e["archive_sha256"], **e["response"]}
            for e in portal if e["phase"] == "development"],
        "development_uploads": sum(1 for e in receipts if e["phase"] == "development"),
        "test_uploads_accepted": len(test_receipts),
        "_source": "submissions/registry.jsonl",
    }


def lockbox_facts() -> dict:
    events = jl(ROOT / "experiments" / "lockbox_access.jsonl")
    looks = [e for e in events if e.get("event") == "lockbox_look"]
    distinct = sorted({e["reason"].split(":")[0] for e in looks})
    return {"drawn": next(e for e in events if e.get("event") == "lockbox_drawn"),
            "access_records": [{k: e[k] for k in ("at", "config", "mode", "reason")} for e in looks],
            "looks_used": len(distinct), "looks_cap": 4, "_source": "experiments/lockbox_access.jsonl"}


def preregistration_facts() -> list[dict]:
    keep = ("event", "kind", "name", "candidate", "at", "pass", "win", "decision", "action", "result", "pass_iff", "win_iff",
            "disclosure", "approved_by_user")
    return [{k: e[k] for k in keep if k in e} | {"_source": "experiments/preregistration.jsonl"}
            for e in jl(ROOT / "experiments" / "preregistration.jsonl")]


# ---------------------------------------------------------------- diagnostics and synthetic set
def diagnostic_facts() -> list[dict]:
    out = []
    for e in jl(ROOT / "experiments" / "diagnostics.jsonl"):
        out.append({"name": e["name"], "verdict": e["verdict"], "target_rate_gain": e["target_rate_gain"],
                    "arms": {k: {f: v[f] for f in ("model", "effort", "target_slot_correct", "target_by_template", "non_target_fields_correct", "votes_target_correct")}
                             for k, v in e["arms"].items()},
                    "_source": src("experiments/diagnostics.jsonl", e["name"])})
    return out


def synth_facts() -> dict:
    out = {}
    runs = jl(ROOT / "synth" / "author_runs.jsonl")
    for rules, root in (("v2", ROOT / "synth"), ("v3", ROOT / "synth" / "v3")):
        mine = [r for r in runs if r.get("rules", "v2") == rules and r["status"] == "ok"]
        latest = {}
        for r in mine:
            latest[r["index"]] = r
        probe = root / "probe_haiku_fable.jsonl"
        cross = root / "crosscheck_fable.jsonl"
        probe_rows = {r["template_id"]: r for r in jl(probe)} if probe.exists() else {}
        cross_rows = {r["template_id"]: r for r in jl(cross)} if cross.exists() else {}
        out[rules] = {
            "templates_authored": len(latest),
            "repairs": sum(r["attempts"] - 1 for r in latest.values()),
            "author_cost_equivalent_usd": round(sum(r["cost_equivalent_usd"] for r in latest.values()), 2),
            "crosscheck_templates_all_agree": sum(not r["flagged"] for r in cross_rows.values()), "crosscheck_templates": len(cross_rows),
            "haiku_probe_trivial": sum(r["trivial"] for r in probe_rows.values()), "haiku_probe_templates": len(probe_rows),
            "_source": f"synth/author_runs.jsonl, {cross.relative_to(ROOT).as_posix()}, {probe.relative_to(ROOT).as_posix()}",
        }
    return out


# ---------------------------------------------------------------- usage from the response cache
def usage_facts() -> dict:
    db = sqlite3.connect(f"file:{(common.CACHE_DIR / 'llm_cache.sqlite3').as_posix()}?mode=ro", uri=True)
    table: dict = defaultdict(lambda: Counter())
    for request, response in db.execute("SELECT request, response FROM calls"):
        req, resp = json.loads(request), json.loads(response)
        key = f"{req['model']} (effort {req['effort']})"
        u = resp.get("usage") or {}
        t = table[key]
        t["calls"] += 1
        t["input_tokens"] += int(u.get("input_tokens") or 0)
        t["cache_read_input_tokens"] += int(u.get("cache_read_input_tokens") or 0)
        t["cache_creation_input_tokens"] += int(u.get("cache_creation_input_tokens") or 0)
        t["output_tokens"] += int(u.get("output_tokens") or 0)
        t["thinking_tokens"] += int(((u.get("output_tokens_details") or {}).get("thinking_tokens")) or 0)
        t["cost_equivalent_usd_x1e4"] += round(float(resp.get("total_cost_usd") or 0) * 1e4)
    rows = {k: {**{f: v for f, v in c.items() if f != "cost_equivalent_usd_x1e4"},
                "cost_equivalent_usd": round(c["cost_equivalent_usd_x1e4"] / 1e4, 2)} for k, c in sorted(table.items())}
    return {"by_model_effort": rows,
            "total_calls": sum(r["calls"] for r in rows.values()),
            "total_cost_equivalent_usd": round(sum(r["cost_equivalent_usd"] for r in rows.values()), 2),
            "note": ("every distinct model call ever made (one cache row per call; a few calls made twice by the duplicate-run "
                     "incident are counted once). Cost is the CLI's list-price equivalent; the runs used a Claude subscription, "
                     "not per-token billing."),
            "_source": "cache/llm_cache.sqlite3 (read-only)"}


# ---------------------------------------------------------------- organiser facts
def organiser_facts() -> dict:
    reply = (ROOT / "experiments" / "organiser_correspondence" / "2026-10-12_reply.txt").read_text(encoding="utf-8")
    baselines = {m.group(1): {"final_answer": m.group(2), "reasoning_steps": m.group(3)}
                 for m in re.finditer(r"•\s*(Lite|Standard|Advanced):\s*([0-9.]+)\s*/\s*([0-9.]+)", reply)}
    return {"baselines_dev_leaderboard": baselines,
            "baseline_citation_rule": "identify by published labels (Lite, Standard, Advanced) and cite https://the-finai.github.io/IEEE-bigdata-cup/task1/leaderboard/; do not attribute them to a particular model",
            "ranking": "descending lexicographic (CombinedFAC, HiddenFAC, CombinedCheckpoint), each quantized to 6 decimal places, round-half-even; combined = seen and hidden strata weighted equally; ties share rank",
            "test_scorer": "finreason_task1/scoring.py, finreason.task1.scorer/2.0.0, toolkit commit 983537c23fbb28c4fb67fb958ffcaf49f9f7c69e",
            "finchain_disclosure_request": "the Working Notes must state which FinChain version was used, how questions were matched to templates and executed, and what FinChain contributed to the predictions",
            "_source": "experiments/organiser_correspondence/2026-10-12_reply.txt"}


# ---------------------------------------------------------------- error analysis (tuning only)
def error_facts(runs: dict) -> dict:
    d = common.data()
    wanted = ["20261011T184257Z_r0_tuning-eval_S", "20261012T051314Z_r1_tuning-eval_S_forced-novel",
              "20261012T065939Z_r2_tuning-eval_S_forced-novel", "20261012T132507Z_r3_tuning-eval_S_forced-novel",
              "20261012T102730Z_e_base_tuning-noex_H", "20261012T105448Z_e_conv_tuning-noex_H", "20261012T125649Z_e_hint_tuning-noex_H",
              "20261012T155533Z_r0_tuning-noex_S", "20261012T163028Z_r4_tuning-noex_S"]
    out = {}
    for run in wanted:
        if runs.get(run, {}).get("split") in ("lockbox", "test928", "leaderboard580"):
            continue  # never case-level outside tuning
        rows = jl(ROOT / "runs" / run / "cases.jsonl")
        misses = Counter()
        finals = Counter()
        for r in rows:
            q, g = d.questions[r["case_id"]], d.gold[r["case_id"]]
            pred = {s["slot_id"]: s["value"] for s in r["row"]["steps"]}
            for sl in q["trace_spec"]["slots"]:
                if pred.get(sl["slot_id"]) != g["slot_values"][sl["slot_id"]]:
                    misses[f"{d.template(r['case_id'])} :: {sl['slot_id']} ({sl['description'].strip()})"] += 1
            if r["fac"] != 1:
                finals[d.template(r["case_id"])] += 1
        out[run] = {"slot_misses_by_template_slot": dict(misses.most_common()), "wrong_finals_by_template": dict(finals.most_common()),
                    "_source": f"runs/{run}/cases.jsonl (tuning data; case-level analysis allowed)"}
    return out


def build() -> dict:
    runs = run_facts()
    return {
        "_about": "Generated by paper/build_facts.py. Every number in the Working Notes must come from here or from the files named in _source.",
        "team": {"name": "carnot", "_source": "PLAN.md §0 D1"},
        "data": data_facts(),
        "runs": runs,
        "sigma_run": sigma_facts(runs),
        "comparisons": comparison_facts(),
        "submissions": submission_facts(),
        "lockbox": lockbox_facts(),
        "preregistration": preregistration_facts(),
        "diagnostics": diagnostic_facts(),
        "synthetic_set": synth_facts(),
        "usage": usage_facts(),
        "organiser": organiser_facts(),
        "error_analysis_tuning": error_facts(runs),
    }


# ---------------------------------------------------------------- tables
def fmt(x, places=6):
    if x is None:
        return "–"
    try:
        return f"{float(Fraction(str(x))):.{places}f}"
    except (ValueError, ZeroDivisionError):
        return str(x)


def tables(f: dict) -> str:
    L = ["# Tables for the Working Notes", "",
         "Generated by `paper/build_facts.py` from the raw logs. Do not edit by hand; regenerate. "
         "Lockbox rows are aggregates only; test rows are package facts only.", ""]
    dd = f["data"]
    L += ["## T1. Data", "", "| Item | Value |", "|---|---|"]
    L += [f"| Questions: train / dev / leaderboard / test | {dd['questions']['train']} / {dd['questions']['dev']} / {dd['questions']['leaderboard']} / {dd['questions']['test']} |",
          f"| Seen templates / topics / domains | {dd['templates_seen']} / {dd['topics']} / {dd['domains']} |",
          f"| Templates by difficulty | {dd['templates_by_difficulty']} |",
          f"| Train answer types | {dd['train_answer_types']} |",
          f"| Train slot instances; slot-count distribution | {dd['train_slot_instances']}; {dd['train_slot_count_distribution']} |",
          f"| Gold fields (train+dev) by rendering | {dd['gold_fields_train_dev']} (total {dd['gold_fields_total']}) |",
          f"| Questions routed *novel* (rule novel_vs_train_v1) | {dd['routing_novel_counts']} |",
          f"| Internal splits | {dd['splits']} |", ""]
    L += ["## T2. Runs with gold scores (official toolkit hierarchical scores)", "",
          "| Run | Config | Split | Mode | n | seen FAC | seen checkpoint | fresh / cached calls | cost-eq $ |", "|---|---|---|---|---|---|---|---|---|"]
    for rid, r in f["runs"].items():
        if "seen_fac" in r and r.get("complete") and not r.get("limit"):
            L.append(f"| `{rid}` | {r['config']} | {r['split']} | {r['mode']} | {r['n_cases']} | {fmt(r['seen_fac'])} | {fmt(r['seen_checkpoint'])} | {r['fresh_calls']} / {r['cached_calls']} | {r['cost_equivalent_usd']} |")
    s = f["sigma_run"]
    L += ["", f"σ_run (R0, three tuning-eval replicates): FAC {s['sigma_fac']:.6f}, checkpoint {s['sigma_checkpoint']:.6f}.", ""]
    L += ["## T3. Pre-registered paired comparisons (B − A; paired bootstrap, B = 10,000)", "",
          "| A | B | Δ FAC | 95% CI | Δ checkpoint | 95% CI | changed (FAC / ckpt) |", "|---|---|---|---|---|---|---|"]
    for c in f["comparisons"]:
        L.append(f"| `{c['a']}` | `{c['b']}` | {c['fac']['delta_exact']} | [{c['fac']['ci95'][0]:+.6f}, {c['fac']['ci95'][1]:+.6f}] | "
                 f"{c['checkpoint']['delta_exact']} | [{c['checkpoint']['ci95'][0]:+.6f}, {c['checkpoint']['ci95'][1]:+.6f}] | "
                 f"{c['changed_cases']['fac']} / {c['changed_cases']['checkpoint']} |")
    sub = f["submissions"]
    L += ["", "## T4. Submissions", "", "| Phase | Config | Receipt | Accepted (UTC) | ZIP SHA-256 |", "|---|---|---|---|---|"]
    L += [f"| {e['phase']} | {e['config']} | `{e['receipt_id']}` | {e['accepted_at']} | `{e['archive_sha256'][:16]}…` |" for e in sub["receipts"]]
    L += ["", f"Latest accepted test submission: **{sub['latest_test']['config']}** (`{sub['latest_test']['receipt_id']}`).",
          f"Packaged test ZIPs never uploaded: {sub['packaged_not_uploaded']}.",
          ""]
    L += ["Development leaderboard results (portal responses, verbatim fields):", ""]
    L += [f"- {r['config']}: Final answer {r['final_answer_score']}, Reasoning steps {r['reasoning_steps_score']}, rank {r['current_rank']} at {r['accepted_at']}"
          for r in sub["development_portal_responses"]]
    L += [""]
    L += ["## T5. Organiser baselines on the development leaderboard (cite by label)", "", "| Baseline | Final answer | Reasoning steps |", "|---|---|---|"]
    L += [f"| {k} | {v['final_answer']} | {v['reasoning_steps']} |" for k, v in f["organiser"]["baselines_dev_leaderboard"].items()]
    L += [f"| carnot {r['config'].upper()} (ours) | {r['final_answer_score']} | {r['reasoning_steps_score']} |"
          for r in sub["development_portal_responses"]]
    L += [""]
    L += ["## T6. Diagnostics and synthetic hidden-like set", ""]
    for g in f["diagnostics"]:
        L.append(f"- `{g['name']}`: verdict {g['verdict']}; " + "; ".join(f"{k}: target {v['target_slot_correct']} {v['target_by_template']}" for k, v in g["arms"].items()))
    for rules, v in f["synthetic_set"].items():
        L.append(f"- Synthetic set rules {rules}: {v['templates_authored']} templates authored ({v['repairs']} repairs, ≈ ${v['author_cost_equivalent_usd']}); "
                 f"blind cross-check all-agree {v['crosscheck_templates_all_agree']}/{v['crosscheck_templates']}; Haiku probe trivial {v['haiku_probe_trivial']}/{v['haiku_probe_templates']}")
    L += ["", "## T7. Model usage (every distinct call, from the response cache)", "",
          "| Model, effort | Calls | Output tokens | Thinking tokens | Cost-eq $ |", "|---|---|---|---|---|"]
    for k, v in f["usage"]["by_model_effort"].items():
        L.append(f"| {k} | {v['calls']} | {v['output_tokens']} | {v['thinking_tokens']} | {v['cost_equivalent_usd']} |")
    L += [f"| **Total** | {f['usage']['total_calls']} | | | {f['usage']['total_cost_equivalent_usd']} |", "", f"_{f['usage']['note']}_", ""]
    L += ["## T8. Residual errors on tuning data (case-level; tuning only)", ""]
    for run, e in f["error_analysis_tuning"].items():
        L.append(f"**`{run}`**: slot misses {sum(e['slot_misses_by_template_slot'].values())}, wrong finals {sum(e['wrong_finals_by_template'].values())}")
        for k, n in list(e["slot_misses_by_template_slot"].items())[:8]:
            L.append(f"- {n} × {k}")
        for k, n in e["wrong_finals_by_template"].items():
            L.append(f"- final wrong {n} × {k}")
        L.append("")
    lb = f["lockbox"]
    L += ["## T9. Lockbox discipline", "", f"Looks used: {lb['looks_used']} of {lb['looks_cap']}.", ""]
    L += [f"- {e['at'][:19]} {e['config']} ({e['mode']}): {e['reason']}" for e in lb["access_records"]]
    return "\n".join(L) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    facts = build()
    text = json.dumps(facts, indent=1, ensure_ascii=False, default=str) + "\n"
    if args.check:
        stored = OUT_JSON.read_text(encoding="utf-8") if OUT_JSON.exists() else ""
        print("facts.json up to date" if stored == text else "facts.json differs from a fresh build: rerun without --check and review the diff")
        return 0 if stored == text else 1
    OUT_JSON.write_bytes(text.encode("utf-8"))
    OUT_MD.write_bytes(tables(facts).encode("utf-8"))
    print(f"wrote {OUT_JSON.relative_to(ROOT)} and {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
