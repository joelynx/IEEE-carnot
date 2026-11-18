"""Versioned candidate-evaluation runner for the continuation campaign (PLAN.md Package B).

Composes the frozen R4/R5 components (solver, client, selectors, verifier) without editing them.

  python -m carnot.improvement_validation_v1 panel --kind tuning --split tuning-eval --out <panel.json>
  python -m carnot.improvement_validation_v1 generate --panel <panel.json> --mode S --run-dir <dir> \
      --arms r4,p,d5,x1,v --r4-offset 500 [--routing forced-novel] [--cache-only] [--concurrency 3]
  python -m carnot.improvement_validation_v1 score --run-dir <dir>

Generation reads question files only and writes one record per case and, once every case is
complete, every recipe's predictions.  Scoring is a separate command that loads gold only after
those predictions exist.  Historical lockbox, dev, leaderboard and Test cases are refused, and a
confirmation panel needs a frozen confirmation preregistration naming it.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import common, exemplars, harness, splits
from .config import load_config, make_sandbox, solver_options, system_prompt_path
from .continuation_state_v1 import ROOT as CONTINUATION, verify_accepted, verify_baseline_manifest
from .formatter import build_row, empty_row
from .llm_client import CacheMissError, ClaudeCLI, LLMError, UsageLimitError
from .selection import final_first_complete
from .solver import SampleResult, Solver, load_system_prompt
from .verification import candidate_packet, check_evidence

RUNNER_VERSION = "improvement_validation_v1"
RECIPES_PATH = CONTINUATION / "candidate_recipes.json"
R4_CONFIG, P_CONFIG = "configs/r4.json", "configs/r5p.json"
ROLES_PATH = common.ROOT / "carnot" / "prompts" / "r5_diversity_roles.json"
VERIFIER_PROMPT = common.ROOT / "carnot" / "prompts" / "verify_selection_v1.txt"
VERIFIER_MODEL, EXTRA_MODEL, EFFORT = "claude-opus-5-5", "claude-opus-5-5", "medium"
VERIFIER_TAG, EXTRA_SAMPLE, N_SAMPLES = "r5v-selection-v1", 5, 5
ORDER_SEED = "carnot-continuation-v1-order"
ARMS = ("r4", "p", "d5", "x1", "v")
NEEDS = {"x1": "d5", "v": "d5"}
RECIPES = ("R4", "P", "D", "J", "JB", "X1", "X1C", "V")
RECIPE_ARMS = {"R4": ("r4",), "P": ("p",), "D": ("d5",), "J": ("d5",), "JB": ("d5",),
               "X1": ("d5", "x1"), "X1C": ("d5", "x1"), "V": ("d5", "v")}
# Model groups share weight 1/2 each, split uniformly over their scheduled roles.
JB_WEIGHTS = (Fraction(1, 6), Fraction(1, 6), Fraction(1, 6), Fraction(1, 4), Fraction(1, 4))
FORBIDDEN_SPLITS = ("lockbox", "dev290", "leaderboard580", "test928")
TUNING_KINDS = {"tuning-eval", "tuning-noex"}
IDENTITY_FILES = (
    "carnot/improvement_validation_v1.py", "carnot/solver.py", "carnot/llm_client.py", "carnot/selection.py",
    "carnot/verification.py", "carnot/formatter.py", "carnot/exemplars.py", "carnot/config.py", "carnot/routing.py",
    "carnot/common.py", "carnot/sandbox/executor.py", "carnot/sandbox/worker.py", "carnot/sandbox/runner.py",
    "carnot/sandbox/policy.py", "carnot/sandbox/finq.py", R4_CONFIG, P_CONFIG, "carnot/prompts/pot_system_v1.txt",
    "carnot/prompts/pot_system_v2.txt", "carnot/prompts/r5_diversity_roles.json",
    "carnot/prompts/verify_selection_v1.txt", "exemplars/r0_exemplars.json",
    "experiments/improvement_continuation_20261021/candidate_recipes.json",
)


class StopRun(LLMError):
    """A condition that must stop the whole run rather than one case."""


class ModelMismatch(StopRun):
    pass


def save_json(path: Path, value: Any) -> None:
    common.write_bytes_atomic(path, (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(common.ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else common.ROOT / candidate


# ---------------------------------------------------------------- backend


class StrictClient(ClaudeCLI):
    """The cache key is unchanged; only a response from a different model is refused."""

    def _response(self, payload, key, cached):
        response = super()._response(payload, key, cached)
        if response.model_id != self.model:
            raise ModelMismatch(f"model identity mismatch: requested {self.model}, received {response.model_id}")
        return response


class RoleClient:
    """D5: role k answers sample k with its own model and an appended role instruction.

    With an empty instruction the request is byte-identical to R5-P's sample of that index.
    """

    def __init__(self, roles: Sequence[Mapping[str, Any]], clients: Mapping[str, Any]):
        if len(roles) != N_SAMPLES or any(r["effort"] != EFFORT for r in roles):
            raise ValueError("D5 needs exactly five medium-effort roles")
        self.roles, self.clients = list(roles), clients

    @staticmethod
    def system_for(system: str, role: Mapping[str, Any]) -> str:
        instruction = role["instruction"]
        return system if not instruction else system + "\n\nIndependent derivation role:\n" + instruction

    def complete(self, system, user, sample=0, tag=""):
        role = self.roles[sample]
        return self.clients[role["model"]].complete(self.system_for(system, role), user, sample=sample, tag=tag)


class SavedPoolSolver(Solver):
    """Votes over saved samples plus newly generated ones, with the unchanged Solver.solve rule."""

    def __init__(self, *args, saved, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved = saved

    def solve_sample(self, question, examples, sample, exclude_template=None):
        if sample < len(self.saved):
            saved = self.saved[sample]
            return SampleResult(texts=saved["texts"], issues=saved["issues"], attempts=saved["attempts"])
        return super().solve_sample(question, examples, sample, exclude_template)


# ---------------------------------------------------------------- selectors (no gold, no case IDs)


def fields_of(question: Mapping[str, Any]) -> list[str]:
    return ["final"] + [slot["slot_id"] for slot in question["trace_spec"]["slots"]]


def row_from_texts(question: Mapping[str, Any], texts: Mapping[str, str]) -> dict:
    row, dropped = build_row(question, texts["final"], {k: v for k, v in texts.items() if k != "final"})
    if dropped:
        raise RuntimeError(f"selected complete row failed the validator gate: {dropped}")
    return row


def complete_row_choice(question, samples, fallback_row) -> tuple[dict, dict]:
    """J: carnot.selection.final_first_complete; abstention keeps the field-plurality row."""

    fields = fields_of(question)
    choice = final_first_complete([s["texts"] for s in samples], fields)
    if choice["index"] is None:
        return fallback_row, choice
    texts = samples[choice["index"]]["texts"]
    return row_from_texts(question, {k: texts[k] for k in fields}), choice


def balanced_complete_row(texts_list: Sequence[Mapping[str, str]], fields: Sequence[str],
                          weights: Sequence[Fraction] = JB_WEIGHTS) -> dict:
    """JB: exact role weights pooled over identical complete rows; ties go to the earliest role."""

    if len(texts_list) != len(weights):
        raise ValueError("one weight per scheduled role is required")
    support: dict[tuple, list] = {}
    for index, texts in enumerate(texts_list):
        if not all(f in texts for f in fields):
            continue  # incomplete or failed role: zero weight, not redistributed
        key = tuple(texts[f] for f in fields)
        entry = support.setdefault(key, [Fraction(0), index, []])
        entry[0] += weights[index]
        entry[2].append(index)
    if not support:
        return {"index": None, "reason": "no_complete_row"}
    weight, first, members = max(support.values(), key=lambda e: (e[0], -e[1]))
    return {"index": first, "reason": "balanced_complete_row", "weight": str(weight), "roles": members,
            "rows": len(support)}


def selections(question, d5: Mapping[str, Any], six: Mapping[str, Any] | None,
               verdict: Mapping[str, Any] | None, triggered: bool) -> dict[str, dict]:
    """Every pool-derived recipe from one saved D5 pool (plus the shared sixth sample / verifier call)."""

    samples = d5["samples"]
    fields = fields_of(question)
    out = {"D": {"row": d5["row"]}}
    j_row, j_choice = complete_row_choice(question, samples, d5["row"])
    out["J"] = {"row": j_row, "choice": j_choice}
    jb = balanced_complete_row([s["texts"] for s in samples], fields)
    out["JB"] = ({"row": row_from_texts(question, samples[jb["index"]]["texts"]), "choice": jb}
                 if jb["index"] is not None else {"row": j_row, "choice": jb, "fallback": "J"})
    if six is not None:
        x1c_row, x1c_choice = complete_row_choice(question, six["samples"], six["row"])
        out["X1"] = {"row": six["row"], "triggered": True}
        out["X1C"] = {"row": x1c_row, "choice": x1c_choice, "triggered": True}
    else:
        out["X1"] = {"row": j_row, "triggered": triggered, "fallback": "J"}
        out["X1C"] = {"row": j_row, "triggered": triggered, "fallback": "J"}
    if verdict is not None and verdict.get("selected_original_index") is not None:
        out["V"] = {"row": row_from_texts(question, samples[verdict["selected_original_index"]]["texts"]),
                    "reason": verdict["reason"]}
    else:
        out["V"] = {"row": j_row, "fallback": "J",
                    "reason": verdict["reason"] if verdict else ("no_call" if triggered else "no_complete_disagreement")}
    return out


# ---------------------------------------------------------------- panels and questions


def panel_case_ids(split: str) -> list[str]:
    if split == "tuning-eval":
        return sorted(splits.load()["tuning-eval"])
    if split == "tuning-noex":
        exemplar_ids = {e["case_id"] for e in read_json(common.ROOT / "exemplars/r0_exemplars.json")["exemplars"]}
        return sorted(c for c in splits.load()["tuning"] if c not in exemplar_ids)
    raise ValueError(f"unsupported tuning split {split}")


def forbidden_ids() -> set[str]:
    loaded = splits.load()
    return {c for name in FORBIDDEN_SPLITS for c in loaded[name]}


def tuning_panel(split: str) -> dict:
    ids = panel_case_ids(split)
    return {"panel_id": split, "kind": "tuning", "split": split, "partition": "regression",
            "case_ids": ids, "case_ids_sha256": common.sha256_text("\n".join(ids))}


def load_panel(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    panel = json.loads(raw)
    if common.sha256_text("\n".join(panel["case_ids"])) != panel["case_ids_sha256"]:
        raise RuntimeError("panel case list does not match its hash")
    if len(set(panel["case_ids"])) != len(panel["case_ids"]):
        raise RuntimeError("duplicate case IDs in panel")
    return panel, common.sha256_bytes(raw)


def check_allowed(panel: Mapping[str, Any], confirmation_prereg: Path | None, panel_sha: str, arms) -> None:
    """Research splits only.  Test, leaderboard, dev and lockbox can never be loaded here."""

    ids = set(panel["case_ids"])
    if panel["kind"] == "tuning":
        if panel["split"] not in TUNING_KINDS or not ids <= set(splits.load()["tuning"]):
            raise RuntimeError("tuning panels may contain tuning cases only")
        if ids & forbidden_ids() or panel["case_ids"] != panel_case_ids(panel["split"]):
            raise RuntimeError("tuning panel must equal its frozen split exactly")
    elif panel["kind"] == "synthetic":
        if any(not c.startswith("t1_syn") for c in ids):
            raise RuntimeError("synthetic panels contain synthetic case IDs only")
        if panel["partition"] == "confirmation":
            if confirmation_prereg is None:
                raise RuntimeError("confirmation is sealed: a frozen confirmation preregistration is required")
            prereg = read_json(confirmation_prereg)
            if prereg.get("status") != "frozen" or prereg.get("panel_sha256") != panel_sha \
                    or sorted(prereg.get("arms", [])) != sorted(arms):
                raise RuntimeError("confirmation preregistration does not authorize this panel and arm set")
        elif panel["partition"] not in ("development", "stress"):
            raise RuntimeError(f"unknown synthetic partition {panel['partition']!r}")
    else:
        raise RuntimeError(f"unknown panel kind {panel['kind']!r}")


def load_questions(panel: Mapping[str, Any]) -> tuple[dict[str, dict], dict[str, str | None], dict[str, str]]:
    """Questions, template IDs and question hashes.  Gold files are never opened here."""

    wanted = set(panel["case_ids"])
    questions, templates = {}, {}
    if panel["kind"] == "tuning":
        for row in common.read_jsonl(common.DEV_DIR / "train_questions.jsonl"):
            if row["case_id"] in wanted:
                questions[row["case_id"]] = row
        for row in common.read_jsonl(common.DEV_DIR / "train_manifest.jsonl"):
            if row["case_id"] in wanted:
                templates[row["case_id"]] = row["template_id"]
    else:
        for entry in panel["question_files"]:
            path = common.ROOT / entry["path"]
            if common.sha256_file(path) != entry["sha256"]:
                raise RuntimeError(f"question file changed: {entry['path']}")
            for row in common.read_jsonl(path):
                if row["question"]["case_id"] in wanted:
                    questions[row["question"]["case_id"]] = row["question"]
                    templates[row["question"]["case_id"]] = None  # family exclusion: no exemplar shares a family
    missing = wanted - set(questions)
    if missing:
        raise RuntimeError(f"{len(missing)} panel cases have no question")
    hashes = {c: common.sha256_text(common.canonical_json(q)) for c, q in questions.items()}
    return questions, templates, hashes


def case_order(panel: Mapping[str, Any]) -> list[str]:
    ids = sorted(panel["case_ids"])
    random.Random(f"{ORDER_SEED}#{panel['panel_id']}").shuffle(ids)
    return ids


# ---------------------------------------------------------------- generation


class Generator:
    def __init__(self, arms: Sequence[str], mode: str, r4_offset: int, routing: str, cache_only: bool,
                 synthetic: bool):
        self.arms, self.mode, self.r4_offset, self.routing = tuple(arms), mode, r4_offset, routing
        self.synthetic = synthetic
        self.r4, self.p = load_config(R4_CONFIG), load_config(P_CONFIG)
        self.examples_file = read_json(common.ROOT / self.r4["exemplars"])
        if self.r4["exemplars"] != self.p["exemplars"]:
            raise RuntimeError("R4 and R5-P exemplar files differ")
        self.box = make_sandbox(self.r4)
        self.clients: dict[tuple[str, str], StrictClient] = {}
        novel = self.r4["routing"]["novel"]

        def client(model, effort):
            if (model, effort) not in self.clients:
                c = StrictClient(model, effort)
                c.cache_only = cache_only
                self.clients[(model, effort)] = c
            return self.clients[(model, effort)]

        r4_options, p_options = solver_options(self.r4, "novel"), solver_options(self.p, "novel")
        self.solvers: dict[str, Solver] = {}
        if "r4" in self.arms:
            self.solvers["r4"] = Solver(client(novel["model"], novel["effort"]), self.box,
                                        load_system_prompt(system_prompt_path(self.r4, "novel")),
                                        self.r4["max_retries"], **r4_options)
        self.p_system = load_system_prompt(system_prompt_path(self.p, "novel"))
        if "p" in self.arms:
            pn = self.p["routing"]["novel"]
            self.solvers["p"] = Solver(client(pn["model"], pn["effort"]), self.box, self.p_system,
                                       self.p["max_retries"], **p_options)
        if "d5" in self.arms:
            self.roles = json.loads(ROLES_PATH.read_text(encoding="utf-8"))
            role_clients = {r["model"]: client(r["model"], r["effort"]) for r in self.roles}
            self.solvers["d5"] = Solver(RoleClient(self.roles, role_clients), self.box, self.p_system,
                                        self.p["max_retries"], **p_options)
        self.p_options = p_options
        if "x1" in self.arms:
            self.extra_client = client(EXTRA_MODEL, EFFORT)
        if "v" in self.arms:
            self.verifier = client(VERIFIER_MODEL, EFFORT)
            self.verifier_system = VERIFIER_PROMPT.read_text(encoding="utf-8")
        self.router = self.seen_solver = None
        if routing == "routed":
            from .routing import NoveltyRouter
            self.router = NoveltyRouter()
            self.seen_solver = Solver(client(self.r4["model"], self.r4["effort"]), self.box,
                                      load_system_prompt(system_prompt_path(self.r4)), self.r4["max_retries"],
                                      **solver_options(self.r4, "seen"))

    def describe(self) -> dict:
        return {f"{m}/{e}": c.describe() for (m, e), c in sorted(self.clients.items())}

    def close(self) -> None:
        self.box.close()

    def examples(self, template_id: str | None) -> list[dict]:
        if self.synthetic:
            return exemplars.select(self.examples_file, None, "H")
        return exemplars.select(self.examples_file, template_id, self.mode)

    def run_case(self, question: Mapping[str, Any], template_id: str | None) -> dict:
        examples = self.examples(template_id)
        record: dict[str, Any] = {"exemplars": [e["case_id"] for e in examples]}
        if self.routing == "routed" and not self.router.is_novel(question):
            outcome = self.seen_solver.solve(question, examples, self.r4["n_samples"], 0, exclude_template=template_id)
            record.update(route="seen", seen=outcome,
                          selections={name: {"row": outcome["row"], "route": "seen"} for name in RECIPES})
            return record
        record["route"] = "novel"
        arms: dict[str, Any] = {}
        if "r4" in self.arms:
            arms["r4"] = self.solvers["r4"].solve(question, examples, N_SAMPLES, self.r4_offset,
                                                  exclude_template=template_id)
        if "p" in self.arms:
            arms["p"] = self.solvers["p"].solve(question, examples, N_SAMPLES, 0, exclude_template=template_id)
        if "d5" not in self.arms:
            record["arms"] = arms
            record["selections"] = {name: {"row": arms[a]["row"]} for name, a in (("R4", "r4"), ("P", "p")) if a in arms}
            return record
        d5 = arms["d5"] = self.solvers["d5"].solve(question, examples, N_SAMPLES, 0, exclude_template=template_id)
        candidates, packet = candidate_packet(question, d5["samples"])
        triggered = len(candidates) >= 2
        record["trigger"] = {"triggered": triggered, "complete_distinct_rows": len(candidates),
                             "candidate_original_indices": [c["original_index"] for c in candidates]}
        six = verdict = None
        if triggered and "x1" in self.arms:
            extra = SavedPoolSolver(self.extra_client, self.box, self.p_system, 0, saved=d5["samples"],
                                    **self.p_options)
            six = arms["x1"] = extra.solve(question, examples, N_SAMPLES + 1, exclude_template=template_id)
        if triggered and "v" in self.arms:
            response = self.verifier.complete(self.verifier_system, packet, sample=0, tag=VERIFIER_TAG)
            verdict = check_evidence(response.text, candidates, question, self.box)
            arms["v"] = {"call": {"cache_key": response.key, "cached": response.cached, "model": response.model_id,
                                  "usage": response.usage, "cost_equivalent_usd": response.cost_equivalent_usd,
                                  "meta": response.meta, "raw_response": response.text},
                         "verdict": verdict, "packet_sha256": common.sha256_text(packet)}
        chosen = selections(question, d5, six, verdict, triggered)
        if six is not None:  # keep the shared sixth sample, not a second copy of the saved pool
            arms["x1"] = {"row": six["row"], "votes": six["votes"], "dropped_by_gate": six["dropped_by_gate"],
                          "extra_sample": six["samples"][N_SAMPLES]}
        record["arms"] = arms
        if "r4" in arms:
            chosen["R4"] = {"row": arms["r4"]["row"]}
        if "p" in arms:
            chosen["P"] = {"row": arms["p"]["row"]}
        record["selections"] = {k: v for k, v in chosen.items() if set(RECIPE_ARMS[k]) <= set(self.arms)}
        return record


def identity(panel_sha: str, mode: str, arms, r4_offset: int, routing: str, cli_version: str) -> dict:
    return {"runner": RUNNER_VERSION, "files": {p: common.sha256_file(common.ROOT / p) for p in IDENTITY_FILES},
            "panel_sha256": panel_sha, "mode": mode, "arms": list(arms), "r4_offset": r4_offset,
            "routing": routing, "cli_version": cli_version}


def pending_cases(run_dir: Path, order: Sequence[str], ident_sha: str, qhash: Mapping[str, str]) -> list[str]:
    """Cases still to run; a saved record from another identity or question text fails closed."""

    todo = []
    for case_id in order:
        path = run_dir / "cases" / f"{case_id}.json"
        if path.exists():
            saved = read_json(path)
            if saved["identity_sha256"] != ident_sha or saved["question_sha256"] != qhash[case_id]:
                raise RuntimeError(f"stale case record {case_id}; refusing to mix identities")
            continue
        todo.append(case_id)
    return todo


def recipes_for(arms) -> list[str]:
    return [r for r in RECIPES if set(RECIPE_ARMS[r]) <= set(arms)]


def write_predictions(run_dir: Path, order: Sequence[str], arms) -> dict[str, str]:
    records = {c: read_json(run_dir / "cases" / f"{c}.json") for c in order}
    hashes = {}
    for recipe in recipes_for(arms):
        rows = [records[c]["selections"][recipe]["row"] for c in sorted(order)]
        hashes[recipe] = common.write_jsonl(run_dir / "predictions" / f"{recipe}.jsonl", rows)
    save_json(run_dir / "predictions" / "manifest.json", {"at": now(), "sha256": hashes, "cases": len(order),
                                                          "gold_loaded": False})
    return hashes


def generate(args) -> int:
    panel_path = Path(args.panel)
    panel, panel_sha = load_panel(panel_path)
    arms = [a for a in ARMS if a in set(args.arms.split(","))]
    if len(arms) != len(set(args.arms.split(","))):
        raise SystemExit(f"unknown arm in {args.arms}; choose from {ARMS}")
    for arm, needed in NEEDS.items():
        if arm in arms and needed not in arms:
            raise SystemExit(f"arm {arm} needs arm {needed}")
    if panel["kind"] == "tuning" and args.routing != "forced-novel":
        raise SystemExit("tuning panels are forced-novel stress tests")
    if panel["kind"] == "synthetic" and args.mode != "H":
        raise SystemExit("synthetic panels use fixed H-mode exemplars, as in the pilot")
    check_allowed(panel, Path(args.confirmation_prereg) if args.confirmation_prereg else None, panel_sha, arms)
    try:
        lock = common.RunLock(common.RUNS_DIR / ".run.lock", f"{RUNNER_VERSION} generate {args.run_dir}")  # noqa: F841
    except common.LockHeld as exc:
        raise SystemExit(str(exc))
    verify_accepted()
    verify_baseline_manifest()
    questions, templates, qhash = load_questions(panel)
    run_dir = Path(args.run_dir)
    done, failures, stop_reason, order = 0, {}, None, case_order(panel)
    generator = Generator(arms, args.mode, args.r4_offset, args.routing, args.cache_only, panel["kind"] == "synthetic")
    try:
        cli_version = next(iter(generator.clients.values())).version
        ident = identity(panel_sha, args.mode, arms, args.r4_offset, args.routing, cli_version)
        ident_sha = common.sha256_text(common.canonical_json(ident))
        run_file = run_dir / "run.json"
        if run_file.exists():
            prior = read_json(run_file)
            if prior["identity_sha256"] != ident_sha:
                changed = [k for k in ident if ident[k] != prior["identity"].get(k)]
                raise SystemExit(f"run identity differs from the existing run ({changed}); use a new run directory")
        else:
            save_json(run_file, {"identity": ident, "identity_sha256": ident_sha, "created": now(),
                                 "panel_path": relative(panel_path), "panel": {k: panel[k] for k in panel if k != "case_ids"},
                                 "backends": generator.describe(), "sandbox": None})
        events = run_dir / "events.jsonl"
        common.append_jsonl(events, {"event": "start", "at": now(), "argv": sys.argv[1:], "cache_only": args.cache_only})
        todo = pending_cases(run_dir, order, ident_sha, qhash)
        if args.limit is not None:  # smoke: the first cases of the frozen order, resumable into the full run
            pending = set(todo)
            todo = [c for c in order[: args.limit] if c in pending]
        stop = threading.Event()
        t0 = time.perf_counter()

        def job(case_id):
            if stop.is_set():
                return case_id, None
            record = generator.run_case(questions[case_id], templates.get(case_id))
            record.update(case_id=case_id, question_sha256=qhash[case_id], identity_sha256=ident_sha,
                          completed_at=now())
            save_json(run_dir / "cases" / f"{case_id}.json", record)
            return case_id, record

        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {pool.submit(job, c): c for c in todo}
            for future in as_completed(futures):
                case_id = futures[future]
                try:
                    future.result()
                    done += 1
                except (UsageLimitError, StopRun, CacheMissError) as exc:
                    stop.set()
                    stop_reason = f"{type(exc).__name__}: {exc}"[:500]
                    failures[case_id] = stop_reason
                except Exception as exc:  # noqa: BLE001  (infrastructure failure: resume later)
                    failures[case_id] = f"{type(exc).__name__}: {exc}"[:500]
                if (done + len(failures)) % 10 == 0 or done + len(failures) == len(todo):
                    print(f"[{done + len(failures)}/{len(todo)}] completed={done} failures={len(failures)} "
                          f"elapsed={time.perf_counter() - t0:.0f}s", flush=True)
        if generator.box.info:
            record = read_json(run_file)
            record["sandbox"] = generator.box.info
            save_json(run_file, record)
    finally:
        generator.close()
    complete = all((run_dir / "cases" / f"{c}.json").exists() for c in order)
    common.append_jsonl(events, {"event": "stop", "at": now(), "completed_now": done, "failures": failures,
                                 "stop_reason": stop_reason, "complete": complete})
    summary = {"run_dir": run_dir.as_posix(), "complete": complete, "completed_now": done,
               "failures": len(failures), "stop_reason": stop_reason}
    if complete:
        summary["predictions_sha256"] = write_predictions(run_dir, order, arms)
    print(json.dumps(summary, indent=1))
    return 0 if complete else 3


# ---------------------------------------------------------------- scoring (gold enters only here)


def load_gold(panel: Mapping[str, Any]) -> dict[str, dict]:
    if panel["kind"] == "tuning":
        gold = common.data().gold
        return {c: gold[c] for c in panel["case_ids"]}
    out = {}
    for entry in panel["gold_files"]:
        path = common.ROOT / entry["path"]
        if common.sha256_file(path) != entry["sha256"]:
            raise RuntimeError(f"gold file changed: {entry['path']}")
        for row in common.read_jsonl(path):
            if row["case_id"] in panel["case_ids"]:
                out[row["case_id"]] = row["gold"]
    if set(out) != set(panel["case_ids"]):
        raise RuntimeError("gold does not cover the panel")
    return out


def score(args) -> int:
    from finreason_task1.scoring import score_case

    run_dir = Path(args.run_dir)
    run = read_json(run_dir / "run.json")
    panel, panel_sha = load_panel(resolve(run["panel_path"]))
    if panel_sha != run["identity"]["panel_sha256"]:
        raise SystemExit("panel changed since generation")
    manifest_path = run_dir / "predictions" / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit("predictions are not complete; scoring refuses to load gold")
    manifest = read_json(manifest_path)
    for recipe, expected in manifest["sha256"].items():
        if common.sha256_file(run_dir / "predictions" / f"{recipe}.jsonl") != expected:
            raise SystemExit(f"predictions for {recipe} changed after generation")
    if panel["kind"] == "synthetic" and panel["partition"] == "confirmation" and not args.confirmation_prereg:
        raise SystemExit("confirmation scoring needs its frozen preregistration")
    questions, _, _ = load_questions(panel)
    gold = load_gold(panel)
    ids = sorted(panel["case_ids"])
    result = {"run_dir": run_dir.as_posix(), "scored_at": now(), "panel_sha256": panel_sha,
              "predictions_sha256": manifest["sha256"], "recipes": {}}
    for recipe in manifest["sha256"]:
        rows = common.read_jsonl(run_dir / "predictions" / f"{recipe}.jsonl")
        by_id = {r["case_id"]: r for r in rows}
        if set(by_id) != set(ids):
            raise SystemExit(f"{recipe}: prediction coverage differs from the panel")
        cases = {}
        for c in ids:
            s = score_case(questions[c], gold[c], by_id[c])
            cases[c] = {"fac": s.fac, "matched_slots": s.matched_slots, "total_slots": s.total_slots}
        entry = {"cases": cases, "correct_final": sum(v["fac"] for v in cases.values()),
                 "matched_slots": sum(v["matched_slots"] for v in cases.values()),
                 "total_slots": sum(v["total_slots"] for v in cases.values())}
        if panel["kind"] == "tuning":
            official = harness.score([by_id[c] for c in ids], ids)
            entry["official"] = official["report"]["scores"]
            per = {c["case_id"]: c for c in official["cases"]}
            if any(per[c]["fac"] != cases[c]["fac"] or per[c]["matched_slots"] != cases[c]["matched_slots"] for c in ids):
                raise SystemExit("toolkit per-case scores disagree with score_case")
        result["recipes"][recipe] = entry
    save_json(run_dir / "scores.json", result)
    print(json.dumps({r: {k: v for k, v in e.items() if k != "cases"} for r, e in result["recipes"].items()}, indent=1))
    return 0


# ---------------------------------------------------------------- CLI


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_panel = sub.add_parser("panel")
    p_panel.add_argument("--kind", choices=["tuning"], required=True)
    p_panel.add_argument("--split", choices=sorted(TUNING_KINDS), required=True)
    p_panel.add_argument("--out", required=True)
    p_gen = sub.add_parser("generate")
    p_gen.add_argument("--panel", required=True)
    p_gen.add_argument("--mode", choices=["S", "H"], required=True)
    p_gen.add_argument("--run-dir", required=True)
    p_gen.add_argument("--arms", required=True)
    p_gen.add_argument("--r4-offset", type=int, default=0, choices=[0, 500])
    p_gen.add_argument("--routing", choices=["forced-novel", "routed"], default="forced-novel")
    p_gen.add_argument("--cache-only", action="store_true")
    p_gen.add_argument("--concurrency", type=int, default=3)
    p_gen.add_argument("--confirmation-prereg", default=None)
    p_gen.add_argument("--limit", type=int, default=None, help="smoke: only the first N cases of the frozen order")
    p_score = sub.add_parser("score")
    p_score.add_argument("--run-dir", required=True)
    p_score.add_argument("--confirmation-prereg", default=None)
    args = parser.parse_args(argv)
    if args.command == "panel":
        out = Path(args.out)
        if out.exists():
            raise SystemExit(f"{out} exists; panels are frozen")
        save_json(out, tuning_panel(args.split))
        print(f"wrote {out}")
        return 0
    if args.command == "generate":
        if not 1 <= args.concurrency <= 3:
            raise SystemExit("concurrency is bounded at 3 by the preregistration")
        return generate(args)
    return score(args)


if __name__ == "__main__":
    raise SystemExit(main())
