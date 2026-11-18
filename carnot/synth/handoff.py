"""Hand-off package for an author/checker working outside this repo (PLAN.md §4b; non-Claude half).

  python -m carnot.synth.handoff build --name nonclaude_v1 [--force]
  python -m carnot.synth.handoff verify --name nonclaude_v1

build: writes synth/handoff/<name>/ and <name>.zip.  The package holds only what
the external model may see: the v3 house rules, the 25 assignment prompts
(exactly as the Fable author received them), the solving rules, the team's
checking code, a copy of the organiser's validators (contracts.py, scoring.py),
hashed novelty data, and the phase-2 cross-check questions (Fable v3 templates,
seeds 0 and 1, questions only), sealed until phase 1 is complete.  No test,
leaderboard or lockbox text, no gold for phase 2, nothing from R1 or R2.  The
item-to-template key stays here (synth/handoff/<name>_key.json).

verify: runs the package's self-check, checks that its engine reproduces our
Fable v3 instances byte for byte, and walks the phase flow in a scratch copy.
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import shutil
import subprocess
import sys
import tempfile
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

from .. import common, exemplars
from ..config import load_config
from ..routing import signature, skeleton
from ..solver import build_user_prompt
from .author import PROMPTS, SYNTH_DIR, plan_for, rules_root, user_prompt
from .template import body_limits

HANDOFF_DIR = SYNTH_DIR / "handoff"
TOOLS_SRC = Path(__file__).resolve().parent / "handoff_tools"
RULES = "v3"
LIB_FILES = [
    "carnot/__init__.py", "carnot/common.py", "carnot/formatter.py", "carnot/routing.py",
    "carnot/sandbox/executor.py", "carnot/sandbox/finq.py", "carnot/sandbox/policy.py",
    "carnot/sandbox/runner.py", "carnot/sandbox/worker.py",
    "carnot/synth/__init__.py", "carnot/synth/answer_format.py", "carnot/synth/template.py",
    "finreason_task1/contracts.py", "finreason_task1/scoring.py",
]
TOOL_FILES = ["_common.py", "selfcheck.py", "check_template.py", "start_phase2.py", "solve_question.py", "finish.py",
              "sample_template.json"]
ITEM_SEED = "carnot-handoff-items-v1"


def novelty_index() -> dict:
    d = common.data()
    train = [d.questions[c] for c in d.ids("train")]
    return {
        "rule": "novel_vs_train_v1: novel iff neither the number-masked skeleton nor the (slot_id, description) signature occurs in train",
        "skeleton_sha256": sorted({common.sha256_text(skeleton(q["question"])) for q in train}),
        "signature_sha256": sorted({common.sha256_text(common.canonical_json([list(p) for p in signature(q)])) for q in train}),
    }


def phase2_items(source: Path) -> tuple[list[dict], dict]:
    config = load_config("configs/r1.json")
    exemplar_file = json.loads((common.ROOT / config["exemplars"]).read_text(encoding="utf-8"))
    chosen = exemplars.select(exemplar_file, None, "S")
    rows = []
    for directory in sorted(source.glob("syn.*")):
        if (directory / "instances.jsonl").exists():
            rows += [(directory.name, r) for r in common.read_jsonl(directory / "instances.jsonl")[:2]]
    random.Random(ITEM_SEED).shuffle(rows)
    items, key = [], {}
    for n, (tid, row) in enumerate(rows, start=1):
        name = f"item_{n:02d}"
        items.append({"item": name, "case_id": row["question"]["case_id"], "question": row["question"],
                      "prompt": build_user_prompt(row["question"], chosen)})
        key[name] = {"template_id": tid, "seed": row["seed"], "case_id": row["question"]["case_id"]}
    return items, key


def build(name: str, force: bool = False) -> Path:
    out = HANDOFF_DIR / name
    if out.exists():
        if not force:
            raise SystemExit(f"{out} exists; pass --force to rebuild")
        shutil.rmtree(out)
    source = rules_root(RULES) / "fable"
    templates = sorted(source.glob("syn.*"))
    if len(templates) != 25:
        print(f"WARNING: {len(templates)} Fable {RULES} templates found (expected 25); phase 2 will have {2 * len(templates)} items")
    for rel in LIB_FILES:
        target = out / "lib" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(common.ROOT / rel, target)
    for rel in TOOL_FILES:
        (out / "tools").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TOOLS_SRC / rel, out / "tools" / rel)
    for rel in ("INSTRUCTIONS.md", "RUN_INFO.md"):
        shutil.copyfile(TOOLS_SRC / rel, out / rel)
    ref = out / "reference"
    (ref / "assignment_prompts").mkdir(parents=True)
    shutil.copyfile(PROMPTS[RULES], ref / "house_rules.txt")
    shutil.copyfile(common.ROOT / "carnot" / "prompts" / "pot_system_v1.txt", ref / "solving_rules.txt")
    plan = plan_for(RULES)
    assignments = [{k: a[k] for k in ("index", "domain_id", "topic_id", "difficulty")} for a in plan["assignments"]]
    (ref / "assignments.json").write_bytes((json.dumps(assignments, indent=1) + "\n").encode("utf-8"))
    for assignment in plan["assignments"]:
        (ref / "assignment_prompts" / f"assignment_{assignment['index']:02d}.txt").write_bytes(user_prompt(assignment).encode("utf-8"))
    (ref / "novelty_index.json").write_bytes((json.dumps(novelty_index()) + "\n").encode("utf-8"))
    limits = {"p90": body_limits("p90"), "max": body_limits("max")}
    (ref / "length_limits.json").write_bytes((json.dumps(limits) + "\n").encode("utf-8"))
    items, key = phase2_items(source)
    (out / "phase2").mkdir()
    sealed = base64.b64encode(zlib.compress(json.dumps(items, ensure_ascii=False).encode("utf-8"), 9))
    (out / "phase2" / "crosscheck_items.bin").write_bytes(sealed)
    for sub in ("templates", "drafts", "previews", "programs", "solutions", "logs", "work"):
        (out / "outputs" / sub).mkdir(parents=True, exist_ok=True)
        (out / "outputs" / sub / ".keep").write_bytes(b"")
    manifest = [f"{common.sha256_file(p)}  {p.relative_to(out).as_posix()}" for p in sorted(out.rglob("*"))
                if p.is_file() and "outputs" not in p.relative_to(out).parts]
    (out / "MANIFEST.sha256").write_bytes(("\n".join(manifest) + "\n").encode("utf-8"))
    zip_path = HANDOFF_DIR / f"{name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                archive.write(p, f"{name}/{p.relative_to(out).as_posix()}")
    key_record = {"name": name, "built_at": datetime.now(timezone.utc).isoformat(), "rules": RULES,
                  "zip_sha256": common.sha256_file(zip_path), "manifest_sha256": common.sha256_file(out / "MANIFEST.sha256"),
                  "items": key, "fable_templates": [p.name for p in templates]}
    (HANDOFF_DIR / f"{name}_key.json").write_bytes((json.dumps(key_record, indent=1) + "\n").encode("utf-8"))
    print(f"built {out} ({len(manifest)} files), {zip_path.name} sha256 {key_record['zip_sha256']}, {len(items)} phase-2 items")
    return out


def _run(folder: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", *args], cwd=folder, capture_output=True, text=True, encoding="utf-8")


def verify(name: str) -> int:
    out = HANDOFF_DIR / name
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / name
        shutil.copytree(out, work)
        problems = []
        result = _run(work, "tools/selfcheck.py")
        print("selfcheck:", result.stdout.strip() or result.stderr.strip()[-300:])
        if "OK" not in result.stdout:
            problems.append("selfcheck failed")
        # parity: the package's engine reproduces our Fable v3 instances exactly
        parity = ("import sys, json; sys.path.insert(0, 'tools'); import _common as c; e = c.setup_engine(); b = c.sandbox()\n"
                  "tpl = json.load(open(sys.argv[1], encoding='utf-8')); g = e.generate(tpl, 'fable', 6, b, rules='v3'); b.close()\n"
                  "print(json.dumps([[i.question['case_id'], i.gold] for i in g.instances]))")
        same = 0
        sources = sorted((rules_root(RULES) / "fable").glob("syn.*"))
        for directory in sources:
            ours = [[r["question"]["case_id"], r["gold"]] for r in common.read_jsonl(directory / "instances.jsonl")]
            theirs = _run(work, "-c", parity, str(directory / "template.json"))
            same += theirs.returncode == 0 and json.loads(theirs.stdout) == ours
        print(f"engine parity: {same}/{len(sources)} Fable {RULES} templates reproduce our instances byte for byte")
        if same != len(sources):
            problems.append("engine parity")
        # phase flow in the scratch copy: a real v3 template as assignment 00, the rest marked failed
        first = next(d for d in sources if json.load(open(d / "author_log.json", encoding="utf-8"))["assignment"]["index"] == 0)
        shutil.copyfile(first / "template.json", work / "outputs" / "templates" / "assignment_00.json")
        flow = {"check_pass": _run(work, "tools/check_template.py", "outputs/templates/assignment_00.json").stdout.strip()[:80],
                "phase2_refused_early": _run(work, "tools/start_phase2.py").returncode == 2}
        for i in range(1, 25):
            (work / "outputs" / "templates" / f"assignment_{i:02d}.FAILED.md").write_text("scratch test", encoding="utf-8")
        flow["phase2_open"] = _run(work, "tools/start_phase2.py").stdout.strip()[:90]
        (work / "outputs" / "work" / "bad.py").write_text("def solve():\n    return {'final': 1}\n", encoding="utf-8")
        flow["solve_incomplete"] = _run(work, "tools/solve_question.py", "phase2/items/item_01.json", "outputs/work/bad.py").stdout.strip()[:60]
        flow["finish_refused"] = _run(work, "tools/finish.py").returncode == 2
        print("phase flow:", json.dumps(flow, indent=1))
        if not (flow["check_pass"].startswith("PASS") and flow["phase2_refused_early"] and flow["phase2_open"].startswith("Phase 1 complete")
                and flow["solve_incomplete"].startswith("INCOMPLETE") and flow["finish_refused"]):
            problems.append("phase flow")
        forbidden = [p for p in work.rglob("*") if p.is_file() and any(s in p.name for s in ("test_questions", "leaderboard", "lockbox", "_gold"))]
        if forbidden:
            problems.append(f"forbidden files: {forbidden}")
    print("VERIFY:", "PASS" if not problems else f"FAIL {problems}")
    return 0 if not problems else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--name", required=True)
    b.add_argument("--force", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        build(args.name, args.force)
        return 0
    return verify(args.name)


if __name__ == "__main__":
    sys.exit(main())
