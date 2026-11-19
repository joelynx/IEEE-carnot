# Verification of the Working Notes (`paper/working_notes/main.tex`)

Written on 14 October 2026 for the draft produced that day. `python -I paper/build_facts.py --check` printed "facts.json up to date" at the start of the session. Every number and factual claim in the paper is traced below to `paper/facts.json` (key path), `paper/TABLES.md` (table), or a file named in a `facts.json` `_source` field. Where a figure was recomputed read-only to confirm it, the script is in `paper/working_notes/verify/` (hard-coded repository path; run with `python -I`). Nothing outside `paper/working_notes/` and this file was written; no model was run; nothing was uploaded.

Precedence: where `DOSSIER.md` and `facts.json` disagree, `facts.json` wins (section 3 below).

## 1. Sources checked for updates (14 October 2026)

| Check | Result |
|---|---|
| Remote repository (`git fetch`, read-only; not pulled) | `origin/main` at `b98fb5d`, 18 commits ahead of local `983537c`. `public/references/` unchanged (empty diff), so the three required BibTeX entries in `working_notes/references.bib` equal the current official files. `README.md` changes concern Task 2 only. |
| New Task 1 guidance upstream | `app/task1/rules-clarification.tsx` (new, "Task 1 rules clarification, 12 October 2026"): ranking tuple and quantisation, FinChain uses permitted with a disclosure request, development limit, restoring earlier test predictions, baseline labels and scores. Text identical in substance to `experiments/organiser_correspondence/2026-10-12_reply.txt`; nothing new for the paper. `app/task1/test-submission-policy.tsx` adds the restoration clarification. |
| Live site (`https://the-finai.github.io/IEEE-bigdata-cup/`, `/task1/submit/`) | Working Notes rules as recorded in `ORGANISER_REQUIREMENTS.md` (10 pages including references, IEEE two-column, CyberChair SC03, single-blind with names and affiliations, three required citations, refresh provisional entries, code optional). The homepage lists the same citation keys. |
| Scorer facts used in the paper | `finreason_task1/scoring.py` lines 20-42: `SCORER_VERSION`, seen weights 2/5, 2/5, 1/5, hidden weights 1/2, 1/2, `test_private_seen: 580`, `test_private_hidden: 348`, `checkpoint_cases: 864`, `total_slots: 1492`. |

## 2. Claim-by-claim trace

Abbreviations: F = `paper/facts.json`, T = `paper/TABLES.md`, PR = `experiments/preregistration.jsonl` (named in `F#preregistration[*]._source`), LOG = `experiments/log.jsonl` (named in `F#runs.*._source`), RIGHTS = `public/task1/RIGHTS_AND_PROVENANCE.md`, REPLY = `experiments/organiser_correspondence/2026-10-12_reply.txt` (named in `F#organiser._source`), DOSSIER = `paper/DOSSIER.md`.

### Title, authors, abstract

| Claim or number | Source |
|---|---|
| Team name carnot | `F#team.name` |
| Author Joel Jobi, sole author; affiliation Indian Institute of Technology Delhi -- Abu Dhabi, Abu Dhabi, United Arab Emirates; e-mail | Confirmed by the user on 15 October 2026 ("I am the only author, ... IIT Delhi - Abu Dhabi"); e-mail from git config user.email |
| Acknowledgment: organisers thanked; AI-use disclosure naming the system, the affected sections (all) and the level of use | IEEE Author Center, "Guidelines for Artificial Intelligence (AI)-Generated Text" (read 15 October 2026): disclosure in the acknowledgments section, AI system identified, affected sections identified, level of use explained. Content of the disclosure: DOSSIER §3.2 (Claude Code), this session (text drafted by Claude Fable 5.1) |
| 8,888 gold fields round-trip byte for byte | `F#data.gold_fields_total`; `carnot/tests/test_data_and_formatter.py` (formatter round-trip on all gold); DOSSIER §3.1 [O] |
| five-sample plurality vote | `F#runs.20261012T165330Z_r4_test928_S.routing.novel_settings.n_samples` = 5 |
| Leaderboard 1.000000 / 0.999167 (R4); 0.984444 / 0.990000 (Advanced) | `F#submissions.development_portal_responses[1]`; `F#organiser.baselines_dev_leaderboard.Advanced` |
| Test scores unknown; hidden performance not measured | REPLY ("Test scores are hidden until final results"); DOSSIER §1, §9 |

### 1 Introduction

| Claim or number | Source |
|---|---|
| 290 seen templates; 12 domains; 58 topics | `F#data.templates_seen`, `#domains`, `#topics` |
| Strata weighted equally; hidden FAC first tie-breaker; ranking tuple | REPLY; `F#organiser.ranking` |
| FinChain: parameterised templates with executable solutions, 12 domains, 58 topics; organisers call it a provenance and novelty reference only | FinChain PDF (repo root) pp. 1-2; RIGHTS ("provenance and novelty reference only") |
| Exact scoring; one malformed value invalidates the file | `finreason_task1/scoring.py`; PLAN.md §2.5 [O]; DOSSIER §2 |
| Related-work citations | `working_notes/references.bib`: entries downloaded verbatim from ACL Anthology, NeurIPS proceedings and arXiv (URLs in the file). DBLP and OpenReview were unreachable (bot challenges), so PoT, PAL and self-consistency use arXiv exports |

### 2 Task, data and scoring

| Claim or number | Source |
|---|---|
| Gold rendering conventions; `3/11`; premium `6` | PLAN.md §2.4 "Gold value conventions" [O] (train+dev gold, named in `F#data._source`); `carnot/formatter.py` docstring |
| Data attribution sentence: release, URL, CC BY 4.0 link, no changes | RIGHTS; `ORGANISER_REQUIREMENTS.md` R3; AGENT_INSTRUCTIONS §4 wording |
| Development contract `task1-v4`; test release `task1-v4-test-questions-20260901-r2` | `F#data.release_ids.development`; RIGHTS (the test id; `F#data.release_ids.test` is `null`) |
| Hash-checked on every run | `carnot/common.py:verify_release` (called in `carnot/run.py`) |
| 2,900 / 290 / 580 / 928 questions | `F#data.questions` |
| ten train cases per template, one dev case | `carnot/splits.py` assertion `len(train_ids) == 10 and len(dev_by_template[template]) == 1` |
| 116 / 116 / 58 templates by difficulty | `F#data.templates_by_difficulty` |
| 2,700 decimal and 200 enum train finals | `F#data.train_answer_types` |
| 5,180 slot instances; 320 / 690 / 1,180 / 710 | `F#data.train_slot_instances`, `#train_slot_count_distribution` |
| 8,888 = 3,091 half-up + 5,379 exact + 418 enum | `F#data.gold_fields_train_dev`, `#gold_fields_total` |
| 1,492 test slots; 64 questions without a slot | `scoring.py` `total_slots: 1492`, `checkpoint_cases: 864` (= 928 - 64); recomputed by `verify/verify_counts.py` from `test_questions/test_questions.jsonl` |
| Scorer version, commit `983537c`, frozen test scorer | REPLY; `F#organiser.test_scorer` |
| Exact matching rules; zero-slot cases excluded from checkpoint; aggregation order; weights; 12 domains | `finreason_task1/scoring.py` (lines 20-42 read; aggregation per PLAN.md §2.5 [O] and DOSSIER §2) |
| Invalid row rejects the file | PLAN.md §2.5 [O]; REPLY (portal admission) |
| Ranking: lexicographic, 6 dp round-half-even, equal weights, ties share rank | REPLY; `F#organiser.ranking` |
| 580 seen / 348 hidden; routing flags exactly 348 and 0 elsewhere | `scoring.py` lines 34-35; `F#data.routing_novel_counts`; recomputed by `verify/hidden_stats.py` |
| 149 distinct novel-route slot ids never in train; all 456 novel-route slots half-up; 4,850 of 5,180 train slots exact; 84 of 348 enum finals; median length 895 vs 556 | `verify/hidden_stats.py` (public question fields only; files named in `F#data._source`); also PLAN.md §2.3-2.4 [O] |

### 3 System

| Claim or number | Source |
|---|---|
| Prompt composition; output-table wording; retries (2); fallback = omission; `validate_prediction_record` gate | `carnot/solver.py` (`output_table`, `describe_spec`, `solve_sample`, `max_retries`), `carnot/formatter.py:build_row`; `configs/r0.json` `max_retries: 2` |
| Example hint text "number in percent, percentage points (5.25 means 5.25 %); checked as an exact value (return it unrounded)" | `carnot/solver.py:describe_spec` |
| No test submission needed the fallback: non-null finals for 928 and 1,492 slots | `verify/verify_counts.py` on `runs/<test run>/predictions.jsonl` for R0, R1, R3, R4 (0 null finals, 1,492 steps each); PLAN.md §0.1 [O] |
| Packaging with toolkit `validate`/`package`/`validate-zip` | `carnot/run.py` (`toolkit_cli`); `F#runs.*.package.package_ok` |
| Chain-of-thought fallback and same-template retrieval never built | DOSSIER §3.1, §3.3; AGENT_INSTRUCTIONS §3 row 4 |
| Exemplar categories A/B/C; seeded order; verified by the official scorer; two per category; all six at the first attempt; template names | `carnot/exemplars.py`; `exemplars/r0_exemplars.json` (`bootstrap_log` attempts = 1 for all six; template ids `standard_wacc`, `var.time_horizon`, `early_retirement_bridge`, `disclosure_threshold`, `irr.bond_coupon_reinvestment`, `irr.after_tax_net_sale_cost`) |
| Backup replaces primary in H-mode; no retrieval | `carnot/exemplars.py:select`; DOSSIER §3.3 |
| Sandbox policy (allowed modules, rejected constructs), rewrite of float literals and operators, `float()` raises, helper functions, 60-digit decimals, inexact only in half-up fields | `carnot/sandbox/policy.py`, `finq.py` (`PRECISION = 60`), `runner.py` (`float=finq._no_float`), `formatter.py:render` |
| WSL2 Ubuntu, `unshare -rmn`, tmpfs over `/mnt`, rlimits, 5 s timeout | `carnot/sandbox/executor.py:backend_command`, `worker.py:_limits`; `configs/*.json` `"timeout": 5` |
| Formatter rules (2^a 5^b, irreducible n/d, half-up quantise and pad, enum membership) | `carnot/formatter.py` |
| Voting rule and tie-break | `carnot/solver.py:Solver.solve` |
| Routing rule definition and counts | `carnot/routing.py`; `F#data.routing_novel_counts` |
| CLI 2.1.296, headless, flags, scrubbed environment, cache key fields, no temperature or seed | `carnot/llm_client.py`; `F#runs.*.cli_version` |
| 19,538 cached calls; returned model id equals requested id for all | `F#usage.total_calls`; `verify/verify_counts.py` read-only query of `cache/llm_cache.sqlite3` (0 mismatches, 0 rows without `modelUsage`) |
| System definitions R0-R4 (model, effort, N, unit hints, echo notes) | `configs/r0.json` ... `r4.json`; `F#runs.*.routing.novel_settings`, `*.conventions` |
| Unit hint v1 and v2 wording | `carnot/solver.py` (`DIMENSIONLESS_V2`, `describe_spec`) |
| Echo rule definition and normalisation | `carnot/solver.py` (`echoed_slots`, `_norm_sentence`, `output_table`) |
| Echo trigger fires on 0 novel-route test questions | PR (r4 pre-registration, `affected_counts_question_text_only.test_novel_route.echo = 0`) |
| System prompt unchanged ("plain numbers") caveat | `carnot/prompts/pot_system_v1.txt`; DOSSIER §3.7 |

### 4 Evaluation methodology

| Claim or number | Source |
|---|---|
| Splits: lockbox 870 (290 dev + 2 train per template), tuning 2,320, tuning-eval 580, exemplar pool 1,740, tuning-noex 2,314; seeded once | `F#data.splits`; `carnot/splits.py`; `carnot/run.py` (`tuning-noex`); `F#lockbox.drawn` |
| Lockbox cap 4, used 2; aggregates-only rule after look 1 | `F#lockbox.looks_cap`, `#looks_used`, `#access_records`; PLAN.md §5.3 [O] |
| Development leaderboard used twice (R0 check, R4 decisive) | `F#submissions.development_uploads` = 2; PR (r4 step 2) |
| S/H modes; H differs only in backup examples (no retrieval) | `carnot/exemplars.py:select`; `carnot/run.py` (`exclude_template`); DOSSIER §4 |
| Official scoring with `score_submission`; one-hot probed weights; recomputation must equal the report; bootstrap 10,000, fixed seed, case/template schemes | `carnot/compare.py`, `carnot/harness.py`; `F#comparisons[*].replicates` = 10000 |
| σ_run: FAC 1.000000 / 0.998333 / 1.000000; 0.000962 and 0.000481 | `F#sigma_run` |
| Improvement rule | PLAN.md §5.6 [O]; `carnot/compare.py:verdicts` |
| Non-inferiority rule (a)-(e); approved 12 October | PLAN.md §4a (D12); PR (r1 pre-registration `check_c`, `check_d`, `check_e`) |
| Each candidate approved before it was built | PR `approved_by_user` fields; `F#preregistration[*].approved_by_user` |

### 5 Results

| Claim or number | Source |
|---|---|
| Table II rows | T2 / `F#runs.<run>.seen_fac`, `.seen_checkpoint` for `20261011T184257Z_r0_tuning-eval_S`, `20261011T190219Z_r0_tuning-eval_H`, `20261011T201038Z_r0_lockbox_S`, `20261012T155533Z_r0_tuning-noex_S`, `20261012T051314Z_r1_tuning-eval_S_forced-novel`, `..._H_forced-novel`, `20261012T065939Z_r2_...`, `20261012T074942Z_r2_...`, `20261012T132507Z_r3_...`, `20261012T133010Z_r3_...`, `20261012T163526Z_r4_...`, `20261012T163913Z_r4_...`, `20261012T163028Z_r4_tuning-noex_S`, `20261012T102730Z_e_base_tuning-noex_H`, `20261012T105448Z_e_conv_tuning-noex_H`, `20261012T125649Z_e_hint_tuning-noex_H`, `20261012T130052Z_e_base_lockbox_H`, `20261012T131457Z_e_hint_lockbox_H`. Rounded to 6 dp from the fractions in F |
| R0 misses five slots on tuning-eval; three wrong finals in 870 lockbox cases | T8 / `F#error_analysis_tuning.20261011T184257Z_r0_tuning-eval_S` (5 slot misses); `F#runs.20261011T201038Z_r0_lockbox_S.micro` = 867/870 |
| Table III rows | `F#organiser.baselines_dev_leaderboard`; `F#submissions.development_portal_responses` |
| Baselines: organiser model-based reference systems, identities not public, cite by label | REPLY; `F#organiser.baseline_citation_rule` |
| R1 and R3 leaderboard ZIP identical to R0's | `F#runs.20261012T044724Z_r1_leaderboard580_S.package.archive_sha256` and `20261012T132359Z_r3_leaderboard580_S` = `fc3089da...` = `20261011T201016Z_r0_leaderboard580_S` |
| R4 re-solved 32 leaderboard questions (4 echo, 28 dimensionless); changed 5 answers | `F#runs.20261012T164501Z_r4_leaderboard580_S.fresh_calls` = 32; PR (r4 `affected_counts_question_text_only.leaderboard`); `verify/verify_counts.py` diff of R0 vs R4 leaderboard `predictions.jsonl` = 5 rows (matches DOSSIER §5.2) |
| Table IV and the §V-C decimals, fractions and intervals | T3 / `F#comparisons[*]` (`delta_exact`, `delta`, `ci95`); decision text from PR `check_result`, `evaluation_result`, `step_result` events |
| R2 passes by 0.00001 against −0.000962 | PR (r2 `check_result.check_c.margin_note`); `F#comparisons[2].checkpoint` |
| R2 five changed slots: +2 / −3 | PR (r2 `check_result.check_c.case_detail`); `F#comparisons[2].changed_cases.checkpoint` = 5 |
| hints_v2: 9 changed, all fixes; rule "Δ > 0 and non-inferior FAC"; direction not significance | PR (`step_result` step 1 and step 2 notes) |
| R3 S-mode interval degenerate (both changed cases in one template) | PR (r3 `check_result.check_c.note`) |
| R4 step 1: finals 2/0, slots 9/1; biased; step 2 rule and result; rank not stated | PR (r4 pre-registration `step1_seen_route_safety_gate`, `step2_decisive_development_leaderboard`; `step_result` step 1 and step 2) |
| R4 forced vs R3 forced: 0 changed cases | `F#comparisons[12]`, `[13]` |
| Improvement-criteria sentence: R3 S checkpoint and R4 seen-route checkpoint have `improved: true` | `F#comparisons[9].checkpoint.improved`, `[11].checkpoint.improved`; R3's lockbox evidence = look 2 (`F#comparisons[8]`), R4 did not use the lockbox (PR r4 `why_not_lockbox`) |
| Four accepted test submissions R0, R1, R3, R4; R4 latest; receipt prefix, acceptance time, ZIP prefix; R2 not uploaded | `F#submissions.receipts`, `#latest_test`, `#packaged_not_uploaded` |

### 6 What did not transfer

| Claim or number | Source |
|---|---|
| Diagnostic: 4 cases, 2 templates, 10 samples per case and arm, same prompt; 0/20 vs 20/20 (sign), 0/20 both (variance), 80/80 non-target, votes 0/8 vs 4/8; verdict | `F#diagnostics[0]`; `experiments/diagnostics/opus_vs_sonnet_conventions_v1.json` (cases, arms); PLAN.md §0.1 row "Diagnostic" [O] |
| "effective sample is two conventions" caveat | PLAN.md §0.1 ("Effective n = 2 conventions") |
| R2 disclosure (Opus outputs seen for 4 cases) | PR (r2 pre-registration `disclosure`); `F#preregistration[4].disclosure` |
| R2 vs R1: +2 sign, −2 `growth_multiplier_trace` (annual vs cumulative), −1 `eligible_rebate_trace` 3-2 vote | PR (r2 `check_result.check_c.case_detail`); T8 for `20261012T065939Z_r2_tuning-eval_S_forced-novel` |
| "We believe Opus reads more literally" marked as belief | DOSSIER §6.1 [I] |
| Synthetic set construction (Fable author, tuning questions only, sandbox programs, seeded parameters, validators, 1/1 self-score, novel under routing, train-derived style limits, Answer-format sentence reproduces 3,190 questions) | PLAN.md §4b rules 1-4 [O]; DOSSIER §6.2 |
| Haiku probe: 4 disjoint instances, trivial iff all fields right | PR (`haiku_probe_v1` pre-registration) |
| v2: 25 templates, 6 repairs, $5.99, cross-check 25/25, 24/25 trivial, floor 12 | `F#synthetic_set.v2`; PR (`haiku_probe_v1` floor; `filter_result`) |
| v3: 5 templates, 3 repairs, $2.17, 5/5 agree, 5/5 trivial, 20/20 questions, 100/100 fields, bar 3 of 5 | `F#synthetic_set.v3`; PR (`synth_rules_v3_pilot` `pass_iff`, `pilot_result`) |
| Nothing from the set used; second half never built | PR (`pilot_result.action`); DOSSIER §6.2; `F#runs.*` have `synthetic_data_used: false` (LOG) |
| conventions_v1 design (2 per slot, other templates, tuning pool) | `carnot/conventions.py`; `configs/e_conv.json`; PR (`conventions_v1` candidate) |
| e_base / e_conv setting (Sonnet medium, 1 sample) | `configs/e_base.json`, `e_conv.json`; PR `configs.note` |
| 11 fixed, 8 broken, 2 finals broken; hint alone 8 fixed / 0 broken on 80 questions; examples 3 fixed / 8 broken + 2 tax finals; slot names inconsistent | PR (`conventions_v1` `evaluation_result.result.changed`, `.breakdown`, `.finding`) |
| Dimensionless gold examples: 15, 1.0609, −400, 225 (from 5.5 + 9.5 = 15 percent) | `verify/examples.py` on `development_files/train_gold.jsonl` (named in `F#data._source`); PLAN.md §4c [O] |
| Hint-only candidate post hoc; 32 newly observed questions, 1 fixed / 0 broken | PR (`hints_v2` pre-registration `disclosure`, `step1_breakage_check`; `step_result` step 1) |
| R3: hint on the novel route only; 90 fresh test calls; rest replayed | `configs/r3.json`; `F#runs.20261012T133458Z_r3_test928_S.fresh_calls` = 90, `.cached_calls` = 2233 |
| Tax example: gold taxable income 400, prediction 400.00, gold tax 100.00 | `verify/examples.py` on `runs/20261012T102730Z_e_base_tuning-noex_H/cases.jsonl` (case `t1_gr7owktaijktdsa6xpzag`, tuning data); DOSSIER §6.5 |
| Echo rule scope: 22 questions, 2 templates; 4 leaderboard, 4 seen-route test, 0 novel-route test | PR (r4 pre-registration `echo_rule`, `affected_counts_question_text_only`) |
| Fixed both tax finals on tuning-noex without breaking a final | PR (r4 `step_result` step 1 `breakage`, `changed`) |

### 7 Error analysis

| Claim or number | Source |
|---|---|
| R0 tuning-eval S: 0 wrong finals, 5 slot misses (2 sign, 2 units, 1 horizon) | T8 / `F#error_analysis_tuning.20261011T184257Z_r0_tuning-eval_S` |
| Sign example (predicted −0.04, gold 0.04; formula V·(c/100)·s; gold c/100) | `verify/examples.py` (case `t1_dze57qquqcc7cqr2xpua6`; question text of template `portfolio_single_factor`); "also applied the sign of s": DOSSIER §7 [O] |
| Units example (gold 256, prediction 0.0256) | `verify/examples.py` (case `t1_hjxf7by5ix5meugpknjp6`) |
| Horizon example (gold 1.295029 = 1.09^3, prediction 1.09) | `verify/examples.py` (case `t1_coev42cc2m5einmt5okie`) |
| R3 forced: 2 misses, sign | T8 / `F#error_analysis_tuning.20261012T132507Z_r3_tuning-eval_S_forced-novel` |
| R4 seen route tuning-noex: 0 wrong finals, 6 misses (4 + 1 sign, 1 horizon); R0 same set 14 misses, 2 tax finals | T8 / `F#error_analysis_tuning.20261012T163028Z_r4_tuning-noex_S`, `...20261012T155533Z_r0_tuning-noex_S` |
| e_base H: 14 misses, 3 tax finals (2 + 1) | T8 / `F#error_analysis_tuning.20261012T102730Z_e_base_tuning-noex_H`; `verify/examples.py` (predicted taxable amounts) |
| Lockbox look 1: three wrong finals, inspected individually, tax confusion (the only disclosed case-level lockbox detail) | `F#runs.20261011T201038Z_r0_lockbox_S.micro` = 867/870; PLAN.md §0.1 disclosure [O]; DOSSIER §7 |
| R1's votes fixed 1 of 5; 0 of 40 fresh samples | T8 (R0 5 misses, R1 4 misses); `F#diagnostics[0].arms.control_sonnet_medium.target_slot_correct` = 0/40 |

### 8 Integrity, reproducibility and resource use

| Claim or number | Source |
|---|---|
| FinChain: planning only, read-only, 11 templates, pinned commit `146eaa82...`, no execution, no data, no matching, no contribution; 20/30 finals, 28/60 slots on three templates | PLAN.md §2.8 [O] (outside `facts.json`; recorded here as the source); RIGHTS (pinned commit); DOSSIER §8.4; REPLY (later permission) |
| Toolkit unmodified, Apache-2.0 | RIGHTS; `ORGANISER_REQUIREMENTS.md` R3 |
| Model disclosure (ids, routes, effort, N, CLI 2.1.296, no sampling controls) | `configs/*.json`; `carnot/llm_client.py`; `F#usage.by_model_effort` (models that appear) |
| Baselines not used; no human labelled test questions | DOSSIER §8.6 |
| No hand edits; logged system; selection sets; thinking-token caveat (12,326 vs 268) | DOSSIER §8.1-8.3; `F#runs.20261011T193529Z_r0_test928_S.thinking_tokens` = 12326, `20261011T184257Z_r0_tuning-eval_S.thinking_tokens` = 268; PR (r1 `rationale`) |
| Disclosures (1)-(5) | PR (`disclosure` fields of `hints_v2`, r2, r4; `infrastructure_fix` r1 `incident`; `incident` "hints_v2 step 1 interrupted"); `F#preregistration[*]` |
| Replay: 0 fresh, 2,323 cached, toolkit checks pass, ZIP byte-identical (`ea491873...`, `cec784e2...`) | `F#runs.replaycheck_r3_test928`, `replaycheck_r4_test928`; `paper/REPLAY_CHECK.md` |
| R1, R2, R3 leaderboard replays reproduce R0's ZIP | `F#runs.20261012T044724Z_r1_leaderboard580_S`, `20261012T065838Z_r2_leaderboard580_S`, `20261012T132359Z_r3_leaderboard580_S` (`archive_sha256` = `fc3089da...`) |
| Table V (calls, output tokens, thinking tokens, cost by model and effort; total 19,538; $200.50) | T7 / `F#usage` |
| Test-run fresh calls and list-price equivalents: 928 / $12.75, 1,743 / $9.98, 1,740 / $19.39, 90 / $0.45, 32 / $0.42 | `F#runs.20261011T193529Z_r0_test928_S` (12.7456), `20261012T055828Z_r1_test928_S` (9.9766), `20261012T075604Z_r2_test928_S` (19.3856), `20261012T133458Z_r3_test928_S` (0.4549), `20261012T165330Z_r4_test928_S` (0.4169); `fresh_calls` fields |
| "list-price equivalent", subscription | `F#usage.note` |

### 9 Limitations and conclusion

| Claim | Source |
|---|---|
| Hidden performance unmeasured; R3 gain small, slot-level, directional (lockbox interval includes 0); R4 rule narrow, never fires on the novel route; no sampling controls; remaining errors unfixed | DOSSIER §9; `F#comparisons[8].checkpoint.ci95`; PR (r4 `affected_counts_question_text_only.test_novel_route.echo` = 0) |

## 3. Discrepancies found (facts.json wins)

| Where | DOSSIER / other | facts.json | Used in the paper |
|---|---|---|---|
| Usage totals | DOSSIER §5.4: 17,592 calls, ≈ $175.75; Sonnet 4,131 low / 8,541 medium | `F#usage`: 19,538 calls, $200.50; Sonnet 6,057 low / 8,561 medium (DOSSIER §5.4 predates the R0 tuning-noex and R4 runs) | facts.json values |
| Model-id check | DOSSIER §3.2: "across all 17,592 cached calls" | re-verified read-only on all 19,538 rows: 0 mismatches | 19,538 |
| Development uploads | DOSSIER §4: "1 upload of a planned 6" | `F#submissions.development_uploads` = 2 | 2 |
| Test release id | `F#data.release_ids.test` = null | RIGHTS names `task1-v4-test-questions-20260901-r2` | RIGHTS value |
| Title option 2 in AGENT_INSTRUCTIONS ("What Did Not Transfer to Hidden Templates") | would assert a hidden-template finding that was not measured | — | not used as the title; Section VI keeps the shorter heading "What Did Not Transfer" |

Numbers deliberately left out of the paper: the number of test rows on which R4 differs from R3 (and R3 from R1, R1 from R0), although computed as a pipeline check, because they are statistics on test outputs; the leaderboard ranks (14, 15, 16), because they depend on other teams; FinChain's own benchmark scores.

## 4. Final checklist (AGENT_INSTRUCTIONS §6)

- [x] IEEE two-column conference format (`\documentclass[conference]{IEEEtran}`; MiKTeX's installed `IEEEtran.cls` and `IEEEtran.bst`; nothing was installed)
- [x] ≤ 10 pages total including references: **9 pages** (pdflatex, bibtex, pdflatex ×2, 14 October 2026)
- [x] Author names and affiliations present: author Joel Jobi; **affiliation is a visible placeholder that the user must replace** (not in the record)
- [x] Cites `finreason2026overview`, `finreason2026task1overview`, `xie-etal-2026-finchain` with the official BibTeX; entries equal the current `public/references/` files on `origin/main` (`b98fb5d`)
- [x] Data attribution: release named, canonical URL, CC BY 4.0 link, "no changes" (Section II-B)
- [x] FinChain statement: pinned commit, procedure (none: no matching, no execution), contribution (none) (Section VIII)
- [x] Baselines named only by label, development leaderboard cited (Section V-B, Table III)
- [x] Model disclosure: ids, access route, effort, N, no sampling controls, the cache (Sections III-G, III-H, VIII)
- [x] Test scores stated as unknown and pending; hidden-template performance stated as unmeasured (abstract, I, V-D, IX)
- [x] Disclosures: look-1 case inspection; post-hoc hint candidate; R2 diagnostic seen before pre-registration; thinking-token caveat; incidents without effect (Section VIII)
- [x] Reproducibility: byte-identical cached replay of the final submission (Section VIII; `paper/REPLAY_CHECK.md`)
- [x] No case-level lockbox detail beyond the disclosed note; no test-answer statistics; no deadlines
- [x] Every number traced (this file)
- [x] The PDF compiles cleanly with no undefined references or citations and no overfull boxes

Build note (final, 15 October 2026, after the author block and the Acknowledgment were added): `pdflatex` → `bibtex` → `pdflatex` ×2 with MiKTeX 25.4 (`-disable-installer`); output `main.pdf` (copied to `carnot_finreason2026_task1_working_notes.pdf`), 9 pages; 0 errors, 0 undefined references or citations, 0 `Overfull \hbox`, 10 bibliography entries. `carnot_working_notes_standalone.tex` (generated by `verify/flatten.py`, tables and figure inlined) compiles to the same 9 pages with the same checks.

Remaining open items for the user: confirm the affiliation wording ("Indian Institute of Technology Delhi -- Abu Dhabi"; the user wrote "Indian Institute of Delhi - Abu Dhabi Campus (IIT Delhi - Abu Dhabi)"); decide on code sharing and, if yes, add the repository URL at the marked spot in Section VIII; keep or edit the Acknowledgment. Open items for the user: affiliation, title choice, code-sharing URL, acknowledgements, whether to keep the cost figures, and whether anything was uploaded after 12 October 2026.

## 5. Update of 25 October 2026: post-submission investigations

The user asked for the Working Notes to report the post-submission investigations. The edit followed `AGENT_INSTRUCTIONS.md`:

- I wrote only under `paper/working_notes/` and this file, and ran no model.
- I uploaded and submitted nothing.

Text was added as follows:

- a new Section IX, "Post-Submission Investigations", with Table VI (`tables/post.tex`);
- one sentence each in the abstract, introduction item 3, the model paragraph and the limitations;
- an updated usage table and model-identifier sentence;
- the Acknowledgment now names Claude Opus 5.5 as drafter of Section IX and the related updates.

### 5.1 facts.json rebuild

`python -I paper/build_facts.py --check` reported a difference at the start of the session. A rebuild (`python -I paper/build_facts.py`) changed only `usage`: the cache-wide call counts, tokens and costs now include the post-submission campaigns. After the rebuild the check prints "facts.json up to date".

These rows supersede rows in section 3 above:

| Item | Before | Now | Source |
|---|---|---|---|
| Usage totals (Table VII) | 19,538 calls, $200.50 | 68,697 calls, $515.18; per row Sonnet low 6,057, Sonnet medium 55,138, Opus 6,667, Fable high 257, Fable medium 453, Haiku 125 | `F#usage` (rebuilt); the row sums were checked to equal the totals |
| Model-id check (Section III-G) | 19,538 rows, 0 mismatches | 68,697 rows, 0 mismatches | Re-verified read-only on 25 October 2026 over every row of `cache/llm_cache.sqlite3`, comparing `request.model` with the first key of `response.modelUsage` |

### 5.2 Claim-by-claim trace for Section IX and Table VI

Abbreviations:

- P1 = `experiments/improvement_20261020/`
- C = `experiments/improvement_continuation_20261021/`
- S2 = `experiments/safeguard_s2_20261022/`

| Claim or number | Source |
|---|---|
| No upload, test run or lockbox look after R4 | C `final_manifest.json` (`lockbox_looks` 0, `test_runs` 0, `portal_uploads` 0); P1 `final_manifest.json`; `submissions/registry.jsonl` (no entry after R4); `experiments/lockbox_access.jsonl` (2 looks, both before R4) |
| Definitions of P, D, J, V; V triggers only on ≥ 2 distinct complete rows and makes no value edits; J fallback | C `candidate_recipes.json`; `carnot/verification.py`; `carnot/selection.py` |
| D: three Sonnet and two Opus roles at medium effort; three roles carry an instruction | `carnot/prompts/r5_diversity_roles.json` (roles 1, 2 and 4 have instructions; 0 and 3 are empty) |
| Controls (model-balanced vote JB; one extra Opus sample X1/X1C) never beat V | Pilot: C `replay/pilot/run/scores.json` (JB, X1, X1C 95; V 96). Tuning-eval: C `regression/report.json` (all 580). Families: C `ablations/wave1_report.json` and `wave2_report.json` (all 96). Stress: `wave1_report.json` stress panel (JB, X1, X1C 85; V 88) |
| Pilot: 24 families × 4; Fable authoring, blind solve; R4 93, P 94, D/J 95, V 96 of 96 | P1 `DECISION.md` table; P1 `preregistration.json`; reproduced by C `replay/pilot/run/scores.json` |
| All pilot differences in one amortizing-bond family; wording "from year 2 onward the rate changes by" | P1 `BOND_DIAGNOSTIC.md`; P1 `pilot/family_09/template.json` |
| V over R4: family-macro FAC +0.03125, interval [0, 0.09375] | P1 `DECISION.md` ("Why no promotion"); reproduced by `python -m carnot.continuation_analysis_v1 families` on the pilot replay (seed `carnot-r5-family-bootstrap`) |
| Versioned runner replayed 96 pilot cases identically, 1,464 cached calls, none fresh | C `replay_report.json` (`pilot.cached_calls_compared` 1464, `identical` true) |
| Tuning-eval S/H, fresh R4: every recipe 580/580; checkpoint differences at most two slots, the size of R4's run-to-run variation | C `regression/report.json` and `regression/REPORT.md`. Slots: R4c 1032, P 1034, D/J 1033, V 1034. Fresh R4 vs the historical replay differs by 2 slots (`historical.R4c_vs_R4_historical`) |
| 48 new families, all 12 domains, six mechanism classes, balanced | C `data/family_design.json`, `data/family_manifest.json` (8 per class per partition; validated by `validate_design`) |
| Three gates: second implementation (question only, different derivation) matched on 12 draws and endpoints; blind solver with neutral prompt on the 4 scored instances; endpoints without unexpected error | C `preregistration.json#oracle_quality`; `carnot/prompts/oracle_second_impl_v1.txt`, `oracle_checker_neutral_v1.txt`; each family's `second_impl.json`, `blind_check.json`, `endpoint_check.json` and `quality.json` under C `data/development/` |
| Three disputed families adjudicated before scoring; no gold value changed | C `data/quality_decisions.jsonl`; `adjudication.json` for `c1_04` (reference accepted), `c1_57` and `c1_66` (wording clarified; the tooling asserts unchanged seeds, parameters and gold); C `amendments.jsonl` A4 and A7 |
| R4: one final error (units conversion) in the first 24 families | C `ablations/WAVE1_ASSESSMENT.md`; `ablations/wave1_report.json` (R4 95/96; family `c1_13`) |
| Single design revision: two mechanism classes, at least six dependent steps | C `data/design_revision_v1.json`; `carnot/prompts/synth_author_v6.txt`; C `amendments.jsonl` A6 |
| Second 24: every recipe 96/96 finals and 348/348 slots | C `ablations/wave2_report.json` |
| Stress: explicit once or recurring bond schedule, every recipe right; original wording and paraphrase R4 2/4 each, V 4/4; no candidate error on the paraphrase, minimal-pair and distractor variants of six families | C `ablations/wave1_report.json` (`c1-stress-stress1` per-family table); C `ablations/WAVE1_ASSESSMENT.md` |
| The pre-registered rule stopped the study before confirmation; R4 remains the system of record | C `preregistration.json#wave1_assessment`; C `DECISION.md`; C `selection_decision.json#status_after_rule` |
| One tuning-eval case weighs 0.0012 to 0.0028; about 2,995 templates needed; 290 exist | C `statistical_feasibility.json` (`regression_tuning_eval.case_fac_weight_min` 0.00119, `_max` 0.002778; `independent_units_for_zero_event_bound_below_margin` 2995; `template_units` 290) |
| R4's σ_run 0.000962 | `F#comparisons` σ_run (already used in Section IV-C); `experiments/comparisons.jsonl` |
| Count-based rule: zero losses, Clopper–Pearson bound ≤ 1.1 %, a second fresh R4 sample, noise-calibrated checkpoint tolerance; adopted prospectively | `docs/task1-safeguard-v2-plan.md`; S2 `preregistration.json` (gates G1 to G5; user choice of option A recorded there) |
| P: no loss and no gain on tuning-eval and on all 2,314 tuning-noex questions, both modes; R4 self-disagreement 0; bound 1.03 %; slots 4,122/4,129 vs 4,120 | S2 `report.json` (tuning-eval); S2 `gate5_report.json` (tuning-noex: `G1_final_losses` empty, `G3_r4_self_discordant_finals` empty, `G2_upper_95` 0.010277, micro slots P 4122/4129, R4a 4120/4129); S2 `REPORT.md` |
| P has not been submitted | `submissions/registry.jsonl` |
| A second subscription account for the later post-submission runs, same interface and model ids | C `amendments.jsonl` A3; each run's `run.json#backends` (CLI 2.1.296) |
| Synthetic families share one author model family with their checks (limitation) | C `preregistration.json#oracle_quality.limitations` |

### 5.3 Checks after the edit

- **Build.** `pdflatex` → `bibtex` → `pdflatex` ×2: `main.pdf` has **10 pages** (limit 10, including references), with 0 undefined references or citations and 0 `Overfull \hbox`. One overfull box in the first build of Table VI was fixed by narrowing the column labels.
- **Standalone copy.** `carnot_finreason2026_task1_working_notes.pdf` was refreshed from `main.pdf`. `carnot_working_notes_standalone.tex` was regenerated with `verify/flatten.py` and compiles to the same 10 pages with the same checks.
- **Calibration.** Section IX calls no difference significant, reports development evidence only, and states that S2 shows no observed harm, not improvement. Test scores are still described as unknown, and no test-output statistic was added.
- **Open items for the user (unchanged):** affiliation wording, code-sharing URL, Acknowledgment text.

## 6. Update of 2 November 2026: post-results revision and response to the critique

The user asked for a revision in response to `working_notes/CRITIQUE_20261102.md`, after reviewing the decisions on each point, and confirmed that no test upload followed R4. The edit followed `AGENT_INSTRUCTIONS.md` with one change: the organisers have now published the test results, so the checklist items "test scores pending" and "hidden-template performance unmeasured" (section 4 above) no longer apply.

- I wrote only under `paper/working_notes/` and this file.
- I ran no model, analysed no test answer, and uploaded nothing.
- `python -I paper/build_facts.py --check` printed "facts.json up to date" before and after the edit.

### 6.1 Decisions on the critique

| Critique point | Decision | Where in the paper |
|---|---|---|
| 1 Outdated results framing | Accepted. New Section V-E, dated, with the organisers' caveat; abstract, introduction and conclusion rewritten around the observed test result | Abstract; I; V-D; V-E; X |
| 2 "Non-inferiority" rule | Accepted. The pre-registered name is kept as history; the rule is called the adoption rule and described as no detected degradation plus a point-estimate tolerance; decisions unchanged | IV-D; V-C; VI-A; Table V |
| 3 H-mode overlap | Accepted. "Hidden simulation" withdrawn; overlap quantified; not independent replications | IV-B; X |
| 4 Safeguard estimands; σ_run attribution | Accepted. The continuation gate and S2 are named with their estimands; the wrong sentence "R4's own σ_run is 0.000962" (σ_run is R0's, T) is removed | IX ("A safeguard that can be met") |
| 5 Abstract contradictions | Accepted, all four, plus "every inspected residual error" | Abstract |
| 6 Causal claims | Partly accepted: no ablation, so no component attribution; round trip described as formatter validation; float behaviour corrected. Kept: execution and rendering errors are excluded by construction (design property), and "extra samples did not fix" (same-configuration diagnostic, 0/40) | I; III-D; VII; X |
| 7 Synthetic panels | Accepted. Narrow reading; units failure named; selection effect of blind-solver admission | VI-B; IX ("Reading") |
| 8 Per-field voting coherence | Accepted as a stated limitation. The optional diagnostic was not computed | III-E; X |
| Presentation | Accepted. The decisions paragraph, incident detail and per-run test costs were shortened to make room | V-C; VIII |

### 6.2 New claims and their sources

R = `working_notes/verify/official_test_results_20261028.json`, the organisers' `https://the-finai.github.io/IEEE-bigdata-cup/task1/results/2026-test-results.json` saved on 2 November 2026 (SHA-256 `df4d6801ab3561990fd49b536f45c305a91b89668ab9e7c1d91fb1eea422a007`); read with `python -I paper/working_notes/verify/official_results.py`.

| Claim or number | Source |
|---|---|
| Results published 28 October 2026; 27 teams; scorer 2.0.0 | R (`published_date`, `teams`, `scorer_version`) |
| Each team scored on its last accepted valid submission | Test leaderboard page `https://the-finai.github.io/IEEE-bigdata-cup/task1/leaderboard/test/` (read 2 November 2026): "Each team is scored on its last accepted, valid submission before" the deadline |
| That submission is R4; no test upload followed it | `submissions/registry.jsonl` (last accepted upload: R4, 2026-10-12T17:04:18Z, archive `cec784e2…`); user confirmation, 2 November 2026 |
| Rank 17; combined FAC 0.985304; hidden FAC 0.976025; combined checkpoint 0.988745; 917 of 928 finals | R, row `team == "carnot"` |
| One question with a wording/reference inconsistency; frozen evaluation kept | R (`known_issue`) |
| Seen-stratum FAC about 0.99458 (derived, not published) | 2 × 0.985304 − 0.976025 = 0.994583; combined FAC is the exact 50/50 mean (`finreason_task1/scoring.py` lines 517 and 586); each published key is rounded to 6 dp, so the derived value is good to ±1.5e-6 |
| Lockbox FAC of earlier configurations 0.995556 to 0.996667 | Table II (T2): R0 lockbox S 0.996667; e_base and e_hint lockbox H 0.995556 |
| Eight teams with hidden FAC 1.000000 | R (count of rows with `hidden_fac` = 1) |
| H-mode changes the examples of 6 of 580 tuning-eval and 21 of 2,314 tuning-noex questions | `python -I paper/working_notes/verify/hmode_overlap.py` (questions of the three primary-example templates in `exemplars/r0_exemplars.json`); the 6 of 580 also matches C `regression/REPORT.md` (2,870 of 2,900 requests shared) |
| Adoption rule (c) is `delta >= -2σ and upper >= 0` | `carnot/compare.py` `verdicts` (`non_inferior`); PR (hints_v2 `step2_lockbox.pass_iff` uses the same criterion for "FAC non-inferior") |
| R2's H-mode checkpoint interval reaches −0.006667 | Table V; `F#comparisons` (unchanged from section 2) |
| Float in a half-up field is rounded and flagged; inexact value in an exact field is a rendering error | `carnot/formatter.py` `coerce_number` (float → flagged Decimal) and `render` ("inexact value for an exact field"); flags logged by `carnot/solver.py` `_render_all` |
| Per-field voting may assemble a row no single sample produced | `carnot/solver.py` (per-field `Counter` over samples) |
| Continuation FAC gate: lower bound > −0.001; all-zero inconclusive unless the zero-event bound is below the margin; the zero-event bound concerns any regression per unit, not weighted FAC loss; 2,995 units | C `statistical_feasibility.md` ("Estimators", "Zero-event bounds") |
| S2 estimand: share of the 290 templates with a net final-answer loss; bound ≤ 1.1 % | `docs/task1-safeguard-v2-plan.md` (gate definition); S2 `preregistration.json` |
| The two fresh R4 samples never disagreed on a final | S2 `gate5_report.json` (`G3_r4_self_discordant_finals` empty); S2 `report.json` |
| R4's family error: a stated annual-to-quarterly growth conversion; every candidate right | C `ablations/WAVE1_ASSESSMENT.md` (family `c1_13`, class units/scale); Table VI (P, D/J, V 96 of 96 in Fam. 1) |
| 0 of 40 fresh samples at a fixed configuration | Section VI-A: Sonnet 0 of 20 (sign) and 0 of 20 (variance units) in the pre-registered diagnostic (section 2 above) |

Removed rather than changed: the per-run test-call costs ($12.75, $9.98, $19.39, $0.45, $0.42), which remain in `F#usage` and Table VII's totals.

### 6.3 Checks after the edit

- **Build.** `pdflatex` → `bibtex` → `pdflatex` ×2: `main.pdf` has **10 pages** (limit 10, including references), with 0 undefined references or citations and 0 `Overfull \hbox`. Page 10 is full.
- **Standalone copy.** `carnot_finreason2026_task1_working_notes.pdf` refreshed from `main.pdf`; `carnot_working_notes_standalone.tex` regenerated with `verify/flatten.py` and compiles to the same 10 pages with the same checks.
- **Calibration.** Pre-results decisions and post-results observations are kept apart (Section V-E opens by saying so). No error is attributed to the question the organisers flagged. No claim is made about which submission or component caused the test gap.
- **Open items for the user (unchanged):** affiliation wording, code-sharing URL, Acknowledgment text (now also naming the post-results revision).

### 6.4 Corrections after review (2 November 2026)

Three corrections were requested after the revision. Each was checked against the record before it was applied.

| Correction | Evidence | Change |
|---|---|---|
| conventions_v1 broke two finals, not one | LOG, conventions_v1 comparison (`"finals_broken":2,"finals_fixed":0`); Section VI-C ("2 finals broken") | V-C: "broke two final answers and was rejected" |
| Replay evidence covers R3 and R4 only | `paper/REPLAY_CHECK.md` and `runs/replaycheck_r3_test928`, `runs/replaycheck_r4_test928` are the only test replays; the leaderboard replays reproduce R0's development ZIP, not a test ZIP. No R0 or R1 test replay exists in `runs/`, LOG or `submissions/registry.jsonl` | Abstract: "The last two test submissions regenerate byte-identically"; I item 4: "The R3 and R4 test submissions"; III-G: "Every replay we checked reproduced its run bit for bit"; X: "made the development results auditable and the checked submissions reproducible" |
| Execution is exact only for rational operations | `carnot/sandbox/finq.py`: module docstring (rational arithmetic exact; roots, logs, exponentials, normal CDF and root-finding return `Decimal`); `PRECISION = 60`; `solve()` bisection default tolerance `10**-45`, overridable by the program; `_MathShim` replaces `math`, so `math.*` returns exact or `Decimal` values, never floats | I: rational arithmetic exact; transcendental functions and root-finding are finite-precision approximations allowed only in half-up fields, with a reference to III-C. III-C: only rational operations are exact; irrational results and values computed from them are 60-digit decimals; bisection tolerance stated. X: "exact rational execution" |

Rebuilt after the corrections: `main.pdf` 10 pages, 0 undefined references or citations, 0 `Overfull \hbox`; the PDF copy refreshed; the standalone copy regenerated and compiled to the same 10 pages with the same checks.

## 7. Update of 2 November 2026: editorial revision after the writing audit

The user asked for decisions on `working_notes/AI_WRITING_AUDIT_20261102.md`, which reviewed `main.tex` at SHA-256 `4afd0929…` (the version after section 6.4). The user approved the decisions and kept the title. The aim was clarity, less repetition and accurate agency, not disguising AI assistance: the Acknowledgment's AI-use disclosure is unchanged, and so is every disclosure in Section VIII. No model was run, no test answer was analysed, nothing was uploaded.

### 7.1 What changed

- **Revision seams removed:**
  - "We originally called H-mode a hidden simulation" is gone; that name appears in no run record, only in `docs/task1-plan-through-20261021.md`.
  - The pre-registered name stays as a parenthetical ("recorded in the pre-registration as a non-inferiority rule"), because `experiments/preregistration.jsonl` and `carnot/compare.py` (`non_inferior`) use it.
  - "We report its decisions unchanged", "Everything above was decided…", "Our reading is narrow" and the "(update of 2 November 2026)" heading are gone; Section V-E now opens with the publication date.
- **Agency made explicit:**
  - "On our recommendation it was not uploaded" became "R2 was not submitted".
  - "Each candidate was approved" became "the author approved each candidate's specification before it was built" (approvals recorded as `approved_by_user` in PR).
- **One home per repeated explanation:**
  - The pipeline stages stay in the abstract and III-A (removed from I and the figure caption).
  - The convention finding stays in the abstract and VII.
  - The cache and missing sampling controls stay in III-G (removed from VIII "Models" and X).
  - Leaderboard selection bias stays in V-B and V-E.
  - Submission status of the post-submission variants is stated once, in the opening of IX.
- **Deleted as duplicates or unused:**
  - The per-run test call counts (1,743, 1,740, 32 and the duplicate 90; R3's 90 fresh calls stay in VI-D).
  - "Planned and never built" sentences; `AGENT_INSTRUCTIONS.md` says to describe only what was built.
  - "By a handful of slots"; the values are in Table II.
- **Verdict phrases replaced by observations:**
  - "Misleads about as often as it helps" was inaccurate: the borrowed examples fixed 3 slots and broke 8 slots and 2 finals. It became "misled more often than they helped", next to those counts.
  - "Sound" became "the portal accepted both uploads" (`submissions/registry.jsonl`, development `portal_response` status `accepted`).
  - "Knife-edge" was removed; V-C gives the margin (0.00001).
  - "Generic in form and narrow in effect" and "nil by construction" were removed; the trigger counts stay.
  - "Directionally confirmed" became "with a lockbox interval that includes 0".
- **Assumption marked:** that the 348 novel-route questions are the hidden stratum (II-D).
- **Headings:**
  - "What Did Not Transfer" became "Variant Experiments". The audit's proposal, "Rejected Variants…", was not used, because the section includes the adopted unit hint and echo notes.
  - "A safeguard that can be met" became "Revised regression safeguard".
  - "Reading" became "Limits of the synthetic panels".
- **Paragraphs split:** IV-D (rule / its limitation), III-A (prompt / execution and submission), VI-B (construction / screening and outcome), VII (taxonomy / system comparisons), IX continuation (replay and tuning-eval / new families), IX safeguard (old criterion / replacement and result). Limitations regrouped into evaluation coverage, causal attribution and scope of the fixes.
- **Captions:**
  - The decisions caption no longer points to decimal values in V-C, which no longer lists them; it refers to Section IV-C (new label `sec:compare`) for the interval.
  - Baselines, usage, post-submission and pipeline captions were shortened.
  - Table V "safety gate" became "safety check"; Table VI "Recipe" became "Variant".
- **Not done (reasons given to the user):** title change (kept on the user's instruction); new tables; scorer hierarchy as a formula; splitting the scoring paragraph; dropping the receipt and hash; deleting the counterfactual in VI-B or the data-policy clause in IX.

### 7.2 Checks after the edit

- **Numbers.** A token comparison of every number in `main.tex`, `tables/*.tex` and `figures/pipeline.tex`, before (backup of `4afd0929…`) and after, shows no changed value.
  - Removed: the per-run call counts listed above, and duplicate occurrences of values that remain elsewhere in the paper.
  - Added: none. The only "new" tokens are tokenizer artefacts of the existing equation $2\times0.985304-0.976025\approx0.99458$.
- **Encoding.** A scripted edit turned one `\ref` into a carriage return ("Section~ef"), and Python's text-mode writes left CRLF endings in six files. Both were found by a byte scan and fixed, and all sources are LF-only again with no control characters.
- **Build.** `pdflatex` → `bibtex` → `pdflatex` ×2: `main.pdf` has 10 pages, the last holding six reference entries. It has 0 undefined references or citations, 0 `Overfull \hbox` and all fonts embedded (`pdffonts`). The standalone copy was regenerated and compiles to the same 10 pages with the same checks.
- **Deliverable.** `carnot_finreason2026_task1_working_notes.pdf`, SHA-256 `fd2d157d03ac0f18ece13fab0fe9be3f4a5bce43cc6d2b630f023c8d01132ae9`, 259,946 bytes, US letter.
- `python -I paper/build_facts.py --check`: "facts.json up to date".

## 8. Update of 18 November 2026: camera-ready revision after the reviews

The paper was accepted with two reviews (both "Accept: a regular paper"). The submitted version (PDF SHA-256 `fd2d157d…`, section 7) is kept unchanged in `working_notes/archive/submitted_20261102/`. This section records what the camera-ready revision changed and where each new number comes from.

### 8.1 Decisions taken by the author before the revision

The author chose all three on 18 November 2026:

1. **Release:** a public repository with code, prompts, configurations, worked examples, splits, experiment logs, per-case run records, the paper sources and the response cache.
2. **One fresh model run:** a zero-shot ablation (R0 without the three worked examples on tuning-eval, S-mode). This lifts `AGENT_INSTRUCTIONS.md` rule 4 ("do not run models") for this one run.
3. **One statistic on our own test outputs:** how often the five novel-route samples disagreed, labelled as computed after the results. This lifts rule 5 ("no statistics computed from test answers") for this one statistic.

Writes outside `paper/working_notes/` in this session, all following from those decisions:

- `experiments/ablation_zeroshot_20261118/` (new): pre-registration, runner, run log, per-case outputs and the comparison with R0.
- `cache/llm_cache.sqlite3`: 580 new rows from that run (3 from the smoke test, 577 from the full run).
- `paper/facts.json` and `paper/TABLES.md`: rebuilt; only `usage` changed (section 8.3).
- `release/` and `release_staging/` (new): tooling and a dry run for the public release.

Nothing was uploaded or submitted, no lockbox look was taken, and the development leaderboard and the test portal were not used.

### 8.2 Review points and the changes made

| Review point | Change | Where |
|---|---|---|
| R1 W1: long and dense; condense Sections IV and IX, move detail to an appendix | Section IV cut from four subsections to two; the post-submission section cut to four paragraphs; the synthetic-set account shortened. The three accounts are kept in full, as submitted, in `working_notes/supplement/supplement.pdf`, which the paper cites as supplementary material in the repository. An appendix inside the paper would count against the ten-page limit. | IV; VII-B; X; IX "Reproducibility and availability" |
| R1 W2: no ablation; R2: one medium-effort sample against the five-sample vote on the same cached questions | New Section VI and Table V. Worked examples: one pre-registered fresh run. Effort and sampling: stored runs rescored per sample. Exact arithmetic: a bound from the gold. The formatter was not ablated, and the paper says so. | VI; Table V; VIII (last sentences); XI |
| R1 W3: the hidden-template failure is unexplained | New Section V-F: the split of the wrong finals implied by the published scores, public-field contrasts, the sample-agreement statistic, and causes stated as hypotheses. | V-F; abstract; XI |
| R1 W4: limited novelty | The introduction now says that program-of-thought and self-consistency are established and that no new prompting technique is proposed. | I |
| R1 W5: narrow fixes | Already stated under "Scope of the fixes"; unchanged. | XI |
| R1 W6: synthetic panels written and checked in one model family | Already stated; kept in the shortened Sections VII-B and X and in XI. | VII-B; X; XI |
| R1 minor: σ from three runs | Stated where σ is defined ("only a rough noise scale") and where it serves as R2's limit. | IV-B; V-C |
| R1 minor: the Opus hypothesis | Now "one reading … two conventions are too few to establish this". | VII-A |
| R1 minor, R2: release of code, prompts and cache; which records support the replay claims | New paragraph "Reproducibility and availability" naming what is public; the supplement lists where each record is. | IX; supplement Section IV |

Related wording changes: the lettered list (a) to (e) of the adoption rule is gone from the paper (it is in the supplement), so Table IV says "adoption rule" and Section IX says "the pre-registered forced check". Disclosure (6) records the two post-results additions. The Acknowledgment thanks the reviewers and names the model that drafted this revision.

### 8.3 New claims and their sources

Scripts are in `paper/working_notes/verify/` and are read-only; run each with `python -I`.

ZS = `experiments/ablation_zeroshot_20261118/` (`preregistration.json`, `run/summary.json`, `run/cases.jsonl`, `comparison_vs_r0.json`, `run.log`).

| Claim or number | Source |
|---|---|
| Each of the 290 released templates matches exactly two seen-route test questions | `derived_strata.py`, item 1: 580 seen-route questions matched to exactly one train template by text skeleton or slot signature; 290 templates, two each |
| A seen-stratum question weighs 1/(120 T), T ∈ {3, 4, 5, 7} topics in its domain; confirmed on tuning-eval | `derived_strata.py`, item 2: topics per domain {3: 1, 4: 4, 5: 5, 7: 2} from `train_manifest.jsonl`; all 580 FAC weights in `experiments/weights/tuning-eval.json` (probed from the organisers' scorer) equal 1/(120 T) |
| Only three wrong seen finals (two in five-topic domains, one in a four-topic domain) fit the published scores; hence 3 of 580 seen and 8 of 348 hidden | `derived_strata.py`, item 2: seen FAC loss lies in [0.0054155, 0.0054185] given half-even rounding of the two published keys to 6 dp; exhaustive search over multisets of up to 11 weights gives the single solution {4, 5, 5}; 11 wrong finals in total (928 − 917, R of section 6.2). Inferred, not published; it assumes the seen stratum is the 580 seen-route questions (Section II-D) |
| Eight teams with hidden FAC 1.000000 | R (section 6.2) |
| 149 slot ids; 456 half-up slots; 4,850 of 5,180; 84 of 348; 200 of 2,900; 895 and 556 characters | Unchanged from section 2 (`hidden_stats.py`); moved from II-D to V-F |
| Median six sentences and seven numbers before the answer-format note, against four and four | `derived_strata.py`, item 4 |
| Conditional cue in 168 of 348 against 470 of 2,900 | `hidden_form_stats.py` ("PAPER conditional cue"); cue list: "if ", "otherwise", "unless", "at least", "at most", "exceed", "whichever", "when " |
| Solve-for wording in 27 of 348 and in no train question | `hidden_form_stats.py` ("PAPER solve-for wording"); pattern `at which`, `what … makes`, `that makes`. A plain search for "makes" gives 33 but includes unrelated uses, so the pattern was narrowed |
| Every novel-route question with a numeric final prescribes exact intermediate arithmetic and half-up rounding of the final | `hidden_form_stats.py` ("PAPER novel questions with a numeric final": 264 of 264) |
| Sample agreement on test: 10 of 348 finals not unanimous (eight 4–1, two 3–2); 23 of 804 fields | `test_vote_agreement.py` on `runs/20261012T165330Z_r4_test928_S/cases.jsonl` (the scored submission). Aggregates only; no reference answer is involved. The only statistic on test outputs in the paper; authorised in 8.1 |
| Same configuration forced onto tuning-eval: no final and 1 of 1,616 fields not unanimous | `component_analysis.py`, rows "R4f" (runs `20261012T163526Z_r4_tuning-eval_S_forced-novel` and the H-mode run). For R3 forced the figures are 1 final and 2 fields |
| Table V, R0 rows: wrong finals 0, 1, 0; missed slots 5, 4, 5; FAC and checkpoint | `runs/20261011T184257Z_r0_tuning-eval_S`, `…203538Z…_rep1`, `…204616Z…_rep2` (`summary.json`, `cases.jsonl`); the same three runs that give σ_run |
| Table V, no-examples row: 2 wrong finals, 5 missed slots, FAC 0.996667, checkpoint 0.995675 | ZS `run/summary.json` (`score.scores`, `micro` 578/580 and 1031/1036) |
| Table V, R1 forced: each sample alone and the vote | `component_analysis.py`, rows "R1f": samples 0, 1, 4 give 0 wrong finals and 4 missed slots; sample 2 gives 0 and 5; sample 3 gives 1 and 4 (numbered 1 to 5 in the paper). The stored vote row is rescored and must equal the run's own summary |
| 580 questions, 1,036 slots, 1,616 fields on tuning-eval | `component_analysis.py` header lines |
| No run in Table V needed a retry | R0 runs and ZS: `attempts_per_question` {1: 580}; R1 forced: 0 retries over 2,900 samples (read from `cases.jsonl`) |
| Zero-shot run misses the same three conventions (sign twice, units twice, horizon once) and two tax finals | ZS `run/cases.jsonl` compared with gold (tuning data): `factor_ratio_trace` twice, `variance_trace` twice, `growth_multiplier_trace` once; finals of `taxcalc.capital_gains` and `taxcalc.standard_deduction` |
| With examples, one of these two questions was missed in one of three low-effort runs and in one of five medium-effort samples | Case `t1_ks6lmh3qyhkt36r57ez4k` (tuning-eval) is the wrong final of R0 rep1 and of sample 3 of R1 forced |
| Paired difference to R0: −1/300 in FAC, interval [−0.006667, 0]; 0 in checkpoint | ZS `comparison_vs_r0.json` (`carnot.compare.compare`, cases within templates, 10,000 replicates, seed `carnot-compare-v1`); checkpoint interval [−0.001667, +0.001667] |
| The vote returns exactly the fields of the first sample; samples disagree on 2 of 1,616 fields; the same for R2, R3 and R4 forced | `component_analysis.py`: "vote differs from sample 0 on 0 fields" for every forced run; non-unanimous fields 2 (R1, R2, R3) and 1 (R4) |
| 5,379 exact gold fields; 618 cannot be matched by a double (548 fractions, 70 decimals); all slots; 61 of 290 templates | `derived_strata.py`, item 3. A decimal counts when the nearest double, printed with Python's shortest round-trip `repr`, is a different number. 440 of 3,190 questions are affected |
| Finals almost all half-up; every novel-route slot half-up | Train finals 2,660 half-up, 40 exact, 200 enum (`derived_strata.py`, item 4); 456 of 456 novel-route slots (section 2) |
| Usage: Sonnet low 6,637 calls, 867,455 output tokens, 17,241 thinking tokens, $76.05; total 69,277 calls, $518.02 | `F#usage` after the rebuild. The rebuild changed only this row and the totals (before: 6,057; 801,222; 16,786; $73.21; 68,697; $515.18). ZS: 577 fresh calls and 3 cached from the smoke test, $2.82 list-price equivalent |
| Returned model identifier equals the requested one for all 69,277 cached calls | Re-verified read-only on 18 November 2026 over every row of `cache/llm_cache.sqlite3`: 0 mismatches, 0 rows without `modelUsage` |
| Zero-shot ablation: 18 November 2026, CLI 2.1.296, `claude-sonnet-5-5`, effort low | ZS `run/summary.json` (`llm`, `started`, `returned_model_id_mismatches` 0). The subscription account is not recorded in run files, so the paper makes no claim about it |
| Pre-registered before any model call | ZS `preregistration.json` (`status`, `at`), SHA-256 `a562781f…`; it names the runner's SHA-256 and what is reported whatever the outcome |
| Post-submission section, shortened | Every statement is a subset of section 5.2; nothing new. "One tuning-eval case carries more than that in official weight": 0.0012 to 0.0028 against the 0.001 margin (section 5.2) |

Removed from the paper and kept in the supplement: the lettered adoption-rule list, the stratification list, the synthetic-set repair counts and costs, the pilot interval of V over R4, the replay call count, the controls, the zero-event bound and the slot counts of the safeguard check.

### 8.4 Limits of the new analyses, as stated in the paper

- The component analysis covers familiar templates only, with one run per configuration. The comparator R0 was sampled on 11 October 2026 and the zero-shot arm on 18 November 2026; a change of the served model between the two dates cannot be excluded (recorded in the pre-registration).
- The paper calls no difference significant. The zero-shot FAC interval reaches 0, so the pre-declared "worse" verdict of `carnot.compare` is false.
- The split of 3 seen and 8 hidden wrong finals is derived, and the causes in Section V-F are labelled hypotheses.
- The paper does not say which test questions were wrong; none of that is known.

### 8.5 Checks after the edit

- **Numbers.** `number_diff.py` against the archived submitted sources: 19 numeric tokens added (−1/300; 1,036; 1,616; 120; 168; 17,241; 23; the set 3, 4, 5, 7; 470; 518.02; 548; 6,637; 61; 618; 69,277; 70; 76.05; 804; 867,455), each traced in 8.3. The tokens removed belong to the passages moved to the supplement or to the old usage row.
- **Build.** `pdflatex` → `bibtex` → `pdflatex` ×2: `main.pdf` has 10 pages, with 0 undefined references or citations and 0 `Overfull \hbox`. (Corrected in section 9: an earlier wording here said the last page was about half used, which described an intermediate build; in the final build of this revision the last page was nearly full.) The supplement compiles to 3 pages with the same checks.
- **Encoding.** All sources are LF-only with no control characters. `verify/flatten.py` now writes bytes, because text mode gave the standalone copy CRLF line endings on Windows.
- **Fonts.** `pdffonts main.pdf`: all 13 fonts embedded.
- **Organiser guidance** (`git fetch`, read-only; `origin/main` at `cee57ae`, not pulled; live site read on 18 November 2026): the ten-page limit including references, the IEEE two-column template and CyberChair SC03 are unchanged for the camera-ready version. `public/references/finreason2026-overview.bib`, `finreason2026-task1-overview.bib` and `finchain.bib` are unchanged since `983537c`, so the three required entries are current. Test answers remain private.
- `python -I paper/build_facts.py --check`: "facts.json up to date" after the rebuild.
- **PDF metadata.** Title and author are now set through `hyperref`.
- **Check scripts.** `examples.py`, `hidden_stats.py`, `hmode_overlap.py` and `verify_counts.py` used a hard-coded absolute path to this machine; they now locate the repository from their own position, and each was re-run with unchanged output.

### 8.6 Release tooling (nothing is published by these tools; the author pushes)

- `release/make_release.py <target>` builds the public tree and three release archives; `release/verify_release.py` and `release/audit.py` check it. The report is `release/AUDIT_REPORT.md`.
- The staged release is in `release_staging/`. Its `ARTIFACTS.md` gives each archive's size and SHA-256, and `MANIFEST.sha256` lists every file of the git tree. The archives are `carnot_response_cache.zip` (69,277 rows; 290 MB unpacked), `carnot_runs.zip` and `carnot_experiment_outputs.zip`.
- Not in the release: the organisers' data and toolkit, the FinChain clone and PDF, `experiments/organiser_correspondence/`, and the planning notes.
- The audit found no credential and no e-mail address other than the author's.

### 8.7 Decisions of the author on 18 November 2026, after the first audit

| Item | Decision | What was done |
|---|---|---|
| Repository | `https://github.com/joelynx/IEEE-carnot` | `\repourl` in `main.tex`; the supplement's abstract; `release/templates/README.md.tmpl` |
| Licence | MIT | `release/templates/LICENSE` (copyright 2026 Joel Jobi), written into the release as `LICENSE`. The release README says that the organisers' material keeps CC BY 4.0 and that the paper and its sources are not covered, because the copyright in the paper may pass to the publisher. This scope note is the drafting model's wording; the author confirmed it on 19 November 2026 (section 10.7). |
| Quoted sentences of the organisers' private e-mail (the audit's one blocker) | Replace them with the organisers' public wording | `paper/ORGANISER_REQUIREMENTS.md`: the two rows of R4 now quote the public "Task 1 rules clarification · 12 October 2026" (`app/task1/rules-clarification.tsx` on the organisers' `origin/main`, read at `cee57ae`); two short quoted phrases of the e-mail are paraphrased. `paper/build_facts.py`: the string `finchain_disclosure_request` is reworded. `paper/facts.json` was rebuilt and differs in that string only; `paper/TABLES.md` is unchanged. No requirement and no number changed. |

Defaults kept, as told to the author: the planning notes stay out of the release; full submission receipt ids and per-call session ids stay in; the working documents in `paper/` stay in. `paper/README.md` gained a section describing the folder's state on 18 November 2026.

### 8.8 Deliverable of this revision (superseded by section 9.6)

- `working_notes/carnot_finreason2026_task1_working_notes.pdf` (a copy of `main.pdf`): SHA-256 `7a6d19e8dbda8ed55ba063c5ad7d0a4e0a56e7b96a251c7d9e3b253c6d0cdd20`, 267,449 bytes, 10 pages, US letter, all 13 fonts embedded, title and author set in the metadata, 0 undefined references or citations, 0 `Overfull \hbox`.
- `working_notes/carnot_working_notes_standalone.tex` was regenerated with `verify/flatten.py` and compiles to the same 10 pages.
- `working_notes/supplement/supplement.pdf`: 3 pages, same checks.
- `python -I paper/build_facts.py --check`: "facts.json up to date".
- The author uploads the PDF through CyberChair SC03 and pushes the repository; neither was done here.
- Still for the author to confirm: the Acknowledgment's wording for the model that drafted this revision ("Claude Fable 5, model `claude-fable-5-2`"), and the scope note of the licence.

## 9. Second camera-ready revision of 18 November 2026: outside assessment and arithmetic replay

### 9.1 What prompted it, and the author's decisions

After the first camera-ready build (section 8; published as commit `44ab0b3` with release `v1.0`) two documents were added to `working_notes/`: `REVIEW_REVISION_ASSESSMENT_20261118.md`, an assessment of how that build answers the reviews, with the check script `verify/revision_assessment.py`, and `EXPERIMENT_RECOMMENDATIONS_20261118.md`, which proposes three experiments. Neither was written in the sessions that produced the paper. Every finding was checked against the files before anything was changed (9.2). (The two documents and the script are not part of the public repository; see 10.9, which also says where the script's figures can be recomputed.)

Decisions of the author on 18 November 2026:

- The second proposed experiment, a floating-point replay of stored programs, is run on the original machine before the project moves to another one. It makes no model call.
- Its pre-registration was approved "as written" after the author read its summary and before any stored program was executed.
- The text corrections are made together with the result.

The first proposed experiment (11,600 fresh samples in a two-by-two design) and the third (an independently checked challenge panel) were not run. The drafting model advised against the first, because every configuration measured so far has 0 to 2 wrong finals in 580 on familiar templates, and for leaving the third as future work; the author did not ask for either.

### 9.2 Findings of the assessment, how each was checked, and what was done

| Finding | Check | Action |
|---|---|---|
| The paper says the code and cache are public, but the repository held only `.gitattributes` and no release | Out of date. The assessment was written before the push. The GitHub API on 18 November 2026 showed `main` at `44ab0b3`, release `v1.0` with three archives, and asset digests equal to `ARTIFACTS.md`; a fresh clone passed `sha256sum -c MANIFEST.sha256` (1,468 of 1,468) | None |
| The README's replay commands lack `--cache-only` | Correct. `carnot/llm_client.py` raises `CacheMissError` only when `cache_only` is set; otherwise a miss calls the model | `release/make_release.py` appends `--cache-only` to the commands it copies from `paper/REPLAY_CHECK.md` and adds a sentence that the replay still needs the recorded CLI version and a claude.ai login |
| "618 exact gold fields cannot be matched by any double-precision value … a floating-point pipeline would forfeit them" claims more than the count shows | Correct. `verify/revision_assessment.py`, re-run: 548 fraction strings, 70 decimals whose nearest double does not print back, none of the 70 exactly representable, and for 2 of the 70 the nearest double printed at the gold's number of decimal places gives the gold string | The paragraph is replaced by the measured replay (9.3). The count moved to the supplement with wording that claims representation only |
| "Exactness matters only at rounding ties" is too narrow | Correct as a matter of principle. In the replay every lost half-up final is in fact an exact tie (9.3), which the paper now reports as an observation | Reworded |
| The paper did not get shorter | Correct. `verify/revision_assessment.py` on the first camera-ready build: 7,636 source tokens against 7,135 submitted. Section 8.5 said the last page was about half used, which was wrong for the final build | Section 8.5 corrected. `RESPONSE_TO_REVIEWS_20261118.md` now says the paper as a whole is not shorter. Cuts in this revision: 9.4 |
| The paper gives the five-week gap between the two runs of the examples comparison but not that the served model may have changed | Correct; the pre-registration of the zero-shot run says it, the paper did not | One clause added in Section VI |

The assessment's length figures for the PDF text (8,553 and 9,200) differ from what its script prints on this machine (8,470 and 9,100, with `pdftotext` from Git for Windows); the conclusion is the same.

### 9.3 The arithmetic replay: sources

AR = `experiments/arith_replay_20261118/` (`preregistration.json`, `run_arith_replay.py`, `sandbox_binary64/`, `run.log`, `results/`). Order of events, all on 18 November 2026 (UTC): design drafted 15:18; approved by the author; exact reproduction step run 17:44 to 17:46 (every program reproduced; the evidence written before sealing is `results/overview_exact_only.json` and `exact_replay_before_sealing` in the pre-registration, because the full run rewrote `results/exact_reproduction.json`); files sealed by hash at 17:46:30 (`status: frozen_before_binary64_execution`); full run from 17:46:35. Before the approval only toy programs had been executed (`--selftest`). The approval itself has no independent timestamp: it is recorded in the pre-registration's `approval` field and in the session, and the text of the pre-registration at the time of approval was not hashed. `analyse_replay.py` was written after the results and is labelled as such.

**An error found by an independent check, and its correction.** Before the paper was finalised, a separate read-only check compared every number of this revision with the result files. It confirmed the tables and counts and found one false statement: the pre-registration, the supplement and the first draft of the paper's sentence treated the tuning-noex run as holding *different* programs for the 580 tuning-eval questions. It does not. That run took its responses for those questions from the response cache (`summary.json`: 1,734 fresh and 580 cached calls; same cache keys and program text, `verify/arith_replay_checks.py`, item 1). There are 2,314 distinct programs, and 2,894 is the number of executions per arm. The correction: amendment A1 in AR `preregistration.json` (appended by `amend_preregistration.py`; the original wording stays), the supplement lists the 1,734 other programs separately, and the paper's sentence now reports those 1,734 only. No design choice, sealed file or result changed.

| Claim or number | Source |
|---|---|
| Pre-registered; no model call; programs of the first R0 run on tuning-eval (580) and of the R0 run on tuning-noex (2,314) | AR `preregistration.json` (`inputs`, `approval`, `frozen_at`, `sealed_files_sha256`); the runner reads `runs/20261011T184257Z_r0_tuning-eval_S/cases.jsonl` and `runs/20261012T155533Z_r0_tuning-noex_S/cases.jsonl` and refuses a record that is not one sample with one attempt |
| Executed exactly, the programs reproduce every stored field | AR `results/exact_reproduction.json`: `reproduced_all` true, 580 of 580 and 2,314 of 2,314 (rendered fields, issues and prediction rows equal); `results/<split>/comparison_exact_replay.json`: differences 0. The 2,314 programs carry 6,443 fields, the 580 among them 1,616 (`verify/arith_replay_checks.py`, item 1) |
| The binary64 arm uses the same isolation; the frozen sandbox files are unchanged | AR `run_arith_replay.py` (`check_files`, `make_box`): hashes of `carnot/sandbox/*.py` and `carnot/formatter.py` checked at start; the twin `worker.py` and `policy.py` are byte-identical copies; only the folder the four sandbox files are copied from differs |
| The formatter refuses a float in an exact field | `carnot/formatter.py`, `render`: "inexact value for an exact field" |
| Three rules fixed in advance; the third writes a reconstructed fraction when the value is not a short decimal | AR `preregistration.json` (`renderings_of_a_float_in_an_exact_field`); `render_binary64` in the runner (12 significant digits; `Fraction.limit_denominator()` with its default bound of 10^6) |
| Table V, last block: 4, 178, 0.994286, 0.839775; 3, 127, 0.995952, 0.888280; 3, 64, 0.995952, 0.948571 | AR `results/tuning-eval/binary64_repr`, `binary64_15g`, `binary64_rational` (`summary.json`: `wrong_finals`, `missed_slots`, `score.scores`), scored by the organisers' `score_submission` through `carnot.harness` |
| Every rule loses three half-up finals, each an exact tie; 22.815 computed as 22.814999999999998 and rendered 22.81 | AR `results/tuning-eval/field_transitions_*.json` ("final \| half-up": lost 3); `results/posthoc_analysis.json` (exact value 4563/200, gold 22.82; all 3 are ties) |
| The first rule also loses an exact final, written as 100.00000000000001 | Same files ("final \| exact, gold a decimal": lost 1 under `repr`; gold `100`) |
| All 93 fraction slots lost unless fractions are reconstructed, which recovers 64 | `field_transitions_*.json` ("slot \| exact, gold a fraction": lost 93, 93, and kept 64 / lost 29) |
| 29 to 80 of the 872 exact decimal slots that the exact run matches | `field_transitions_*.json` ("slot \| exact, gold a decimal": lost 80, 29, 30; 872 = kept + lost; 5 more are wrong in the exact run as well) |
| The tuning-noex run holds these 580 programs and 1,734 others; among the others every rule loses 10 half-up finals, all exact ties | `verify/arith_replay_checks.py`, items 1 and 2 (1,590 half-up finals matched exactly, 10 lost under each rule); AR `posthoc_analysis.json`: 13 lost half-up finals in the whole run, all 13 exact ties, 3 of them in the 580 |
| Supplement, Table III, block of the 1,734 other programs | `verify/arith_replay_checks.py`, item 2. The block of the 580 and the block of all 2,314 are AR `field_transitions_*.json`; the three blocks add up |
| On the novel route every numeric field is rounded half-up | Section 2 and 8.3: 264 half-up and 84 enum finals, 456 of 456 slots half-up |
| Abstract: "replaying one run's programs in double precision lost three or four" | The three rows of Table V |
| Supplement, Table II: scores, differences and intervals of both runs | AR `results/<split>/<arm>/summary.json` and `comparison_<arm>.json` (`carnot.compare.compare`, cases within templates, 10,000 replicates, seed `carnot-compare-v1`) |
| Supplement, Table III and "What explains the losses" | AR `field_transitions_*.json`, `posthoc_analysis.json`, and `verify/arith_replay_checks.py`, item 3 (set differences between the rules: rule 3 loses every decimal slot that rule 2 loses, and 1 and 8 more; rule 1 loses every decimal slot that rule 2 loses, and 51 and 255 more; the one fraction slot for which the reconstruction returns another fraction). `posthoc_analysis.json` assigns each lost slot to the first matching reason, so its label "a fraction was written for a finite decimal" reads 1 and 9 where the set difference is 1 and 8, and its "denominator above 10^6" (6 and 18) counts only slots whose computed double is the nearest one |
| No execution failed in binary64; no field was unrenderable or dropped by the validator | AR `results/overview.json`: `execution_failures` {}, `unrendered_fields` {}, `fields_dropped_by_gate` 0 in all six arms |
| Supplement, Section IV: loss interval [0.0054155, 0.0054185]; weights 1/360, 1/480, 1/600, 1/840; 1, 4, 5 and 2 domains; the single solution | `verify/derived_strata.py`, items 1 and 2 (as in 8.3) |
| Supplement, "Representation of the gold values": 548; 70; 2 of the 70; 618 slots in 61 templates | `verify/derived_strata.py`, item 3, whose last line gives the two counts first taken from `verify/revision_assessment.py`: none of the 70 exactly representable, and 2 given back when the nearest double is printed with the gold's number of decimal places |

Limits stated in the paper and the supplement: the programs were written for an exact pipeline; three float implementations are not every possible one; both runs hold familiar templates only, and the second run contains the programs of the first, so they are not two independent samples. The paired intervals of the replay exclude 0, but the paper still calls no difference significant.

Sections 8.2 and 8.3 describe the first camera-ready build. Where they say that the post-submission section has four paragraphs, that exact arithmetic is covered by a bound from the gold, or that the record list is Section IV of the supplement, this section supersedes them: three paragraphs, a measured replay, and Section VI.

### 9.4 Other text changes

- Section V-F, "Size": the weight expression and the solution moved to the supplement (Section IV there). Removed from the paper: 120, the set 3, 4, 5, 7.
- Section X: the paragraph on the replaced FAC criterion is one sentence; the authoring model and the mechanism classes are no longer named there (the model is named in Section IX). Removed: −0.001, 1.03 %.
- Sections II-B, III-B, VII-A, VII-D and VIII: the slot-count breakdown, the names of the six worked examples, six template names and three example values were dropped. Removed: 690; 1,180; 710; 1.0609; −400. They remain in the run records and in the version submitted for review (`working_notes/archive/submitted_20261102/main.tex`), and partly in sections 2 to 4 above.
- Section VI: first sentence ("four components"), the examples paragraph (served-model clause), the arithmetic paragraph (9.3). Removed: 618, 548, 70, 61.
- Abstract: one clause on the replay; 250 words by whitespace count.
- Section IX: disclosure (6) names the replay; the availability paragraph lists what the supplement now holds. Section XI: the sentence on causal attribution.
- `tables/components.tex`: last block and caption.
- Supplement: Sections IV and V and two tables are new; 4 pages.

`number_diff.py` against the published first camera-ready sources: 14 tokens added (0.839775; 0.888280; 0.948571; 0.994286; 0.995952; 1,734; 100.00000000000001; 127; 178; 22.81; 22.814999999999998; 22.815; 29; 872), each traced in 9.3, and 13 removed (listed above).

Length, with `verify/revision_assessment.py`'s measure: source 7,612 whitespace-separated tokens (first camera-ready build 7,636; submitted 7,135); extracted PDF text 9,125 words (9,100; 8,470). The paper is about as long as the first camera-ready build and longer than the reviewed version.

### 9.5 Checks after the edit

- **Build.** `pdflatex` → `bibtex` → `pdflatex` ×2: 10 pages, 0 undefined references or citations, 0 `Overfull \hbox`, 0 LaTeX warnings; all 13 fonts embedded; title and author in the metadata. The last page is full in the left column and about three quarters full in the right. The supplement: 4 pages, same checks.
- **Encoding.** `main.tex`, `tables/components.tex` and `supplement/supplement.tex` are LF-only and pure ASCII.
- `python -I paper/build_facts.py --check`: "facts.json up to date". No model call was made in this revision, so the usage table and the count of cached calls are unchanged.
- `python -m carnot.continuation_state_v1 verify`: exit 0 (frozen files and ledgers intact).
- **An edit that was undone.** While the move to another machine was prepared, a setting for the WSL distribution name was added to `carnot/sandbox/executor.py` and removed again the same day, when it turned out that the file's hash is recorded in the continuation's baseline manifest and in 13 run records. The file is byte-identical to the released one (SHA-256 `7d15a38c…`), and the replay's runner checks that hash at start.

### 9.6 Final deliverable (superseded by section 10.7)

- `working_notes/carnot_finreason2026_task1_working_notes.pdf` (a copy of `main.pdf`): SHA-256 `5b771934ec5fc5b706da432053f9b565e3e39115f3cff5d060032201286cf78e`, 266,640 bytes, 10 pages, US letter.
- `working_notes/carnot_working_notes_standalone.tex`: regenerated with `verify/flatten.py`.
- `working_notes/supplement/supplement.pdf`: 4 pages.
- The author uploads the PDF through CyberChair SC03 and pushes the repository; neither was done here.
- Still for the author to confirm, as in 8.8: the Acknowledgment's wording for the model that drafted the camera-ready revisions, and the scope note of the licence. The two documents named in 9.1, with `verify/revision_assessment.py` and `verify/revision_assessment_page10.png` (a picture of the last page of the first camera-ready build), are in `paper/working_notes/` and go into the public release under the default of 8.7 unless the author excludes them (`release/exclude.txt`).

### 9.7 Release rebuild

- `release/make_release.py` changed in two places: the README's replay commands (9.2), and a list `WHOLE_IN_TREE` that keeps `experiments/arith_replay_20261118/` whole in the git tree (7.5 MB, 55 files), so that the three archives already attached to release `v1.0` stay as they are.
- After the rebuild the three archives have the SHA-256 values of release `v1.0` (`1aa6fb41…`, `af27d880…`, `df255815…`) and `ARTIFACTS.md` is byte-identical to the published one. No archive has to be uploaded again.
- `release/verify_release.py release_staging`: all four checks passed (69,277 rows in the cache snapshot; every zip passes its self-test; no forbidden path; `MANIFEST.sha256` matches the tree).
- `release/audit.py`: the same eleven decision items as in the first audit and no new kind of finding. The first rebuild carried one blocker, the tool's own warning that three files under `experiments/` had been written in the fifteen minutes before the build (the amendment and the README of the replay); the tree was therefore built again after that interval. The report is `release/AUDIT_REPORT.md`, which is not part of the released tree.
- What the paper says about the repository (the supplement, the replay records, the README's commands) is true of the rebuilt tree and becomes true of the public repository when the author pushes it. Until then the public repository is the first camera-ready build, commit `44ab0b3`. (The author pushed this build later the same day as commit `7a1fbba`; see section 10.1.)

## 10. Third camera-ready build of 18 November 2026: editorial revision after a second writing audit

### 10.1 What prompted it, and how it was judged

`working_notes/AI_WRITING_AUDIT_20261118.md` reviewed the PDF of section 9.6 (SHA-256 `5b771934…`). It was not written in the sessions that produced the paper. By then the author had pushed that build: the public repository was at commit `7a1fbba`, and its PDF had the same SHA-256 (checked on 18 November 2026 through the GitHub API and by downloading the file). The audit quotes 125 passages with a comment on each; it marks 34 as salient, 5 as context and 2 as disclosure.

The author asked the drafting model to read the audit and to judge what to add, delete or modify. The choices below are therefore the model's. The author had not reviewed them when this section was written, and it is the author who decides whether this build replaces the public one.

One question was asked of every entry: does the passage say something inaccurate or stronger than its source, give an action to the wrong subject, or repeat something without adding to it? Whether a passage reads as drafted by a model was not a criterion. The drafting is disclosed in the Acknowledgment, which is unchanged, and every disclosure of Section IX is kept (disclosure 2 now also names the breakage check, 10.2).

By the model's count 107 of the 125 entries led to a change, some of them only in part, and 18 did not (10.3). All 34 salient entries are among the 107. No model was run, no experiment was made, no test answer was analysed, and nothing was uploaded or pushed.

### 10.2 Statements corrected, and the source of each new wording

"Before" is the build of section 9 (commit `7a1fbba`). WA = `working_notes/verify/writing_audit_checks.py` (new, read-only: it compares stored prediction files field by field).

| Where | Before | Now | Why, and source |
|---|---|---|---|
| III-B | "There is no retrieval, so same-template examples are never shown" | "as deployed, every question gets the same three examples, including the questions of those three templates" | The old sentence was false for the deployed mode. `carnot/exemplars.py`, `select`: the three primaries are returned whenever the mode is S; six tuning-eval questions share a primary's template (Section IV-A) |
| Table I | "echo notes (never fire on test)" in the novel-route column | "(triggered by none of the 348)" | The echo rule fires on 4 seen-route test questions (Section VII-E; section 2) |
| XI | "with one run per configuration" | "rests on few runs: its one run without examples is compared with baseline runs made five weeks earlier" | Table V holds three R0 runs and five samples scored alone; only the run without examples is single (8.3) |
| V-F | "whose slots are exact" | "whose slots are mostly exact" | 4,850 of 5,180 train slots (section 2) |
| I, related work | "the intermediate chain, which is where our residual errors lie" | clause removed | The inspected errors include wrong final answers (the tax confusion, Sections VII-E and VIII) |
| VII-C | "Evaluated as `e_base` against `e_conv`" | "evaluated as `e_conv` against the baseline `e_base`" | The roles were reversed. PR (`conventions_v1`): baseline `e_base`, candidate `e_conv` |
| VII-B | "24 of 25 authored templates trivial, below the pre-registered floor of 12 non-trivial templates" | "which left one non-trivial template against a pre-registered floor of 12" | Same figures (section 2); the old sentence compared 24 with a floor for the other category |
| X | "These panels did not discriminate between systems." | sentence removed; XI now says "the systems differed mostly on one ambiguous wording" | Table VII shows 83 to 88 on the stress panel; the supported statement is that the gains "came mostly from the ambiguous bond wording" (section 5.2) |
| Abstract | "replaying one run's programs in double precision lost three or four" | "re-executing … lost three or four (depending on how floats are written)" | The range is over the three renderings of Table V, not an uncertainty (9.3) |
| Abstract, V-F | "The published scores imply three wrong finals … and eight …"; "The published scores fix how the eleven wrong finals divide" | both now open with the assumption that the 348 novel-route questions are the hidden ones | The derivation rests on that assumption (8.3; supplement, Section IV) |
| Abstract, V-F, VII-C, XI | "the hidden questions" for properties measured on the novel route | "the 348", "novel-route questions", "on the novel route" | The route is what was measured (Section II-D) |
| V-C | "so we call no difference in this paper significant" | "so we call none of these differences significant" | The inference covers the pre-registered comparisons. It remains true that the paper calls no difference significant |
| IV-B | "no statistic computed on test outputs is used" | "The decision uses no statistic computed on test outputs; Section IX discloses one statistic of a test run that a written rationale mentioned" | PR (`r1`: `check_e`, `rationale`); section 2, row on the thinking-token caveat |
| I | "so arithmetic and formatting errors cost as much as reasoning errors" | "so a value that is off in its last digit scores no better than a wrong method, and one malformed value invalidates the whole file" | A malformed value costs the file, which is more than one field (Section II-C) |
| III-G | "so samples are independent calls"; "Every replay we checked reproduced its run bit for bit" | "separate calls with the same prompt"; "Replaying the R3 and R4 test submissions from this cache reproduced the uploaded files byte for byte" | `carnot/solver.py` (`solve_sample`); `paper/REPLAY_CHECK.md` |
| III-B | "all six were verified at the first attempt" | "no candidate was rejected" | WA, item 3: six candidates tried, six verified, one attempt each (`exemplars/r0_exemplars.json`, `bootstrap_log`) |
| V-C | "Forced onto the novel route, R4 equals R3 exactly." | "Applied to every tuning-eval question, R4's novel-route configuration returned the same fields as R3's." | WA, item 1: 0 of 1,616 fields differ, in S-mode and in H-mode |
| VI | "Table V separates four components" | "examines four components … The comparisons are not equally controlled: two rescore stored runs, one adds a run made five weeks later, and one re-executes stored programs." | 8.3 and 9.3 |
| VI, worked examples | "On familiar templates the examples thus change a few fields at most" | "Field by field, the run without examples differs from the first R0 run in 4 of 1,616 fields, these two finals and two slots; this single comparison suggests, and cannot establish, …" | WA, item 2: finals of `t1_ks6lmh3qyhkt36r57ez4k` and `t1_ls7mubqvgwm32wk4e5xze` (the two tax finals of 8.3); `growth_multiplier_trace` in two cases of one template, one newly matched and one newly missed, which is why the checkpoint difference is 0 |
| VI, sampling | "the vote removes an isolated deviation … and adds no answer that a typical single sample lacks. The same holds for the forced runs of R2, R3 and R4." | "The five-sample vote of R1 forced … a final in one sample and a slot in another; the vote corrects these two deviations and otherwise returns what all five samples returned. In the forced runs of R2, R3 and R4 the vote likewise returns the fields of its first sample." | `component_analysis.py`: R1 forced has 2 non-unanimous fields, and the voted value equals the gold in both; the vote differs from the first sample on 0 fields in every forced run. The old last sentence claimed more than that for R2 to R4 |
| VI, exact arithmetic | "all 93 whose gold is a fraction unless fractions are reconstructed, which recovers 64, and 29 to 80 of the 872 exact decimal slots" | "Of the 93 exact slots whose gold is a fraction, the first two rules lose every one and the third loses 29; of the 872 exact decimal slots that the exact run matches, the three rules lose 80, 29 and 30." | Same source as 9.3 (AR `field_transitions_*.json`: 93, 93, 29 and 80, 29, 30) |
| III-H | heading "The submitted systems"; "the more specific per-field hint changed the behaviour" | "Systems R0 to R4"; "was enough to change the scale that the programs returned (Section VII)" | R2 was never uploaded. The hint alone fixed 8 slots and broke none (section 2, `conventions_v1`) |
| Table VI, IX | "Distinct model calls of the whole project" | "Distinct model calls in the response cache: all runs of the pipeline and the experiments, … but not the Claude Code sessions in which the code and this paper were written." | `carnot/llm_client.py`: the cache is written only by the project's own client; `paper/build_facts.py` (`usage_facts`) sums its rows. Interactive sessions never write to it |
| IX, disclosure (2) | "the lockbox look was decisive" | "the breakage check and the lockbox look were decisive" | PR (`hints_v2`): "only the breakage check and the lockbox are decisive". Section VII-D says the same and keeps "as pre-registered" |
| IX, availability | "With the cache, readers can repeat both test replays without a model call." | "The repository's README gives the commands and requirements for repeating both test replays from the cache without a model call." | The released README: both commands with `--cache-only`, and the recorded CLI version, a login, the sandbox and the organisers' data as requirements (9.2) |
| IX, models | "again with that interface version and model identifier" | "with the same interface version and `claude-sonnet-5-5`" | ZS `run/summary.json` (8.3) |
| X | "V adds one Opus call that must select an existing candidate through an evidence program" | "that sees the candidate programs and must return a program whose outputs reproduce those of one candidate, so that it can select a candidate but cannot edit a value" | `carnot/verification.py` (`check_evidence`); supplement, Section III |
| XI | "adopted on prior evidence and the absence of detected harm on familiar templates" | adds "their effect on hidden templates was never measured" | Sections II-D and V-E |
| XI, last paragraph | "The hidden questions are longer and more conditional … which is where further work on this pipeline should start." | "Further work on this pipeline should start with held-out templates fixed before development, and should test whether disagreement among the samples marks the wrongly answered questions, which we could not tell on the test set." | Section V-F: split and unanimous votes could not be told apart |
| V-F | "Third, our synthetic panels were too easy to expose such errors"; "We have no indication that arithmetic or rendering contributed" | no longer numbered as a cause; "The specifications give no reason to suspect arithmetic or rendering, although no hidden case can be inspected" | The third item explained why the checks missed the errors, not what caused them; the reason given shows agreement with the specification, not a diagnosis |

**Wrong or unclear grammatical subject, reworded without a change of content:** "Each question publishes a specification"; "Neither measure checks" (now "Neither exact execution nor rendering"); "The equivalence is the scorer's own"; the adoption rule's "forced onto every tuning-eval question in both modes, neither score is detectably lower"; "Decomposed, the unit hint alone"; "Train's dimensionless gold holds"; "every other R3 answer replayed R1's cached responses"; "took the development leaderboard to 1.000000" (the clause is gone; the score is in Section V-B); "R1's noted that"; "without manual edits, including to formatting"; disclosure (4), "which uses the leaderboard"; "A pre-registered continuation replayed … and authored"; "the pre-registered rule stopped the study"; "P lost and gained no final answer"; "divide the samples".

**Announcements and repeated statements removed:** "Two properties of the task shaped the design"; "What we add is …" before the list of contributions; the first-sample clause in contribution 2 (it stays in the abstract and Section VI); "so that the executed program's value is the submitted value" in the related work (it stays in contribution 1 and Section III-D); "Two prompt changes need detail"; "The public record supports three observations and suggests possible causes"; "These are hypotheses" after the label; "the causes named in Section V-F are hypotheses" in XI; the second "pre-registered with the disclosure" sentences in VII-A and VII-D (disclosures 3 and 2 carry them); "Later lockbox results were read as aggregates only" in VIII (it is in IV-A); the one-sentence "Resource use" paragraph (its pointer to Table VI moved to "Models"); the pointer in the caption of Fig. 1 to the section the figure is in; "none was submitted" in the text of X (the caption of Table VII says it). "Decisive" occurs once instead of five times and "pre-registered" 16 times instead of 17.

**Layout:** the three limitation labels of Section XI start paragraphs of their own; the three-part prompt description of III-A and the synthetic-set description of VII-B are split into shorter sentences.

### 10.3 Entries not acted on

- **Title** (2 entries): kept on the author's instruction of 2 November (section 7).
- **II-A and II-C** both describe the three kinds of field: one gives the form of the gold strings, the other the scorer's comparison. Both are needed.
- **II-D, "We assume, but cannot verify"**, and **IV-A, "a sensitivity check and not an independent replication"**: the audit itself cites the first as the careful wording and calls the count in the second essential.
- **IV-B, "The author approved …"**: the third person is deliberate (section 7.1).
- **V-E, "after all of the model-selection decisions above"**: the order of events matters for a system that was selected.
- **VI, "not every floating-point pipeline"**: the limit of the replay (9.3).
- **VII-A, "two conventions are too few to establish this"**: it answers a reviewer's point (8.2); the same remark one sentence earlier was removed instead.
- **VIII:** the three case reports, "Among the inspected errors we found no arithmetic-execution or formatting failure" and the sentence on R1's one slot are the evidence itself.
- **IX, disclosure (5)** (the two incidents) and "none of them informed a decision" in **disclosure (6)**: the list of disclosures is the formal record and stays complete, also where the body says the same.
- **Acknowledgment** (3 entries) and **References** (1 entry): the AI-use disclosure and the organisers' required entries.

Partly acted on: the receipt and hash of R4 stay in V-D (section 7.1) and only the sentence order changed; the opening exception of VIII stays.

### 10.4 Rows of earlier sections whose quoted wording changed

The sources are unchanged; only the sentences differ.

- Section 2: "all six at the first attempt" is now "no candidate was rejected"; "Backup replaces primary in H-mode; no retrieval" is now the sentence of 10.2, first row.
- Section 8.3: the sampling row and the worked-examples rows keep their sources; the paper's sentences are those of 10.2.
- Section 8.4: "with one run per configuration" is superseded by 10.2, third row.
- Section 9.3: "All 93 fraction slots lost unless fractions are reconstructed, which recovers 64" and "29 to 80 of the 872" are now the per-rule sentence of 10.2; "replaying one run's programs …" is now "re-executing …".

### 10.5 Statements removed, and where the fact remains

| Removed | Where the fact remains |
|---|---|
| II-C: "We give official scores to six decimal places, as the organisers do." | Caption of Table II; the ranking sentence of II-C |
| III-A: "this fallback was declared in advance" | PR; not needed for the description |
| III-F: "The rule is fixed, derived from train and uses only these public fields." | II-D ("built from train alone"), the definition in III-F, and IX ("routing is derived from train") |
| V-A: the tuning-noex scores of R4's seen route and of R0 | Table II |
| V-B: "so we name them by label and cite …", "so the R0 row is also theirs", "the portal accepted both uploads" | Table III; the first sentence of V-B |
| V-F: "so these questions can be answered" | The count of eight teams stays |
| VII-B: "which does not show that fully specified financial reasoning is solved" | The sentence is now limited to "the fully specified problems that the model wrote" |
| VII-C: "never from the question's own template"; "We observed that the organisers do not use slot names consistently"; "Under the registered rule" | "from *other* templates"; the observation stays without the attribution; Table IV |
| XI: "A held-out-template check would have had to be fixed before method development." | The last paragraph now recommends it |
| XI: "its logs and replay checks make the development decisions auditable" | Contribution 4 and Section IX |
| Abstract: the validator clause; "one short" | Section III-A |

The sentence of II-B on hash checks was first removed and then restored in shorter form ("every run hash-checks the files against the release manifests"), because it is the paper's only support for "we made no changes to the data".

### 10.6 Checks after the edit

- **Numbers.** `number_diff.py` against the sources of commit `7a1fbba` (kept locally in `paper_backups/second_camera_ready_5b771934/`, which is not part of the release): 0 tokens added, 0 removed. Two existing tokens have a new use: "4 of 1,616" (10.2) and "30" (the third rule's lost decimal slots).
- **Independent check.** A separate read-only pass compared all 74 changed passages of `main.tex`, the table and figure changes, and the removed sentences with the run files, the code and the logs. It found no statement that the records contradict. It found three wording defects in the new text (in the abstract a pronoun that pointed at the 580 and a clause in which the program was "rendered"; in XI, panels that "differed between systems") and twelve smaller points, of which eleven were applied and one needed no change; they are part of 10.2. It also found four places in `RESPONSE_TO_REVIEWS_20261118.md` that described the previous wording; they are corrected.
- **Build.** `pdflatex` → `bibtex` → `pdflatex` ×2: 10 pages, 0 undefined references or citations, 0 `Overfull \hbox`, 0 LaTeX warnings; all 13 fonts embedded; title and author in the metadata. The right column of the last page is a little more than half used.
- **Encoding.** `main.tex`, the tables, the figure and the standalone copy are LF-only without control characters.
- **Length**, by `verify/paper_length.py` (the same two measures as the outside script used in section 9): source 7,601 whitespace-separated tokens (second build 7,612; first build 7,636; submitted 7,135); extracted PDF text 9,134 words (9,125; 9,100; 8,470). The abstract has 250 words by whitespace count. The paper is as long as before: the removed repetition is balanced by statements that became more exact.
- `python -I paper/build_facts.py --check`: "facts.json up to date". `python -m carnot.continuation_state_v1 verify`: exit 0. `carnot/sandbox/executor.py` is unchanged (SHA-256 `7d15a38c…`).
- The supplement is unchanged (SHA-256 of the PDF `37273617…`); no statement in it describes the paper wrongly after the edit.

### 10.7 Deliverable

- `working_notes/carnot_finreason2026_task1_working_notes.pdf` (a copy of `main.pdf`): SHA-256 `137febf630231b5790469cb7a32374e3b36a8bda7d6b2858e828bbb2a2a06aa0`, 267,715 bytes, 10 pages, US letter.
- `working_notes/carnot_working_notes_standalone.tex`: regenerated with `verify/flatten.py`; it compiles to the same 10 pages with identical extracted text.
- The public repository holds the build of section 9 until the author pushes this one, and the author uploads the PDF through CyberChair SC03. Neither was done here.
- Confirmed by the author on 19 November 2026: the Acknowledgment's wording for the model that drafted the camera-ready revisions ("the camera-ready revision by Claude Fable 5, model `claude-fable-5-2`"), and the scope note of the licence in the release README (8.7). Both were open in 8.8 and 9.6; neither text was changed.
- Decided by the author on 19 November 2026: the outside documents of 18 November 2026 are left out of the public release (10.9).
- Still for the author to decide: whether this build replaces the public one.

### 10.8 Release rebuild

- `release/make_release.py` is unchanged. After the rebuild the three archives again have the SHA-256 values of release `v1.0` (`1aa6fb41…`, `af27d880…`, `df255815…`), and `ARTIFACTS.md` and the release `README.md` are byte-identical to the pushed ones. No archive has to be uploaded again.
- Relative to commit `7a1fbba` the tree differs in the paper's sources and PDF (`main.tex`, four tables, the figure, `main.pdf`, the deliverable PDF, the standalone copy), `paper/VERIFICATION.md`, `paper/README.md`, the response letter, `working_notes/verify/derived_strata.py` and `MANIFEST.sha256`. It gains `working_notes/verify/writing_audit_checks.py` and `working_notes/verify/paper_length.py`, and it no longer holds the four outside files of 10.9 that commit `7a1fbba` contained.
- `release/verify_release.py release_staging`: all four checks passed (69,277 rows in the cache snapshot; every zip passes its self-test; no forbidden path; `MANIFEST.sha256` matches the tree).
- `release/audit.py`: 0 blockers, and the same eleven decision items as before. The report is `release/AUDIT_REPORT.md`, which is not part of the released tree.

### 10.9 Outside documents left out of the public repository

Decision of the author on 19 November 2026. Five files that were not written in the sessions that produced the paper are kept by the author and are not released (`release/exclude.txt`):

- `working_notes/REVIEW_REVISION_ASSESSMENT_20261118.md` and `working_notes/EXPERIMENT_RECOMMENDATIONS_20261118.md` (9.1);
- `working_notes/verify/revision_assessment.py` and `working_notes/verify/revision_assessment_page10.png` (9.1, 9.6);
- `working_notes/AI_WRITING_AUDIT_20261118.md` (10.1).

The first four were part of the tree pushed as commit `7a1fbba`; the fifth was never pushed. Sections 9 and 10 still name the files, because they record what was checked and why. No number in the paper or the supplement is traced to them alone:

- The two counts that section 9 took from the outside script (none of the 70 decimals is exactly representable as a double; 2 are given back when the nearest double is printed with the gold's number of decimal places) are now printed by `verify/derived_strata.py`, item 3, which gained one output line. The label of the line before it was corrected from "no double-precision value can match" to "fractions plus decimals that the nearest double does not print back", in keeping with 9.2.
- The length figures of 9.4 and 10.6 are printed by `verify/paper_length.py` (new): 7,135 and 7,601 source tokens, and 8,470 and 9,134 words of extracted PDF text, for the submitted version and for this build. The figures for the first and second camera-ready builds (7,636 and 7,612 tokens; 9,100 and 9,125 words) were measured in the same way on the files of those builds.

The critique and the wording audit of 2 November 2026 (sections 6 and 7) are also outside documents. They have been public since the first release and stay.

## 11. Check against the conference's camera-ready instruction (19 November 2026)

### 11.1 What prompted it

The author asked for a check of the conference's camera-ready instruction for the Cup (the page named in `ORGANISER_REQUIREMENTS.md`, R7, where its rules are quoted). By then the author had pushed the build of section 10: the public repository was at commit `af54b6c`, with the PDF of 10.7. The instruction sends authors to IEEE PDF eXpress, so the IEEE Author Center's list of what PDF eXpress checks was read as well (R7).

### 11.2 Each rule and the state of the paper

"Before" is the PDF of 10.7 (SHA-256 `137febf6…`).

| Rule | Check | Before | Now |
|---|---|---|---|
| At most 10 pages with figures, tables and references | `pdfinfo` | 10 pages | 10 pages |
| IEEE conference template | `main.tex`: `\documentclass[conference]{IEEEtran}`; no length is changed | met | met |
| Page size 612 x 792 points | `pdfinfo` | met | met |
| All fonts embedded and subset | `pdffonts`: 13 fonts, all Type 1, all embedded, all subset | met | met |
| Graphics at least 300 dpi | `pdfimages -list`: no raster image; the one figure is drawn with TikZ | met | met |
| Acrobat 5.0 compatibility; PDF version 1.4 or later | `pdfinfo` | PDF 1.5 | PDF 1.4 |
| No bookmarks or links | byte search of the file | **not met**: an outline (`/Outlines`), 92 `/Link` annotations and 46 `/URI` actions, written by `hyperref` | met: none of `/Outlines`, `/Annots`, `/Link`, `/URI`, `/Dests` occurs |
| No password, form, script or attachment | `pdfinfo`; byte search | met | met |
| No crop marks, date stamps or other marks | the template prints no page numbers or running heads in conference mode | met | met |
| "Optimized" (linearised for fast web view) | `pdfinfo`: "Optimized: no" | not done | not done |

The last row is not met and was left: pdfTeX does not linearise a file and no tool that does is installed here. It is a Distiller setting in the instruction and is not in the Author Center's list of checks; PDF eXpress decides.

### 11.3 What changed

Only the preamble of `main.tex`, and with it the standalone copy:

- `\pdfminorversion=4` and `\pdfobjcompresslevel=0` before the class is loaded, which gives PDF 1.4.
- `hyperref` is no longer loaded. The title and the author are written into the file's metadata with `\pdfinfo`, and the repository address is typeset through `\urldef` of the `url` package, because `\url` no longer expands a macro without `hyperref`.

No text changed. The text that `pdftotext` extracts is identical to that of the pushed build; every one of the 10 pages renders to an identical image at 60 dpi; `number_diff.py` against commit `af54b6c` shows 0 tokens added and 0 removed; the build has 0 undefined references, 0 `Overfull \hbox` and 0 LaTeX warnings. The source count of `verify/paper_length.py` rises from 7,601 to 7,644 tokens because of the preamble lines and their comments, and the response letter quotes the new figure; the extracted text still has 9,134 words.

### 11.4 Deliverable, and what was not checked

- `working_notes/carnot_finreason2026_task1_working_notes.pdf` (a copy of `main.pdf`): SHA-256 `a74bec6824f12c2d824dbca4b0e9718a229d661dc1acf2cc797bd90aea3405a4`, 225,817 bytes, 10 pages, US letter, PDF 1.4. It replaces the file of 10.7.
- `working_notes/carnot_working_notes_standalone.tex`: regenerated; it compiles to the same 10 pages with identical extracted text.
- **PDF eXpress itself was not run here** (the author ran it later; see 11.8). Only the author can do that (it needs an account and the conference ID). The file to submit in STEP 6 of the instruction is the one that PDF eXpress returns or passes; if it differs in bytes from the file above, its SHA-256 should be recorded here.
- The copyright form (STEP 3), the registration receipt (STEP 7) and the choice of presentation mode (STEP 8) are the author's.

### 11.5 A point outside the instruction: IEEE's posting rules (decided by the author, 11.7)

STEP 3 transfers the copyright through IEEE's electronic form. IEEE's rules for authors who post their papers (IEEE Author Center, "Post Your Paper", https://conferences.ieeeauthorcenter.ieee.org/get-published/post-your-paper/, read on 19 November 2026) then apply to the copies in the public repository: the camera-ready PDF and its LaTeX sources, and the version submitted for review in `working_notes/archive/`. As read there, the accepted paper may be posted on the author's personal website, the employer's website or institutional repository, arXiv, TechRxiv or a funder's repository, with IEEE's copyright notice; the final published paper may not be posted; and a preprint posted earlier is to be replaced after acceptance. The page does not say whether a repository on a code-hosting site counts as a personal website. Nothing was changed for this point when it was raised; the release README already said that the paper and its sources are outside the MIT licence (8.7). The author's decision is in 11.7.

### 11.6 Release rebuild

- The three archives again have the SHA-256 values of release `v1.0`, and `ARTIFACTS.md` is unchanged, so no archive has to be uploaded again.
- Relative to commit `af54b6c` the tree differs in `main.tex`, `main.pdf`, the deliverable PDF, the standalone copy, `paper/VERIFICATION.md`, `paper/ORGANISER_REQUIREMENTS.md` (new section R7), `paper/README.md`, the response letter, the release `README.md` and `MANIFEST.sha256`, and it gains the three `README.md` files of 11.7.
- `release/verify_release.py release_staging`: all four checks passed. `release/audit.py`: 0 blockers and the same eleven decision items.
- The supplement was not rebuilt. It is not submitted to the conference, and it still loads `hyperref`.
- The author pushed this build as commit `e7f588a` (checked on 19 November 2026: the public PDF has the SHA-256 of 11.4). The author also published release `v1.1` with the same three archives; their digests equal `ARTIFACTS.md`. Its tag is on `af54b6c`, the commit before this build.

### 11.7 IEEE copyright notice (author's decision of 19 November 2026)

The author decided to keep the paper's files in the public repository and to add IEEE's notice. Relative to commit `e7f588a` this changes the release `README.md`, `paper/README.md`, `paper/ORGANISER_REQUIREMENTS.md` (one row in R7), `paper/VERIFICATION.md` and `MANIFEST.sha256`, and adds three `README.md` files; the paper's PDF and sources are untouched. After the rebuild `release/verify_release.py` passed all four checks and `release/audit.py` reported 0 blockers and the same eleven decision items. The wording is IEEE's (R7, last row), with the year 2026:

"© 2026 IEEE. Personal use of this material is permitted. Permission from IEEE must be obtained for all other uses, in any current or future media, including reprinting/republishing this material for advertising or promotional purposes, creating new collective works, for resale or redistribution to servers or lists, or reuse of any copyrighted component of this work in other works."

IEEE asks for it "on the initial screen displaying IEEE-copyrighted material", so it stands on every page of the repository that shows the paper's files:

- the release `README.md`, the repository's first page (`release/templates/README.md.tmpl`), below the licence paragraph, whose confirmed wording (8.7) is unchanged;
- `paper/README.md`, new section "Copyright of the paper";
- `paper/working_notes/README.md` (new), next to the camera-ready PDF and its sources;
- `paper/working_notes/archive/submitted_20261102/README.md` (new); the other files of that folder are unchanged (`main.tex` SHA-256 `771537ef…`, PDF `fd2d157d…`, as in section 7);
- `paper/working_notes/supplement/README.md` (new), for the passages that the supplement reproduces.

Each place says that the copies are the author's versions and not the version published by IEEE, and that the DOI will be added when the paper is published. Three things were deliberately not done:

- The notice is not printed in the PDF. The file sent to the conference must carry no mark that the official version lacks (R7), and the repository holds that same file.
- No DOI is given, because none exists yet.
- The version submitted for review stays in `archive/`. IEEE's page says that a preprint posted earlier is to be replaced by the accepted version; the author chose to keep the files, and the folder's new `README.md` points to the accepted version.

The notice says that the copyright "is transferred to IEEE with the conference's copyright form". Whether the author had signed the form when this was written is not known here.

### 11.8 IEEE PDF eXpress: the certified file (20 November 2026)

The author pushed the notices of 11.7 as commit `bcc1ff8`, ran the PDF of 11.4 through IEEE PDF eXpress, and passed the returned file and the service's message to this session. The message gives the paper ID 2026444853, calls the returned file IEEE Xplore compatible, and says that it is the file to submit to the conference's final paper collection site.

- **Returned file:** `2026444853.pdf`, SHA-256 `a40e9d44cd7ddfb4f24b8f460ca8b2c91098152674589bfb4cd0fbbca3c4345f`, 244,679 bytes, PDF 1.4, 10 pages, US letter.
- **Certification:** its document properties and its XMP metadata give the creator as "Certified by IEEE PDFExpress at November 19, 2026 19:59:39". The producer and the creation date are those of the file of 11.4, which is consistent with that file having been the one checked.
- **Same paper.** Checked read-only on a copy in an empty folder: the text that `pdftotext` extracts, plain and with `-layout`, is identical to that of the file of 11.4, and every one of the 10 pages renders to an identical image at 100 dpi. The differences found are the certification stamp, an added metadata stream and the processing record described below; the file is 18,862 bytes larger.
- **Still meets the rules of 11.2:** 13 fonts, all Type 1, all embedded and subset; no raster image; none of `/Outlines`, `/Annots`, `/Link`, `/URI`; not encrypted; no form or script.
- **The certified file is not in the public repository.** Besides the stamp, the service's processing software wrote its own record into the file: the registration name of the service's operator (an administrative e-mail address), a registration key of that software, and a path on the service's server that contains an account number. The release audit found the address when the file was tried as the repository's copy. These belong to the service, and publishing them is not the author's call, so the repository keeps the file of 11.4, which is the one that was sent to PDF eXpress and has the same text and pages (`working_notes/carnot_finreason2026_task1_working_notes.pdf` and `main.pdf`, SHA-256 `a74bec68…`). The author keeps the certified file; a copy is in the local folder `paper_backups/`, which is not released.
- **Not done here:** the upload of the certified file (STEP 6), the copyright form (STEP 3), the registration receipt (STEP 7) and the choice of presentation mode (STEP 8) are the author's, and whether they are done is not known here.
- **Release rebuild:** the three archives are unchanged; relative to commit `bcc1ff8` the tree differs in `paper/working_notes/README.md`, `paper/README.md`, `paper/VERIFICATION.md` and `MANIFEST.sha256`. `release/verify_release.py` passed all four checks, and `release/audit.py` reported 0 blockers and the same eleven decision items.
