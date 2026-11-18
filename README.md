# carnot: FinReason Cup 2026 Task 1

Repository: https://github.com/joelynx/IEEE-carnot

Licence: MIT, see `LICENSE`. It covers the team's own code, prompts, configurations and records. Two things keep their own terms: the material from the organisers' release described under "Organisers' data inside these files" (CC BY 4.0), and the Working Notes paper with its sources under `paper/working_notes/`, whose copyright may pass to the publisher of the proceedings.

This repository holds the materials behind team carnot's Task 1 Working Notes for the FinReason Cup 2026: the code, prompts, configurations, few-shot exemplars, data splits, experiment logs, per-case run records, paper sources and the model-response cache. `paper/README.md` describes the paper folder. `paper/REPLAY_CHECK.md` records that the R3 and R4 test submissions (it labels R4 the final submission) were regenerated from the response cache with 0 fresh model calls, and that each regenerated ZIP was byte-identical to the uploaded file.

## Layout

| Path | Contents |
|---|---|
| `carnot/` | The system: `carnot/run.py` runs a frozen configuration on a split, scores or packages it and logs it; prompts are in `carnot/prompts/`, the sandbox in `carnot/sandbox/`, unit tests in `carnot/tests/`. |
| `configs/` | Frozen run configurations (JSON). |
| `exemplars/` | The few-shot exemplar file that the configurations name. |
| `splits/` | The data splits, as lists of case identifiers with their hashes. |
| `synth/` | Synthetic question templates with their instances, review and cross-check records. |
| `analysis/` | Read-only analysis scripts; see `analysis/README.md`. |
| `experiments/` | Experiment logs: run log, results table, pre-registrations, comparisons, reports and decisions. Per-case outputs are in the `carnot_experiment_outputs` release archive. |
| `submissions/` | `registry.jsonl`, the registry of packaged and uploaded submission files. |
| `paper/` | Working-notes sources and the files they were written from; see `paper/README.md`. |
| `cache/sysprompts/` | The system prompts sent to the model, each stored under its SHA-256. |
| `ARTIFACTS.md` | The release archives: name, size, SHA-256 and contents. |
| `MANIFEST.sha256` | SHA-256 of every file in this git tree. |

Bulky files are not in git. They are zip archives attached to the GitHub Release of this repository:

- `carnot_response_cache.zip`
- `carnot_runs.zip`
- `carnot_experiment_outputs.zip`

`ARTIFACTS.md` gives the size, SHA-256 and contents of each archive. `MANIFEST.sha256` lists the SHA-256 of every file in the git tree, in the format that `sha256sum -c MANIFEST.sha256` reads. `.gitattributes` switches off line-ending conversion so that the files keep those hashes on every platform.

## How to reproduce the R3 and R4 test submissions

1. **Organisers' toolkit.** Clone the organisers' repository, https://github.com/The-FinAI/IEEE-bigdata-cup, check out commit `983537c` (full hash `983537c23fbb28c4fb67fb958ffcaf49f9f7c69e`, the commit recorded in the `git.commit` field of the run records in `experiments/log.jsonl`), and copy the contents of this repository over that checkout. The code needs the organisers' toolkit: `carnot/common.py` imports `finreason_task1.contracts`, and `carnot/run.py` calls `scripts/task1_cli.py`. The organisers license those toolkit files under Apache-2.0 (`public/task1/RIGHTS_AND_PROVENANCE.md` in their repository); they are not redistributed here. The copy replaces the organisers' top-level `README.md` and `.gitignore` with the ones from this repository.

2. **Data.** Download the official Task 1 data files from the organisers' participant hub, https://the-finai.github.io/IEEE-bigdata-cup/task1/, into `development_files/` and `test_questions/`. The organisers license the data under CC BY 4.0 (`public/task1/RIGHTS_AND_PROVENANCE.md`); the data files are not redistributed here. The code checks every downloaded file against the two release manifests, `development_files/release_manifest.json` and `test_questions/test_release_manifest.json`, and stops on a mismatch (`verify_release` in `carnot/common.py`). Use the downloads rather than the copies inside a git checkout of the organisers' repository: section R3 of `paper/ORGANISER_REQUIREMENTS.md` notes that git line-ending conversion had altered those copies.

3. **Response cache.** Download the response-cache archive, `carnot_response_cache.zip`, from the Release assets and unzip it at the repository root. It places the database at `cache/llm_cache.sqlite3`. (If `ARTIFACTS.md` lists the archive in pieces, join them first as described there.) The other archives unzip the same way and are not needed for the replay.

4. **Replay.** Run the commands recorded in `paper/REPLAY_CHECK.md`, from the repository root:

```
python -m carnot.run --config configs/r3.json --split test928 --run-id replaycheck_r3_test928
python -m carnot.run --config configs/r4.json --split test928 --run-id replaycheck_r4_test928
```

`paper/REPLAY_CHECK.md` gives the SHA-256 that each regenerated `submission.zip` had in the original check, next to the SHA-256 of the uploaded file.

### What the replay needs, as documented in this repository

- **Sandbox.** `configs/r3.json` and `configs/r4.json` select the `wsl` sandbox backend, which `carnot/sandbox/executor.py` describes as "WSL2 Ubuntu inside `unshare -rmn`: new user, mount and network namespaces (network unreachable), Windows drives hidden behind a tmpfs, sandbox code copied to a private temp dir; rlimits per program."
- **Environment.** `paper/DOSSIER.md`, section 10, records the environment that was used: "Windows 11 host; WSL2 Ubuntu for the sandbox; Claude Code CLI 2.1.296; Python 3.12 (host), 3.14.4 (sandbox)."
- **Model client.** `carnot/llm_client.py` drives the headless Claude Code CLI (`claude -p`). When it starts it reads the CLI version and requires a claude.ai subscription login. The CLI version is part of every cache key, so the cached responses are found only when the installed CLI reports the version that was used for the original runs; a comment in that file says a CLI update "would silently invalidate replay".
- **Cache-only switch.** `carnot/run.py` has a `--cache-only` option, described there as "fail on any missing cached model response".
- **What a run writes.** A run writes `runs/<run-id>/`, appends a record to `experiments/log.jsonl` and regenerates `experiments/results.md`; a packaged run also appends to `submissions/registry.jsonl` (`carnot/run.py`). The commands above reuse the run identifiers of the original check, so they overwrite `runs/replaycheck_r3_test928/` and `runs/replaycheck_r4_test928/` if the runs archive was unzipped first.

## What is not here

- The organisers' data (`development_files/`, `test_questions/`), their toolkit (`finreason_task1/`, `scripts/task1_cli.py`) and the rest of their repository. They are obtained from the organisers as described above.
- The FinChain repository clone and the FinChain paper PDF that the project used locally. `analysis/README.md` explains how the pinned FinChain tree was extracted.
- The team's private correspondence with the organisers. Some files refer to it by the path `experiments/organiser_correspondence/`; that folder is deliberately absent. `paper/build_facts.py` reads a file in it, so `paper/facts.json` cannot be rebuilt from this tree alone.
- The team's planning notes (`PLAN.md`, `docs/task1-*.md`, `finreason_planning_prompt_v2.md`). Code comments and documents that cite `PLAN.md` sections refer to those notes.
- Lock files, Python bytecode and LaTeX build by-products.

## Organisers' data inside these files

The official data files are not redistributed. Some material from them does appear in this release: the few-shot exemplar file in `exemplars/` reproduces the training questions it uses, and the organisers' case identifiers and slot names appear in the splits, run records and experiment outputs. That material comes from the FinReason Cup Task 1 release, https://the-finai.github.io/IEEE-bigdata-cup/task1/, which the organisers license under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); see `public/task1/RIGHTS_AND_PROVENANCE.md` in the organisers' repository.

## Release archives are not committed

`_release_assets/` is where the release archives are built. It is listed in `.gitignore` and must not be committed: attach the zip files named in `ARTIFACTS.md` to the GitHub Release instead.
