# Release archives

The files below are too bulky for git. They are built into `_release_assets/` (which is not committed) and are meant to be attached to the GitHub Release of this repository. Each archive is a plain deflate zip whose member paths are relative to the repository root, so unzipping it at the root puts every file in place. Members are stored in sorted order with a fixed timestamp.

| Archive | Bytes | Size | Members | SHA-256 |
|---|---:|---:|---:|---|
| `carnot_response_cache.zip` | 21377382 | 21.38 MB | 1 | `1aa6fb416c8317d53ad519b18d932db9a194e8fa1e01d769954c215a14f052c0` |
| `carnot_runs.zip` | 13994745 | 13.99 MB | 157 | `af27d88050f4a7d7228c13d0bf0af695bd7c144287ded992739d7248de2e2d5a` |
| `carnot_experiment_outputs.zip` | 27915055 | 27.92 MB | 9066 | `df25581567176abde25b5b693160bf2b0f49e543f0fe7e88e3768c62746232e8` |

## Response cache: `carnot_response_cache`

One member, `cache/llm_cache.sqlite3`: a point-in-time snapshot of the model-response cache, taken with the SQLite backup API and compacted with `VACUUM`. Unzip it at the repository root to replay runs without model calls.

- Rows in table `calls`: 69277
- Uncompressed size: 290152448 bytes (290.15 MB)
- SHA-256 of the uncompressed database: `bdc9f06a90d48eb1655ed8702405d0e1ca284bf602cf94040b75e1c1cedbb410`
- `PRAGMA integrity_check`: ok
- Schema: `CREATE TABLE calls (key TEXT PRIMARY KEY, created REAL, request TEXT, response TEXT)`

Each row holds the cache key, the creation time, the request descriptor (model, effort, CLI version, flags version, SHA-256 of the system and user prompts, sample index, tag) and the JSON that the model client received (`carnot/llm_client.py`).

## Runs: `carnot_runs`

The `runs/` directory: 157 files in 38 run directories (120.36 MB uncompressed). A run directory holds `cases.jsonl` (per-case records), `predictions.jsonl`, `summary.json` and, for packaged splits, `submission.zip` (`carnot/run.py`). Lock files are left out.

Run directories for the 928 public test questions (7): `20261011T193529Z_r0_test928_S`, `20261012T055828Z_r1_test928_S`, `20261012T075604Z_r2_test928_S`, `20261012T133458Z_r3_test928_S`, `20261012T165330Z_r4_test928_S`, `replaycheck_r3_test928`, `replaycheck_r4_test928`.

## Experiment outputs: `carnot_experiment_outputs`

Per-case outputs under `experiments/` that are too bulky for git. The rule: a file goes into this archive if it lies in a directory named `cases`, or is named `cases.jsonl`, or is larger than 5000000 bytes; files whose names mark them as pre-registrations, reports, decisions, manifests, amendments or protocols, and all `.md` files, always stay in the git tree.

| Directory | Files | Bytes |
|---|---:|---:|
| `experiments/ablation_zeroshot_20261118/run/` | 1 | 1126284 |
| `experiments/ablation_zeroshot_20261118/smoke/` | 1 | 5516 |
| `experiments/improvement_continuation_20261021/ablations/results/stress1/cases/` | 88 | 4453718 |
| `experiments/improvement_continuation_20261021/ablations/results/wave1/cases/` | 96 | 4593376 |
| `experiments/improvement_continuation_20261021/ablations/results/wave2/cases/` | 96 | 4889432 |
| `experiments/improvement_continuation_20261021/regression/historical_r4_tuning_eval_H/cases/` | 580 | 7001666 |
| `experiments/improvement_continuation_20261021/regression/historical_r4_tuning_eval_S/cases/` | 580 | 7000875 |
| `experiments/improvement_continuation_20261021/regression/tuning_eval_H/cases/` | 580 | 22536944 |
| `experiments/improvement_continuation_20261021/regression/tuning_eval_S/cases/` | 580 | 22548462 |
| `experiments/improvement_continuation_20261021/replay/pilot/run/cases/` | 96 | 4970442 |
| `experiments/safeguard_s2_20261022/replay_proof_S/cases/` | 580 | 13840748 |
| `experiments/safeguard_s2_20261022/tuning_eval_H/cases/` | 580 | 20570598 |
| `experiments/safeguard_s2_20261022/tuning_eval_S/cases/` | 580 | 20582740 |
| `experiments/safeguard_s2_20261022/tuning_noex_H/cases/` | 2314 | 81986853 |
| `experiments/safeguard_s2_20261022/tuning_noex_S/cases/` | 2314 | 82024789 |
