"""Fixed evaluation splits (PLAN.md §5.3), drawn once and never redrawn.

Pool: train (10 per template) + dev (1 per template) = 11 per template.
  lockbox      = all 290 dev cases + 2 random train cases per template  (870)
  tuning       = the remaining 8 train cases per template              (2,320)
  tuning-eval  = 2 fixed tuning cases per template                       (580)
  tuning-smoke = the first (by case_id) of those two                     (290)
  exemplar-pool= tuning minus tuning-eval (6 per template), the only source
                 of fixed few-shot exemplars, so no evaluated case is ever an
                 exemplar.

Usage:  python -m carnot.splits build     (refuses if splits already exist)
        python -m carnot.splits show
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import defaultdict

from . import common

SPLITS_FILE = common.SPLITS_DIR / "splits_v1.json"
SEED = "carnot-splits-v1"


def build() -> dict:
    d = common.data()
    rng = random.Random(int(hashlib.sha256(SEED.encode()).hexdigest(), 16))
    train_by_template: dict[str, list[str]] = defaultdict(list)
    dev_by_template: dict[str, list[str]] = defaultdict(list)
    for case_id, row in sorted(d.manifest.items()):
        bucket = train_by_template if row["split"] == "train_public" else dev_by_template
        bucket[row["template_id"]].append(case_id)
    lockbox, tuning, tuning_eval, smoke = [], [], [], []
    for template in sorted(train_by_template):
        train_ids = sorted(train_by_template[template])
        assert len(train_ids) == 10 and len(dev_by_template[template]) == 1
        held = sorted(rng.sample(train_ids, 2))
        rest = sorted(set(train_ids) - set(held))
        evaluated = sorted(rng.sample(rest, 2))
        lockbox += dev_by_template[template] + held
        tuning += rest
        tuning_eval += evaluated
        smoke.append(evaluated[0])
    exemplar_pool = sorted(set(tuning) - set(tuning_eval))
    splits = {
        "lockbox": sorted(lockbox),
        "tuning": sorted(tuning),
        "tuning-eval": sorted(tuning_eval),
        "tuning-smoke": sorted(smoke),
        "exemplar-pool": exemplar_pool,
        "dev290": d.ids("dev"),
        "leaderboard580": d.ids("leaderboard"),
        "test928": d.ids("test"),
    }
    assert len(splits["lockbox"]) == 870 and len(splits["tuning"]) == 2320
    assert not set(splits["lockbox"]) & set(splits["tuning"])
    return {
        "seed": SEED,
        "release_manifest_sha256": common.verify_release(),
        "sizes": {name: len(ids) for name, ids in splits.items()},
        "sha256": {name: common.sha256_text("\n".join(ids)) for name, ids in splits.items()},
        "splits": splits,
    }


def load() -> dict[str, list[str]]:
    return json.loads(SPLITS_FILE.read_text(encoding="utf-8"))["splits"]


def main(argv: list[str]) -> int:
    if argv[:1] == ["build"]:
        if SPLITS_FILE.exists():
            print(f"{SPLITS_FILE} already exists; the lockbox is drawn once and never redrawn.")
            return 2
        content = build()
        common.write_bytes_atomic(SPLITS_FILE, (json.dumps(content, indent=1) + "\n").encode())
        common.append_jsonl(
            common.EXPERIMENTS_DIR / "lockbox_access.jsonl",
            {"event": "lockbox_drawn", "seed": SEED, "lockbox_sha256": content["sha256"]["lockbox"],
             "splits_file_sha256": common.sha256_file(SPLITS_FILE)},
        )
        print(json.dumps(content["sizes"]))
        return 0
    if argv[:1] == ["show"]:
        stored = json.loads(SPLITS_FILE.read_text(encoding="utf-8"))
        print(json.dumps({"sizes": stored["sizes"], "sha256": stored["sha256"]}, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
