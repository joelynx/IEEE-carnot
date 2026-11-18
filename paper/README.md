# paper/: everything needed to write team carnot's Task 1 Working Notes

**Start here: `AGENT_INSTRUCTIONS.md`.** It tells an agent (or a person) exactly how to write the paper from this folder, and it covers the organisers' standards, the reading order, the paper plan within 10 pages, the rules and a final checklist.

| File | What it is |
|---|---|
| `AGENT_INSTRUCTIONS.md` | How to write the paper: rules, questions for the user, reading order, outline and page budget, procedure, checklist |
| `ORGANISER_REQUIREMENTS.md` | The organisers' Working Notes standards, quoted verbatim from their public sources (format, length, citations, attribution, required statements) |
| `DOSSIER.md` | The complete record: identity and final state, task and data, the system as built, evaluation method, results, negative results, error analysis, integrity and disclosures, limitations, reproduction, artefact index |
| `facts.json` | Every number the paper may use, each with its source. Regenerate with `python -I paper/build_facts.py`; verify with `--check` |
| `TABLES.md` | Human-readable tables generated from `facts.json` (data, runs, comparisons, submissions, baselines, diagnostics, usage, residual errors, lockbox) |
| `build_facts.py` | The generator. Read-only on all project data. Enforces: lockbox as aggregates only, test runs as package facts only, case-level analysis from tuning only |
| `REPLAY_CHECK.md` | Proof of reproducibility: R3 and the final submission R4 regenerated from the response cache with 0 model calls, byte-identical ZIPs |
| `working_notes/main.tex` | IEEEtran conference skeleton, section by section, pointing to `DOSSIER.md` |
| `working_notes/references.bib` | The three required citations, copied verbatim from `public/references/` (refresh from the organisers before submission) |

State at 12 October 2026, when this folder was prepared: the final, latest accepted test submission is **R4** (receipt `test-20261012T170418Z-811e06a0…`; development leaderboard 1.000000 / 0.999167, rank 14 at upload). Test scores were hidden until final results.

## State at 18 November 2026: the paper as accepted

The table above describes the folder as it was handed to the writing step. The paper has since been written, submitted, accepted and revised for the camera-ready version. `VERIFICATION.md` traces every number in it and records each revision in order (sections 5 to 11).

| File | What it is |
|---|---|
| `VERIFICATION.md` | Source of every number and claim in the paper; one section per revision |
| `working_notes/main.tex`, `tables/`, `figures/`, `references.bib` | Sources of the camera-ready paper |
| `working_notes/carnot_finreason2026_task1_working_notes.pdf` | The camera-ready paper |
| `working_notes/carnot_working_notes_standalone.tex` | The same sources in one file |
| `working_notes/supplement/supplement.pdf` | Supplementary material: the evaluation protocol, the synthetic set and the post-submission study in full, the derivation of the split of wrong finals, and the full results of the arithmetic replay |
| `working_notes/archive/submitted_20261102/` | The version submitted for review, unchanged |
| `working_notes/verify/` | Read-only scripts that recompute the figures cited in `VERIFICATION.md` |
| `working_notes/RESPONSE_TO_REVIEWS_20261118.md` | What the camera-ready revision changed for each review point |
| `working_notes/CRITIQUE_20261102.md`, `working_notes/AI_WRITING_AUDIT_20261102.md` | An outside critique and an outside audit of the wording of the version submitted for review. `VERIFICATION.md`, sections 6 and 7, records which points were acted on and why |

Three outside documents of 18 November 2026 are not in the public repository: an assessment of the first camera-ready build, the list of experiments it proposed, and an audit of the wording of the second build. `VERIFICATION.md`, sections 9 and 10, records how each of their points was checked and what was done.

The official test results are in `working_notes/verify/official_test_results_20261028.json`, as published by the organisers.
