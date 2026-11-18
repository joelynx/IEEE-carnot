# State at the start of the continuation (21 October 2026)

All checks below come from `python -m carnot.continuation_state_v1 verify` and direct inspection. No model was called.

## Accepted submission

R4 remains accepted. Its artifacts are in `runs/20261012T165330Z_r4_test928_S`:

- ZIP SHA-256: `cec784e29f40f277d86ee6a38701e22ca117f1102abd5541083cefc8c60e0cc3` (verified)
- predictions SHA-256: `e0ef54ebb142a85e3d7c6ec305c6530058b919db3c63e8328810099627913067` (verified)
- Receipt: `test-20261012T170418Z-811e06a0839acd614d49f03127d8c684c79823ddc4473a9c`. This is the latest uploaded Test archive in `submissions/registry.jsonl`.
- Recorded development scores: 1.000000 FAC and 0.999167 checkpoint. Rank 14 is historical; no current-ranking claim is made.

## Historical records

- `experiments/improvement_20261020/final_manifest.json` (status `bounded_pilot_complete_r4_retained`): every listed record hash verifies.
- The execution seal, original preregistration and diversity, verifier and sampling-control preregistrations: all 209 recorded hashes verify. The single exception is documented. The original preregistration's hash of `carnot/improvement_campaign.py` predates that file's amendment. The execution seal records the amendment, and the amended hash verifies.
- Baseline-audit protected files verify: `configs/r4.json`, `pot_system_v1.txt`, splits, exemplars, and the R4 ZIP and predictions.
- The previous root plan `docs/task1-plan-through-20261021.md` matches SHA-256 `194175ef…`.
- Release manifests for development and Test files verify.

## Ledgers

- Historical lockbox: 2 of 4 looks used. Look 1 was R0 (S mode). Look 2 was the paired e_base/e_hint H-mode check, logged as two events under one look number. Two remain.
- Development uploads: 2 of 6 self-imposed (R0 and R4 leaderboard580).
- Test uploads: R0, R1, R3 and R4. R4 is the latest accepted.
- The continuation consumed nothing from these ledgers.

## Backend, cache and locks

- Claude Code CLI `2.1.296 (Claude Code)`, claude.ai team subscription login. This is the same CLI version as every cached historical request, so the historical cache keys remain addressable.
- Response cache `cache/llm_cache.sqlite3`: 21,042 rows, 88,350,720 bytes, one CLI version. Sample identities 500–504 have never been used and are reserved for the contemporary R4 comparator.
- Run lock `runs/.run.lock` is free. Its `.holder` file names a finished sampling-control report (stale text, not a live holder). No model-calling campaign process is running. Unrelated Claude Code and MCP processes were left alone.
- WSL Ubuntu (version 2) is running for the sandbox.
- The existing regression suite passes: `python -m unittest discover -s carnot/tests` ran 91 tests, OK.

## Completed and partial work

- The R5 pilot (24 families, 96 instances) is complete, with R4, P, D5, J, V and the sampling control. There is no partial continuation work. This directory did not exist before 21 October 2026.
- No R5-P, D, J or V tuning-eval run exists. Historical R4 forced-novel tuning-eval S and H runs exist (identities 0–4). Historical R4 tuning-noex used the seen route (one Sonnet-low sample) and is not a forced-novel comparator.

## Development-only material

Everything listed under `development_evidence_only` in `preregistration.json` is development evidence: the 24 pilot families and descendants, earlier synthetic templates, all tuning cases and runs, and the pilot-motivated role, verifier and control designs. None of it may fill a confirmation quota.

## Dependency identities

`baseline_manifest.json` freezes 78 pre-existing dependencies before continuation code was written:

- 24 sealed by the prior campaign;
- 2 protected R4 files;
- 52 unsealed existing helpers, such as `common.py`, `harness.py`, `compare.py`, `exemplars.py`, `routing.py`, the sandbox and `synth/author.py`.

New continuation modules use the `carnot/continuation_` prefix or `carnot/improvement_validation_v1.py` and import the old modules without editing them.
