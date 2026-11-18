# Continuation decision

**Retain the accepted R4 submission.** The continuation plan was executed through its preregistered stopping point.

- No candidate met the promotion gates.
- No confirmation, historical lockbox look, Test run or portal upload was performed.
- The R4 artifacts are unchanged:
  - ZIP SHA-256 `cec784e2…0cc3`;
  - predictions `e0ef54eb…3067`;
  - receipt `test-20261012T170418Z-811e06a0…`.

## What was done

| Package | Outcome |
|---|---|
| A: state and preregistration | All 209 historical hashes verify; the one exception is documented. Ledgers reconcile: 2 of 4 lockbox looks, 2 development uploads. Protocol, recipes, feasibility note and baseline manifest were frozen before any call. |
| B: versioned runner | `carnot/improvement_validation_v1.py`. Cache-only replay of all 96 pilot cases is identical (1,464 calls, 0 fresh) and reproduces every pilot score. Historical R4 tuning-eval replay is identical (2 × 2,900 calls). 123 tests pass. |
| C: tuning-eval regression | All eight recipes 580/580 finals in S and H. FAC gate inconclusive for every candidate (no difference anywhere). Checkpoint gate non-inferior, sparse discordance. No introduced regression. |
| D: new families | 48 development families authored and checked by three independent gates, with 4 documented pre-scoring adjudications and no gold changes. Confirmation was never authored: the stop rule fired first. |
| E: ablations | Wave 1: R4 95/96, every candidate 96/96. Wave 2 (one permitted design revision): every recipe 96/96 and 348/348. Stress panel: candidate gains only on the ambiguous bond wording. |
| F, G | Not run. The preregistered rule stops before nomination proceeds when the revised design stays at ceiling. |

## What improved, and how broadly

- **Development families.** Every candidate fixes R4's single development error (one family, units/scale). The 48-family FAC delta is +0.005208, paired interval [0, 0.015625]. That is one improved family, which falls short of the four net-improved families a positive claim would need.
- **Tuning-eval.** No final-answer change. Checkpoint gains are concentrated in two templates and are no larger than R4's own run-to-run variation.
- **The bond-schedule gain** from the original pilot does not generalize beyond its own wording.
  - When the schedule is stated explicitly (one-time or recurring), every recipe, R4 included, is correct.
  - On the original ambiguous wording and its paraphrase, R4 and P score 2/4 while V scores 4/4. V reaches the author's one-time reading by selecting a minority candidate with executed evidence.
  - Prompting against repeated changes did not harm the case where recurrence is correct.

## Regressions and costs

- **Regressions.** No candidate lost a final answer or a checkpoint field relative to the contemporary R4 on any panel. On tuning-eval, V made one harmful slot override on an ambiguously worded "annual multiplier" slot, relative to J.
- **Cost.** The five-role recipes (D, J, JB, X1, X1C, V) cost about 3.7 times R4 per case. P costs about 5% more than R4. These are usage proxies, not invoices.
- **Continuation usage.** Evaluation runs made 12,143 fresh calls (124.73 USD cost equivalent). Authoring and oracle checks made 477 calls (43.24 USD).

## Gate status

| Gate | Status |
|---|---|
| Engineering (rows, rendering, isolation, cache-only replay, seen-route delegation) | Pass |
| FAC regression, tuning-eval S/H | Inconclusive for every candidate. The frozen policy cannot certify zero differences on 290 templates; the zero-event bound is 0.0103, above the 0.001 margin. |
| Checkpoint non-inferiority, tuning-eval S/H | Pass, with the sparse-discordance flag |
| Wider tuning-noex regression | Not run (stopped earlier) |
| Fresh confirmation | Not run. The revised design stayed at ceiling, so there is nothing a confirmation could detect. |
| Historical lockbox, Test, upload | Not authorized and not performed |

## Why the study stops here

Families written to the plan's quality standard state every convention explicitly. On those, R4 is already at ceiling: 1 final error in 192 development instances, and none after the design revision. The candidates' measurable advantage appears only where wording is underspecified. In those cases the "correct" answer is the author's reading, and the plan forbids building panels from ambiguous gold.

A confirmation panel of this kind would therefore almost certainly be inconclusive. The feasibility note shows that a positive claim needs at least four net-improved families of 48, while the observed rate is about 1 in 48.

This is a limitation of this bounded study. It does not show that improvement is impossible.

## Limiting assumptions to put to the user

1. **The FAC regression gate.** The frozen 0.001 margin cannot be satisfied when R4 is already perfect on tuning-eval. Promoting any novel-route change would require an explicit decision on the risk policy.
2. **Where the gains are.** Any measurable gain from the candidates lies in resolving underspecified wording toward an author's reading. Whether that resembles the private Test's hidden templates is unknown. Testing it would need an independently adjudicated, ambiguity-aware panel, and that would be a new plan, not a continuation of this one.

## Next action

Nothing more is required to keep R4. If you want to pursue either point above, that is a new, separately authorized cycle with its own confirmation families.

The evidence index is in `final_manifest.json`.
