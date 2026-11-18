# Improvement campaign decision

**Retain the accepted R4 submission.** The bounded implementation and pilot are
complete. R5-V is the strongest experimental result on this pilot, but it has not
met the confirmation and regression requirements for promotion. No new Test run
or upload was made.

## Measured development results

The panel contains 96 synthetic questions from 24 families across 12 domains.
These are synthetic development results, not official development or hidden-Test
scores. Four parameter instances from one family are not four independent families.

| Recipe | Correct finals | Correct checkpoint fields | Family-macro FAC | Family-macro checkpoints |
|---|---:|---:|---:|---:|
| R4 | 93/96 | 320/324 | 0.968750 | 0.989583 |
| R5-P: revised novel-route prompt | 94/96 | 321/324 | 0.979167 | 0.992188 |
| R5-D: three Sonnet and two Opus roles | 95/96 | 323/324 | 0.989583 | 0.997396 |
| R5-J: complete-row selection of R5-D | 95/96 | 323/324 | 0.989583 | 0.997396 |
| R5-V: select-only verifier after R5-J | 96/96 | 324/324 | 1.000000 | 1.000000 |
| One extra Opus sample on each disagreement | 95/96 | 323/324 | 0.989583 | 0.997396 |

All selected-score gains occur in the amortizing-bond family. The other 23
families have perfect selected answers and checkpoints even under R4. The error
concerns a coupon-rate change from year two onward: some programs repeat the
change in year three. See `BOND_DIAGNOSTIC.md` for the wording and saved evidence.

The revised prompt fixes one selected answer. Diversity supplies a fully correct
candidate on every pilot question, but one correct minority answer is still
outvoted. Complete-row selection does not fix that loss. The verifier makes seven
calls across all disagreements, corrects that remaining final and checkpoint,
and makes no observed correct-to-wrong flips. Every accepted selection has an
executed supporting program matching all outputs of an existing candidate.
This arithmetic agreement is not proof that the interpretation is correct.

The seven-call sampling control adds one independently generated Opus sample to
the same saved pools and retains the original voting rule. It changes no scores;
the remaining wrong answer becomes a 3–3 final tie. The control uses 6,078 output
tokens and 1,951 reported thinking tokens, versus the verifier's 8,197 and 3,170.
Its list-price equivalent is $0.148501 versus $0.332342 for verification. These
are subscription cost equivalents, not invoices. Different token mixes, cache
usage and tie behavior prevent a general efficiency claim.

## Why no promotion or broad expansion

Relative to R4, R5-V's family-macro FAC delta is +0.03125, with paired family-
bootstrap 95% interval **[0, 0.09375]**. The checkpoint delta is +0.010417, with
interval **[0, 0.03125]**. Both intervals include zero. The implementation's
development bootstrap non-inferiority check passes under its specified estimator;
that does not satisfy the separate positive-improvement and fresh-confirmation
requirements, or establish safety on the private distribution.

The follow-ups are explicitly development-informed: the initial bond failures
motivated the role wording, diversity, verifier and sampling control. None is
fresh confirmation. The synthetic author and blind checker also share a model
family, and the checker uses the revised semantic prompt. Their agreement is
supportive validation, not independent human adjudication.

The pilot shows a useful local failure mode but inadequate breadth for selecting
a hidden-route replacement: 23/24 families are at ceiling and all apparent gains
depend on one description of a rate schedule. Applying the plan's diagnostic-
value stop gate, this campaign does not scale the same generator into the proposed
96-family panel. More parameter instances would not create independent evidence.
The alternative route is retained as experimental code and saved candidates.

The forced-novel tuning regression runs, fresh confirmation panel, remaining
historical lockbox looks, retrieval ablation and Test preparation are deferred.
They were not consumed to promote a candidate from this concentrated pilot.
A promotion decision still requires a sufficiently discriminating, independently
checked family panel and the original regression/confirmation gates. The risk
margin and confirmation policy have not been relaxed.

## Engineering and reproducibility

- 91 regression tests passed (`python -m unittest discover -s carnot/tests`).
- R4 and R5-P replay: 48 cases, 240 cached calls, identical outputs and no fresh calls.
- Diversity replay: 24 cases, 122 cached calls including retries, identical candidate
  outputs and both selectors; no fresh calls.
- Verifier replay: all seven cached calls and their executed evidence reproduced
  identically, with no fresh calls.
- The verifier replay initially used Windows' default text encoding to read a UTF-8
  result file. Request keys already matched; Unicode response text did not. The
  replay reader was corrected to UTF-8 and all seven checks passed. Candidate
  recipes, cached responses and scores were unchanged.
- Prompt/config/data hashes were frozen before each corresponding comparison.
  Stale results fail resume checks. R4 defaults and the seen-route prompt remain
  unchanged; generated programs continue to use the existing isolated sandbox.

R4's accepted artifact remains `runs/20261012T165330Z_r4_test928_S/submission.zip`,
SHA-256 `cec784e29f40f277d86ee6a38701e22ca117f1102abd5541083cefc8c60e0cc3`.
No Test-output comparison, manual prediction edit, portal upload or historical
lockbox evaluation was performed in this campaign.

## Evidence index

- `EXECUTION.md`: procedure, oracle corrections and resume commands.
- `baseline_audit.json`, `preregistration.json`, `execution_seal.json`: baseline
  protection and the original frozen design.
- `pilot_report.json`, `pilot_breakdown.json`: initial paired results, uncertainty,
  domain/difficulty breakdowns, sample errors and usage.
- `diversity_preregistration.json`, `diversity_report.json`: role recipe and both selectors.
- `verifier_preregistration.json`, `verifier_report.json`: eligibility, evidence gates,
  corrections, regressions, selected positions and resource use.
- `sampling_control_preregistration.json`, `sampling_control_report.json`: independent
  sampling control, observed tie and resource comparison.
- `cache_replay.json`, `diversity_cache_replay.json`, `verifier_cache_replay.json`:
  replay scope, cache counts, artifact hashes and replay-code identities.
- `pilot/`, `diversity_pilot/`, `verifier_pilot/`, `sampling_control/`: all per-case
  evidence, including original oracle artifacts preserved before adjudication.
