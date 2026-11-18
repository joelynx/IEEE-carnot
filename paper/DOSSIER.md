# Working Notes dossier: team carnot, FinReason Cup 2026 Task 1

This is the complete record the Working Notes are written from. It describes **what was built and run**, not what was planned; where the two differ, the difference is stated. Every number here was observed in this repository's logs, data or code (tag **[O]**) or is inferred from observed facts with the reasoning given (tag **[I]**). The numbers are regenerated, with their sources, by `python -I paper/build_facts.py` → `paper/facts.json` and `paper/TABLES.md`. **If a number here and `facts.json` disagree, `facts.json` wins; report the discrepancy.**

Record compiled 12 October 2026 and updated the same day after R4. Organiser requirements are in `paper/ORGANISER_REQUIREMENTS.md`; instructions for writing the paper are in `paper/AGENT_INSTRUCTIONS.md`.

---

## 1. Identity and final state

- **Team name:** `carnot` (exact; the portal casefolds it). **Author on record:** Joel Jobi (git config; signed the organiser email). **The full author list and affiliations must be confirmed with the user** before writing; single-blind review requires them. The Claude subscription organisation shown by `claude auth status` was "IITD-AD Students"; this is not an affiliation statement.
- **Final (latest accepted) test submission: R4** [O]. Receipt `test-20261012T170418Z-811e06a0839acd614d49f03127d8c684c79823ddc4473a9c`, accepted 2026-10-12T17:04:18Z; ZIP SHA-256 `cec784e29f40f277d86ee6a38701e22ca117f1102abd5541083cefc8c60e0cc3`; predictions SHA-256 `e0ef54ebb142a85e3d7c6ec305c6530058b919db3c63e8328810099627913067`; run `20261012T165330Z_r4_test928_S` (`submissions/registry.jsonl`; `facts.json#submissions.latest_test`). Its cached replay is byte-identical (`paper/REPLAY_CHECK.md`).
- **Earlier accepted test submissions:** R0 (ZIP `300997af…`, 2026-10-11T20:07:32Z), R1 (ZIP `897c4e55…`, 2026-10-12T06:33:34Z) and R3 (ZIP `ea491873…`, 2026-10-12T13:43:39Z). R2 was packaged (ZIP `eee71e5f…`) and **not uploaded** [O].
- **Development leaderboard, two uploads** [O]; portal responses are stored verbatim in the registry:
  - **R0:** Final answer 0.998333, Reasoning steps 0.998056, rank 15 (2026-10-12T04:25:33Z).
  - **R4:** Final answer **1.000000**, Reasoning steps **0.999167**, rank 14 (2026-10-12T16:52:17Z).
  - Before R4's upload the user reported rank 16.
- **Test scores are unknown.** They are hidden until final results (organiser email). Nothing in the paper may imply a test score.

## 2. Task, data and scoring (for the paper's background section)

**Data** [O] (`facts.json#data`, computed from the organiser downloads):
- Questions: train 2,900; dev 290; development leaderboard 580; test 928.
- 290 seen templates (58 advanced, 116 basic, 116 intermediate), in 58 topics across 12 domains.
- Train answers: 2,700 decimal and 200 categorical (enum). Train has 5,180 slot instances. Slots per question: 0 for 320 questions, 1 for 690, 2 for 1,180, 3 for 710.
- Gold fields in train+dev: 8,888 (3,091 rounded half-up, 5,379 exact, 418 enum).
- Releases used unchanged: development data contract `task1-v4`, development manifest SHA-256 `78ba2922…22f7`, test release `task1-v4-test-questions-20260901-r2`. Both release manifests were hash-checked on every run (`carnot/common.py: verify_release`).

**Test strata** [O+I]. Test = 580 seen-template + 348 hidden-template questions. Our train-only routing rule (§3.6) flags exactly 348 test questions as novel, equal to the scorer's frozen constant `test_private_hidden: 348` (`finreason_task1/scoring.py`, line 35). The development leaderboard and every labelled set route 0 questions to the novel path.

**Scoring** [O] (`finreason_task1/scoring.py`, PLAN.md §2.5):
- A final answer is correct only on an exact match: an exact `Fraction` for exact fields; for half-up fields, the value after ROUND_HALF_UP to the published decimal places. Enums are case-sensitive.
- The reasoning-steps (checkpoint) score credits slot values matched by `slot_id`.
- Scores aggregate hierarchically (domain → topic → case).
- **Ranking** (organiser-confirmed): (CombinedFAC, HiddenFAC, CombinedCheckpoint), each quantized to 6 dp with round-half-even; combined = ½ seen + ½ hidden.
- One invalid row rejects a whole submission file.

## 3. The system as built

Code: `carnot/` (Python standard library only, plus the organiser toolkit, unmodified). One command runs any configuration on any split: `python -m carnot.run --config configs/<name>.json --split <split>`.

### 3.1 Pipeline (per question)
1. **Prompt.** System prompt `carnot/prompts/pot_system_v1.txt` (SHA-256 `02fa7732…`), plus 3 worked examples (§3.3), the question verbatim, and a table of required outputs (`"final"` and every slot id, each with its description and spec rendered as a short hint).
2. **One program per sample.** The model writes a Python `solve()` returning a dict with `final` and every slot id (program of thought).
3. **Exact-arithmetic sandbox** (§3.4) executes it.
4. **Spec-driven formatter** renders every field from its `answer_spec`/`result_spec`. Exact fields become a minimal finite decimal or an irreducible `n/d`; half-up fields are quantized and padded; enums are checked for membership. It round-trips all 8,888 train+dev gold fields byte for byte [O] (test in `carnot/tests/`).
5. **Retries.** Up to 2 per sample, re-prompting with the failing program and the error text when execution fails, a key is missing, or a field cannot be rendered.
6. **Voting** over N samples (§3.5).
7. **Validator gate.** Every row passes the toolkit's `validate_prediction_record` before it is written.
8. **Fallback** (pre-declared): a field that is still invalid is omitted (a final becomes `null`). **No value is ever edited.** The planned chain-of-thought fallback was never built, and no run needed it: all test runs filled every final and all 1,492 slots [O].
9. **Packaging.** The toolkit CLI `validate` → `package` → `validate-zip` for every submission [O].

### 3.2 Model access [O]
- **Claude models through Claude Code CLI 2.1.296 in headless mode** (`claude -p`) on a Claude subscription; no API key.
- Exact flags: `-p --safe-mode --model <id> --effort <level> --system-prompt-file <file> --tools "" --strict-mcp-config --disable-slash-commands --permission-prompts none --max-turns 1 --no-session-persistence --output-format json`. The prompt goes on stdin.
- Calls run from an empty temporary directory with a scrubbed environment. API-key and model/effort override variables are removed; `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and, from 12 October, `DISABLE_AUTOUPDATER=1` are set (`carnot/llm_client.py`).
- **No temperature or seed control exists**, so samples are independent calls. **Reproducibility comes from a response cache** (SQLite) keyed by model, effort, CLI version, flag version, SHA-256 of the system and user prompts, sample index and attempt tag. Replaying any run from the cache reproduces it bit for bit [O]: re-running R1 and R3 on the leaderboard set reproduced R0's ZIP `fc3089da…` exactly.
- Model IDs used: `claude-sonnet-5-5` (R0, R1, R3), `claude-opus-5-5` (R2 and a diagnostic), `claude-fable-5-1` (synthetic-set authoring and cross-check only), `claude-haiku-5-5` (difficulty probe only). Each call's returned model ID was recorded; across all 17,592 cached calls it matches the requested ID in every case [O].

### 3.3 Worked examples: generation and use [O] (`carnot/exemplars.py`, `exemplars/r0_exemplars.json`)
- **Three categories,** defined from public spec fields:
  - (A) decimal final with ≥ 2 exact slots including a percent or ratio unit;
  - (B) enum final with ≥ 1 decimal slot;
  - (C) decimal final with ≥ 1 half-up slot.
- **Generation:** for each category, templates from the exemplar pool (tuning set minus tuning-eval) are visited in a seeded order. One case per template is solved zero-shot by the R0 solver. A program is kept only if the toolkit scorer gives a correct final and every slot correct against train gold. Two verified programs per category (distinct templates) are kept, a primary and a backup; all six verified on the first attempt.
  - A: `standard_wacc` (primary), `var.time_horizon` (backup)
  - B: `early_retirement_bridge`, `disclosure_threshold`
  - C: `irr.bond_coupon_reinvestment`, `irr.after_tax_net_sale_cost`
- **Use:** every prompt shows the three primaries. In leave-template-out (H) evaluation, a backup replaces a primary when the question shares the primary's template. **There is no retrieval in the final system.** The planned same-template retrieval (P1) was never built, so same-template worked examples are never shown.

### 3.4 Sandbox [O] (`carnot/sandbox/`)
- **Code policy:** an AST whitelist (imports only `math`, `fractions`, `decimal`, `itertools`, `functools` and the helper module `finq`; no classes, `with`, `eval`/`exec`/`open`, dunder names or private attributes).
- **Exact arithmetic:** the AST is rewritten so float literals become exact `Q("literal")` rationals and arithmetic operators become exact helpers; integer division is exact. `finq` provides `sqrt`, `ln`, `exp`, `erf`, `norm_cdf`, bisection `solve()` and `round_half_up`. Irrational results are 60-digit `Decimal`s and are allowed only in half-up fields.
- **Isolation:** WSL2 Ubuntu inside `unshare -rmn` (new user, mount and network namespaces; no network; Windows drives hidden by a tmpfs over `/mnt`), per-program rlimits and a 5-second timeout. Sandbox Python 3.14.4.

### 3.5 Self-consistency [O] (`carnot/solver.py`)
N samples per question, then a **per-field plurality vote** on rendered strings. Ties go to the sample agreeing most with the per-field plurality, then to the lowest sample index.

### 3.6 Routing rule `novel_vs_train_v1` [O] (`carnot/routing.py`)
- A question is **novel** iff neither its number-masked text skeleton nor its `(slot_id, description)` signature occurs among the 2,900 train questions.
  - Skeleton: lower-cased, whitespace-normalised, the "Answer format" sentence removed, numbers replaced by `#`.
  - Signature: the ordered list of `(slot_id, description)` pairs.
- The rule reads only public question fields, is built from train only and is applied identically to every question.
- **Counts:** test 348 novel; train, dev, lockbox, tuning-eval and leaderboard 0 (`facts.json#data.routing_novel_counts`).

### 3.7 The submitted systems (`configs/*.json`; SHA-256 values in `facts.json#runs`)

| System | Seen-route questions | Novel-route questions | Test status |
|---|---|---|---|
| **R0** | Sonnet 5.5, effort low, N = 1 | (no routing) same as seen | accepted (safety net) |
| **R1** | = R0 | Sonnet 5.5, effort **medium**, **N = 5**, plurality vote | accepted |
| R2 | = R0 | **Opus 5.5**, effort medium, N = 5 | packaged, **not uploaded** |
| **R3** | = R0 | = R1 plus **unit-hint v2** | accepted |
| **R4 (final)** | R0 plus **unit-hint v2** and **echo notes** | = R3 plus echo notes (they never fire on the 348 novel test questions) | **accepted, latest** |

- **Unit-hint v2** (`carnot/solver.py`, `describe_spec(..., hints="v2")`). In the required-outputs table, a `dimensionless` field is described as "a pure number with no unit; keep the scale of the question's own quantities (do not rescale percentages to fractions unless the description says so)" instead of "a plain number (0.0525, not 5.25)".
- **Caveat to state honestly:** the system prompt was not changed and still says "Outputs in ratio, multiple or dimensionless are plain numbers (0.0525)". In R3 the more specific per-slot hint is what changed behaviour (§5.6).
- **R3's seen-route answers are byte-identical to R0's** for all 580 seen-route test questions [O].

## 4. Evaluation methodology

- **Splits** (drawn once, seed `carnot-splits-v1`, logged in `experiments/lockbox_access.jsonl`) [O]:
  - **lockbox** 870 (all 290 dev + 2 train per template);
  - **tuning** 2,320 (the other 8 train per template);
  - **tuning-eval** 580 (2 per template, from tuning);
  - **exemplar pool** 1,740;
  - **tuning-noex** 2,314 (tuning minus the 6 exemplar cases; used for the convention experiments).
- **Two modes:** S (seen simulation; no retrieval exists, so S differs from H only in exemplar choice) and H (leave-template-out: no worked example or convention example from the question's own template).
- **Official scores** come from the toolkit's `score_submission` on every gold split (hierarchical weights).
- **Paired comparisons** (`carnot/compare.py`) recompute each run's official scores from per-case results and probed per-case weights, and stop if the recomputation differs from the toolkit report. They use a paired bootstrap (B = 10,000, seed `carnot-compare-v1`): S-mode resamples cases within templates; H-mode resamples templates within topics.
- **Run-to-run noise** [O]: three R0 tuning-eval runs with fresh samples gave seen FAC 1.0 / 0.998333 / 1.0, so **σ_run(FAC) = 0.000962 and σ_run(steps) = 0.000481** (`facts.json#sigma_run`).
- **Decision rules, written down before outputs:**
  - **Improvement rule** (PLAN.md §5.6): paired CI excludes 0, Δ > 2σ_run, and a later lockbox look gives Δ > 0.
  - **§4a amendment for changes aimed at the hidden stratum,** which no labelled set can measure (approved 12 October): (a) pre-registration, (b) generic train-driven routing, (c) non-inferiority with the change forced onto all tuning-eval questions in S and H (Δ ≥ −2σ_run and CI upper bound ≥ 0, 4 of 4), (d) non-inferiority on lockbox and leaderboard, (e) no statistic computed on test outputs.
- **Pre-registration log:** `experiments/preregistration.jsonl` holds every candidate's pre-registration (config and code hashes, rationale, pass rule, on-pass/on-fail actions), every result and every incident.
- **Lockbox discipline:** at most 4 looks; **2 used** [O]. Look 1 was R0 (S); look 2 was the hint-only decisive check (two arms, H). Results are read as aggregates only (rule added after look 1; see §7).
- **Development leaderboard:** 1 upload of a planned 6 [O]; used only as a pipeline and distribution-shift check.

## 5. Results

### 5.1 Main results on labelled data [O] (`paper/TABLES.md` T2; official seen scores)

| Run | Split, mode | FAC | Steps |
|---|---|---|---|
| R0 | tuning-eval S (580) | 1.000000 | 0.995675 |
| R0 | tuning-eval H | 1.000000 | 0.995675 |
| R0 (look 1) | lockbox S (870) | 0.996667 | 0.996508 |
| R0 | dev leaderboard (580, official) | **0.998333** | **0.998056** |
| R1 novel path, forced on all | tuning-eval S / H | 1.000000 | 0.996508 |
| R2 novel path, forced on all | tuning-eval S / H | 1.000000 | 0.995556 |
| R3 novel path, forced on all | tuning-eval S / H | 1.000000 | **0.997619** |
| R4 novel path, forced on all | tuning-eval S / H | 1.000000 | 0.997619 (identical to R3) |
| R0 (= R3's seen route) | tuning-noex S (2,314) | 0.999167 | 0.997192 |
| **R4 seen route** | tuning-noex S (2,314) | **1.000000** | **0.998304** |
| **R4** | dev leaderboard (580, official) | **1.000000** | **0.999167** |

**Leaderboard shift check:** the lockbox gave 0.996667 / 0.996508 and the leaderboard 0.998333 / 0.998056. No pipeline or format problem is indicated [I].

### 5.2 Comparison with organiser baselines (development leaderboard; cite by label) [O]

| System | Final answer | Reasoning steps |
|---|---|---|
| Lite (organiser) | 0.234048 | 0.555354 |
| Standard (organiser) | 0.980556 | 0.987725 |
| Advanced (organiser) | 0.984444 | 0.990000 |
| carnot R0 (= R1 = R3 on this set) | 0.998333 | 0.998056 |
| **carnot R4** | **1.000000** | **0.999167** |

R1 and R3 answer every leaderboard question exactly as R0 does (0 novel questions; identical ZIP), so the R0 row is also their leaderboard result. R4 re-solved 32 leaderboard questions (4 with an echoed slot description, 28 with a `dimensionless` field) and changed the answers on 5 [O].

### 5.3 Pre-registered decisions (`paper/TABLES.md` T3) [O]
- **R1 vs R0** (forced, check c): FAC Δ 0; steps Δ **+1/1200** (S CI [0, +0.00167]; H CI [0, +0.0025]). Non-inferior 4/4, so **R1 adopted**.
- **R2 vs R1** (forced, check c): FAC Δ 0; steps Δ **−1/1050** (S CI [−0.00262, +0.00071]), within the −2σ limit (−0.000962) by 0.00001. Passes by rule, but the 5 changed slots were +2 / −3, so **R2 not uploaded** (recommendation accepted by the user).
- **conventions_v1 vs baseline** (tuning-noex, H; 2,314 questions): FAC Δ **−1/1200** (CI [−0.0025, 0]); steps Δ **−1/1800** (CI [−0.0048, +0.0031]). **Rejected.**
- **hints_v2 vs baseline:**
  - tuning-noex H: FAC Δ 0; steps Δ **+19/14400** (CI [0, +0.0035]); 9 questions changed, all fixes; breakage check 1 fixed / 0 broken.
  - **Lockbox look 2:** FAC Δ 0; steps Δ **+1/1800** (CI [−0.0011, +0.0028]).
  - **Passed** (rule: lockbox Δ > 0 and non-inferior FAC). This confirms direction, not significance.
- **R3 vs R1** (forced, check c): FAC Δ 0; steps Δ **+1/900** in S and H. 2 variance slots now right, 4/4 non-inferior, so **R3 adopted and uploaded.**
- **Check (d)** for R1, R2 and R3: the leaderboard ZIP is identical to R0's (0 novel questions; cache replay). No lockbox look or development upload was spent on these, since both would repeat R0's numbers.
- **R4** (pre-registered; changes the seen route):
  - *Step 1, safety gate on tuning-noex S vs R0:* finals 2 fixed / 0 broken (both tax questions); slots 9 fixed / 1 broken. FAC Δ +1/1200 (CI [0, +0.0021]); steps Δ +1/900 (CI [+0.0005, +0.0017]). These tuning figures are biased in R4's favour, because both fixes target failure modes seen in tuning.
  - *Step 1b, §4a(c) vs R3:* identical in S and H.
  - **Step 2, decisive, one development upload:** Final answer 0.998333 → **1.000000** and Reasoning steps 0.998056 → **0.999167**. Passed (rule: neither drops, at least one rises).
  - The lockbox was not used, because its tax cases had been inspected after look 1.

### 5.4 Resource use [O] (`paper/TABLES.md` T7; every distinct call, from the cache)
- **Calls by model and effort:**
  - Sonnet 5.5: 4,131 at low and 8,541 at medium
  - Opus 5.5: 4,691 at medium
  - Fable 5.1: 41 at high and 63 at medium
  - Haiku 5.5: 125 at medium
- **Totals:** 17,592 calls, **≈ $175.75 list-price equivalent** (the CLI's `total_cost_usd`). The work ran on a subscription, not per-token billing.
- **Test runs** (fresh calls; cost-equivalent):
  - R0: 928 calls, 12,326 thinking tokens, $12.75
  - R1: 1,743 calls, 78,269 thinking tokens, $9.98
  - R2: 1,740 calls, $19.39
  - R3: 90 calls, $0.45; every other R3 answer replayed R1's cache.

## 6. What we tried that did not make the final system (ablations and negative results)

### 6.1 A stronger model on the hidden route (R2, Opus 5.5)
- **Pre-registered diagnostic** (`experiments/diagnostics/opus_vs_sonnet_conventions_v1.json`). Setting: the 4 tuning-eval cases where R1 still missed a slot (2 templates), 10 samples per case per arm, same prompt. Results [O]:
  - **Sign convention** (`portfolio_single_factor`): fresh Sonnet 0/20, Opus 20/20.
  - **Variance units** (`two_asset_perfect_correlation_sd`): both 0/20.
  - Non-target fields: 80/80 in both arms.
- **R2's forced tuning-eval run:** +2 slots (sign) and −3 slots [O]:
  - `interest_from_known_total`: the slot is labelled "Exact annual compound multiplier", but the gold is the cumulative multiplier; Opus returns the annual factor.
  - `credit_rebate`: the eligible rebate was lost on a 3–2 vote.
- **Reading [I]:** Opus reads slot descriptions more literally. That helps where the organisers' gold follows the wording and hurts where it does not.

### 6.2 A synthetic "hidden-like" labelled set
- **Purpose:** to measure hidden-stratum gains, which no released labelled set allows.
- **Construction** (`carnot/synth/`):
  - New templates written in the competition format by a model outside the comparison: Fable 5.1, which saw tuning-set questions only.
  - Exact reference programs run in the sandbox, with parameters sampled by our own seeded code.
  - Every record passes the toolkit validators; gold scores 1/1 against itself; every question is novel under the routing rule.
  - The question text follows train-derived house-style limits, and the "Answer format" sentence reproduces all 3,190 train and dev questions exactly.
- **Results** [O]:
  - **v2 rules** (train-like style): 25 templates; blind cross-check 25/25 agree; **the Haiku 5.5 probe solved 24/25 templates perfectly** on 4 disjoint probe instances each.
  - **v3 rules** (advanced only; ≥ 5 steps; a threshold decision, solve-for or multi-period timing): pilot of 5 templates, **5/5 trivial for Haiku** (20/20 probe questions, 100/100 fields).
  - Both stopped by pre-registered floors; nothing from this set is used anywhere in the submitted systems.
- **Reading [I]:** when every convention is stated, these finance problems are solved perfectly even by the smallest Claude model through exact program-of-thought. A set built that way cannot separate systems. Leaving conventions unstated would make the gold follow the author's conventions rather than the organisers'.
- A hand-off package for a second, non-Claude author was built and verified but **never used** (`carnot/synth/handoff.py`).

### 6.3 Cross-template slot-convention examples (`conventions_v1`)
- **Idea:** for each required slot, show up to 2 questions from *other* templates that use the same slot name or description, with the slot's reference value.
- **Result on tuning-noex (H):** rejected (§5.3). It fixed 3 slots, broke 8 (mostly `portfolio_single_factor` in a different template) and broke 2 tax finals [O].
- **Finding [O+I]:** the organisers do not use slot names consistently across templates, so borrowing a convention from another template misleads about as often as it helps.

### 6.4 The hint-only change (adopted as R3)
- The `dimensionless` hint was our own error. Train's `dimensionless` gold holds growth multipliers, counts, pip differences, sentiment fractions and squares of the question's own quantities (a variance of 225 from a 15-percent deviation), never percentages rescaled to fractions [O].
- Removing the false claim fixed every `two_asset_perfect_correlation_sd` variance slot in tuning and broke nothing [O].

### 6.5 Echo notes for the tax confusion (adopted in R4, with the hint fix extended to the seen route)
- **The failure:** tax questions end with a sentence that repeats the slot description ("Report taxable income."), while the final answer is the tax. Models answered the sentence: gold 100.00, predicted 400.00 [O].
- **The rule:** when a sentence of the question repeats a slot description verbatim, the required-outputs table says that sentence belongs to the slot and is not the definition of the final answer. It is generic in form but narrow in effect.
- **Scope** [O]: in train+dev it fires on 22 questions of exactly 2 templates (`taxcalc.standard_deduction`, `taxcalc.capital_gains`), whose final is always the tax. It fires on 4 leaderboard, 4 seen-route test and 0 novel-route test questions.
- **Result:** together with the seen-route hint fix, it took the development leaderboard to Final answer 1.000000 (§5.3).

## 7. Error analysis (tuning data only; `paper/TABLES.md` T8) [O]

- **Every remaining error on labelled data is a misread convention, not a calculation or formatting failure.** Final answers are at or near ceiling.
- **R0 tuning-eval S:** 5 slot misses and 0 wrong finals:
  - 2 × `portfolio_single_factor :: factor_ratio_trace` (sign: the model multiplies by the sensitivity);
  - 2 × `two_asset_perfect_correlation_sd :: variance_trace` (units);
  - 1 × `interest_from_known_total :: growth_multiplier_trace` (annual vs cumulative).
- **R3 forced, tuning-eval S:** 2 slot misses (the sign convention only).
- **R4 seen route on tuning-noex S (2,314):** 0 wrong finals and 6 slot misses: 5 sign convention (`portfolio_single_factor`, two templates) and 1 compound multiplier. The R0 baseline on the same set had 2 wrong finals, both tax.
- **Baseline on tuning-noex (2,314):** 14 slot misses and 3 wrong finals. The wrong finals are all `taxcalc` (`standard_deduction` ×2, `capital_gains` ×1), returning taxable income or gain instead of the tax.
- **Lockbox look 1** (R0) had 3 wrong finals, all `taxcalc` (`standard_deduction`, `capital_gains`), the same confusion. **Disclosure:** these 3 lockbox cases were inspected individually. After that, lockbox results were read as aggregates only, and every later fix was justified and measured on tuning data. The `taxcalc` confusion also occurs on tuning data. No fix for it was adopted.
- **Self-consistency barely helps on systematic errors** [O]: R1's 5 votes at medium effort fixed 1 of R0's 5 slot misses, and 0 of 40 fresh Sonnet samples fixed the two remaining conventions.

## 8. Integrity, provenance and disclosures (state these in the paper)

1. **Every test answer was produced by the logged system** (config hash, code, CLI version, cached responses). **No prediction was edited by hand**, including formatting.
2. **No test output informed any decision.** All model selection used train, tuning, lockbox or the development leaderboard. One caveat to disclose: R1's written rationale mentioned that R0 had spent more thinking tokens on test questions (12,326) than on tuning-eval (268). That is a usage statistic of the R0 test run; R1's adoption rested on the pre-registered check (c) [O].
3. **No ID- or text-specific rules.** All per-question behaviour is generic. Routing is train-driven; worked examples come from the exemplar pool, a subset of train.
4. **FinChain** (answering the organiser's request):
   - The repository was used only in the planning phase, read-only: formulas of 11 templates were compared with train gold at pinned commit `146eaa8225bf867fe7386c2d4727b59e03170235`. The tree was extracted with `git archive`; the local clone's HEAD was `9bd2942`, which only adds a licence file and edits the readme.
   - **No FinChain code was executed.** No FinChain-generated data, template matching or template execution was used, and **FinChain contributes nothing to any prediction.**
   - The organiser later permitted template matching and execution; the team's stricter rule kept them out.
   - The comparison found FinChain's conventions reproduce 20/30 finals and 28/60 slots where it shares a formula (PLAN.md §2.8) [O].
5. **Data:** the official FinReason Cup Task 1 release, CC BY 4.0, **used unchanged** (hash-checked). The toolkit was used unmodified.
6. **Models:** Claude models only, through Claude Code headless on a subscription. The organiser baselines were not used. No human labelled or annotated any test question.
7. **Disclosed post-hoc choices:**
   - The hint-only candidate was chosen after the conventions_v1 result, so its tuning evidence is biased; the decisive evidence is the lockbox look.
   - R2's design followed a diagnostic whose Opus outputs on 4 tuning cases were seen before R2's pre-registration.
   - R4's two fixes target failure modes seen in tuning (and, for the tax case, in lockbox look 1). Its decisive evidence was therefore a single pre-registered development-leaderboard upload, the one dataset never analysed. That uses the leaderboard for one selection decision, which the team rules allow.
   - All are logged as disclosures in `experiments/preregistration.jsonl`.
8. **Incidents, all logged:**
   - A background run survived a session restart, so two copies of R1's tuning check ran at once. Both were killed with no outputs inspected, and a run lock was added.
   - A full disk interrupted one tuning run (SQLite I/O error). The cache integrity check passed, and the run resumed from the cache.
   - Neither affected any submitted file.

## 9. Limitations (for the paper's discussion)
- **Hidden-template performance is unmeasured.** It is half of the combined score and decides the first tie-break. All labelled data is seen-template and at ceiling, so changes aimed at hidden questions were adopted on prior evidence plus non-inferiority.
- **R3's gain is small and slot-level** (third ranking key), and only directionally confirmed (lockbox CI includes 0). It affects only questions with a `dimensionless` field: on test, exactly 18 novel-route questions were re-solved (90 fresh calls) and every other answer equals R1's [O].
- **R4's echo rule is narrow:** in practice it fixes one template family. R4 changes only 32 seen-route test questions; every other R4 test answer is byte-identical to R3's [O]. The leaderboard gain shows it on seen templates. Its effect on hidden templates is nil by construction, because the rule never fires there.
- The headless CLI exposes no sampling controls. Reproducibility therefore rests on the response cache.
- Remaining convention errors (sign conventions, annual vs cumulative, taxable amount vs tax) are not fixed. Generic fixes either did not exist or did not survive testing.

## 10. Reproducing the submitted files
- **Environment:** Windows 11 host; WSL2 Ubuntu for the sandbox; Claude Code CLI 2.1.296; Python 3.12 (host), 3.14.4 (sandbox).
- **Replay** (no model calls when the cache is present): `python -m carnot.run --config configs/r3.json --split test928` regenerates R3's predictions. The same holds for `r0`, `r1` and `r4` (R4 test run `20261012T165330Z_r4_test928_S`).
- **Verify** the ZIP and predictions SHA-256 against `submissions/registry.jsonl`.
- **Replay checks, run 12 October 2026** [O] (`paper/REPLAY_CHECK.md`): R3's and **R4's** test runs regenerated from the cache with **0 model calls**, and both ZIPs are **byte-identical** to the uploaded files (`ea491873…`, `cec784e2…`).
- **Tests:** `python -m unittest discover -s carnot/tests` (scorer contract, formatter round-trip, sandbox, comparison tool, routing, synthetic engine).

## 11. Artefact index

| What | Where |
|---|---|
| Full plan, decisions, findings, build-status table | `PLAN.md` (§0, §0.1, §2, §4a, §4b, §4c, §5) |
| Every run (config, scores, usage) | `experiments/log.jsonl`, `runs/<run_id>/{summary.json,cases.jsonl,predictions.jsonl}` |
| Paired comparisons | `experiments/comparisons.jsonl` |
| Pre-registrations, results, incidents | `experiments/preregistration.jsonl` |
| Lockbox access | `experiments/lockbox_access.jsonl` |
| Diagnostic (Opus vs Sonnet) | `experiments/diagnostics.jsonl`, `experiments/diagnostics/` |
| Submissions and receipts | `submissions/registry.jsonl` |
| Organiser correspondence | `experiments/organiser_correspondence/2026-10-12_reply.txt` |
| Synthetic-set work | `synth/` (plans, templates, cross-checks, probes, review packet) |
| Configs and prompts | `configs/`, `carnot/prompts/` |
| Facts and tables for the paper | `paper/facts.json`, `paper/TABLES.md` (regenerate with `paper/build_facts.py`) |
