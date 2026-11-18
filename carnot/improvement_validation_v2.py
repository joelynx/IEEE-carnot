"""Runner v2 for the S2 safeguard: named generator arms with explicit fresh sample offsets.

  python -m carnot.improvement_validation_v2 generate --panel <panel.json> --mode S --run-dir <dir> \
      --arm R4a=r4:700 --arm R4b=r4:710 --arm P=p:720 [--cache-only] [--concurrency 3]
  python -m carnot.improvement_validation_v1 score --run-dir <dir>      # scoring is unchanged

Each arm is NAME=GENERATOR:OFFSET with GENERATOR r4 or p; samples OFFSET..OFFSET+4 on the novel
route, exactly as carnot.run --sample-offset would draw them.  Everything else (panel allowlist,
gold separation, resume, cache-only, model identity, predictions before gold) is imported from v1.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import common
from .config import load_config, make_sandbox, solver_options, system_prompt_path
from .continuation_state_v1 import verify_accepted, verify_baseline_manifest
from .improvement_validation_v1 import (N_SAMPLES, R4_CONFIG, P_CONFIG, StopRun, StrictClient, case_order, check_allowed,
                                        load_panel, load_questions, now, pending_cases, read_json, relative, save_json)
from .exemplars import select as select_exemplars
from .llm_client import CacheMissError, UsageLimitError
from .solver import Solver, load_system_prompt

RUNNER_VERSION = "improvement_validation_v2"
GENERATORS = {"r4": R4_CONFIG, "p": P_CONFIG}
IDENTITY_FILES = ("carnot/improvement_validation_v2.py", "carnot/improvement_validation_v1.py", "carnot/solver.py",
                  "carnot/llm_client.py", "carnot/formatter.py", "carnot/exemplars.py", "carnot/config.py",
                  "carnot/sandbox/executor.py", "carnot/sandbox/worker.py", "carnot/sandbox/runner.py",
                  "carnot/sandbox/policy.py", "carnot/sandbox/finq.py", R4_CONFIG, P_CONFIG,
                  "carnot/prompts/pot_system_v1.txt", "carnot/prompts/pot_system_v2.txt", "exemplars/r0_exemplars.json")


def parse_arms(items) -> list[tuple[str, str, int]]:
    arms = []
    for item in items:
        name, spec = item.split("=", 1)
        generator, offset = spec.split(":", 1)
        if generator not in GENERATORS or not name.isidentifier():
            raise SystemExit(f"bad arm {item!r}")
        arms.append((name, generator, int(offset)))
    names = [a[0] for a in arms]
    offsets = [(a[1], o) for a in arms for o in range(a[2], a[2] + N_SAMPLES)]
    if len(set(names)) != len(names) or len(set(offsets)) != len(offsets):
        raise SystemExit("arm names and (generator, sample identity) pairs must be unique")
    return arms


class Generator:
    def __init__(self, arms, mode: str, cache_only: bool):
        self.arms, self.mode = arms, mode
        self.r4 = load_config(R4_CONFIG)
        self.examples_file = read_json(common.ROOT / self.r4["exemplars"])
        self.box = make_sandbox(self.r4)
        self.clients = {}
        self.solvers = {}
        for name, generator, _ in arms:
            config = load_config(GENERATORS[generator])
            if config["exemplars"] != self.r4["exemplars"]:
                raise RuntimeError("exemplar files differ")
            novel = config["routing"]["novel"]
            key = (novel["model"], novel["effort"])
            if key not in self.clients:
                self.clients[key] = StrictClient(*key)
                self.clients[key].cache_only = cache_only
            self.solvers[name] = Solver(self.clients[key], self.box, load_system_prompt(system_prompt_path(config, "novel")),
                                        config["max_retries"], **solver_options(config, "novel"))

    def describe(self) -> dict:
        return {f"{m}/{e}": c.describe() for (m, e), c in sorted(self.clients.items())}

    def run_case(self, question, template_id) -> dict:
        examples = select_exemplars(self.examples_file, template_id, self.mode)
        arms = {name: self.solvers[name].solve(question, examples, N_SAMPLES, offset, exclude_template=template_id)
                for name, _, offset in self.arms}
        return {"exemplars": [e["case_id"] for e in examples], "route": "novel", "arms": arms,
                "selections": {name: {"row": outcome["row"]} for name, outcome in arms.items()}}


def identity(panel_sha, mode, arms, cli_version) -> dict:
    return {"runner": RUNNER_VERSION, "files": {p: common.sha256_file(common.ROOT / p) for p in IDENTITY_FILES},
            "panel_sha256": panel_sha, "mode": mode, "arms": [list(a) for a in arms], "routing": "forced-novel",
            "cli_version": cli_version}


def write_predictions(run_dir: Path, order, names) -> dict:
    hashes = {}
    records = {c: read_json(run_dir / "cases" / f"{c}.json") for c in order}
    for name in names:
        hashes[name] = common.write_jsonl(run_dir / "predictions" / f"{name}.jsonl",
                                          [records[c]["selections"][name]["row"] for c in sorted(order)])
    save_json(run_dir / "predictions" / "manifest.json", {"at": now(), "sha256": hashes, "cases": len(order),
                                                          "gold_loaded": False})
    return hashes


def generate(args) -> int:
    panel_path = Path(args.panel)
    panel, panel_sha = load_panel(panel_path)
    if panel["kind"] != "tuning":
        raise SystemExit("runner v2 serves the S2 tuning regression only")
    arms = parse_arms(args.arm)
    check_allowed(panel, None, panel_sha, [a[0] for a in arms])
    try:
        lock = common.RunLock(common.RUNS_DIR / ".run.lock", f"{RUNNER_VERSION} generate {args.run_dir}")  # noqa: F841
    except common.LockHeld as exc:
        raise SystemExit(str(exc))
    verify_accepted()
    verify_baseline_manifest()
    questions, templates, qhash = load_questions(panel)
    run_dir = Path(args.run_dir)
    order = case_order(panel)
    generator = Generator(arms, args.mode, args.cache_only)
    done, failures, stop_reason = 0, {}, None
    try:
        ident = identity(panel_sha, args.mode, arms, next(iter(generator.clients.values())).version)
        ident_sha = common.sha256_text(common.canonical_json(ident))
        run_file = run_dir / "run.json"
        if run_file.exists():
            if read_json(run_file)["identity_sha256"] != ident_sha:
                raise SystemExit("run identity differs from the existing run; use a new run directory")
        else:
            save_json(run_file, {"identity": ident, "identity_sha256": ident_sha, "created": now(),
                                 "panel_path": relative(panel_path), "backends": generator.describe()})
        events = run_dir / "events.jsonl"
        common.append_jsonl(events, {"event": "start", "at": now(), "argv": sys.argv[1:], "cache_only": args.cache_only})
        todo = pending_cases(run_dir, order, ident_sha, qhash)
        if args.limit is not None:
            pending = set(todo)
            todo = [c for c in order[: args.limit] if c in pending]
        stop = threading.Event()
        t0 = time.perf_counter()

        def job(case_id):
            if stop.is_set():
                return None
            record = generator.run_case(questions[case_id], templates[case_id])
            record.update(case_id=case_id, question_sha256=qhash[case_id], identity_sha256=ident_sha, completed_at=now())
            save_json(run_dir / "cases" / f"{case_id}.json", record)
            return case_id

        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {pool.submit(job, c): c for c in todo}
            for future in as_completed(futures):
                try:
                    if future.result() is not None:  # skipped jobs after a stop are not counted
                        done += 1
                except (UsageLimitError, StopRun, CacheMissError) as exc:
                    stop.set()
                    stop_reason = f"{type(exc).__name__}: {exc}"[:500]
                    failures[futures[future]] = stop_reason
                except Exception as exc:  # noqa: BLE001
                    failures[futures[future]] = f"{type(exc).__name__}: {exc}"[:500]
                if (done + len(failures)) % 20 == 0:
                    print(f"completed={done} failures={len(failures)} elapsed={time.perf_counter() - t0:.0f}s", flush=True)
    finally:
        generator.box.close()
    complete = all((run_dir / "cases" / f"{c}.json").exists() for c in order)
    common.append_jsonl(run_dir / "events.jsonl", {"event": "stop", "at": now(), "completed_now": done,
                                                   "failures": failures, "stop_reason": stop_reason, "complete": complete})
    summary = {"run_dir": run_dir.as_posix(), "complete": complete, "completed_now": done, "failures": len(failures),
               "stop_reason": stop_reason}
    if complete:
        summary["predictions_sha256"] = write_predictions(run_dir, order, [a[0] for a in arms])
    print(json.dumps(summary, indent=1))
    return 0 if complete else 3


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--panel", required=True)
    g.add_argument("--mode", choices=["S", "H"], required=True)
    g.add_argument("--run-dir", required=True)
    g.add_argument("--arm", action="append", required=True)
    g.add_argument("--cache-only", action="store_true")
    g.add_argument("--concurrency", type=int, default=3)
    g.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)
    if not 1 <= args.concurrency <= 3:
        raise SystemExit("concurrency is bounded at 3")
    return generate(args)


if __name__ == "__main__":
    raise SystemExit(main())
