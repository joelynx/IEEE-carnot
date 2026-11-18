# Statistical feasibility of the continuation gates

Written before any continuation model call. The numbers below were computed from
hypothetical difference patterns, using the estimators the continuation will apply
(`python -m carnot.continuation_feasibility_v1`, output in `statistical_feasibility.json`).
They describe what the frozen policy can and cannot certify. They are not results.

## Estimators

| Panel | Primary estimand | Independent units | Interval |
|---|---|---|---|
| New synthetic development and confirmation | Equal-family macro FAC (mean over families of the mean over four instances); checkpoint macro secondary | Families (48 per partition). The four instances of a family are descendants, not units | `carnot.prospective.paired_family_interval`: paired family bootstrap, 10,000 resamples, frozen seed |
| Tuning-eval and tuning-noex regression (forced novel, S and H) | Official hierarchical `seen_fac` and `seen_checkpoint` from the toolkit scorer | 290 templates. tuning-noex adds more instances of the **same** 290 templates and does not add template units | `carnot.compare.bootstrap` with official per-case weights, templates resampled within topics (primary); legacy cases within templates for S (reported separately) |

The FAC regression gate reads the one-sided 95% lower bound, which is the 5th percentile of the paired bootstrap. A candidate passes only when that bound is strictly above −0.001. The gate status comes from the frozen `carnot.prospective.decision`. If every cluster difference is zero, the gate is inconclusive unless the zero-event bound is below the margin. The continuation adds a checkpoint gate at the same numerical margin. That gate is a new safeguard, not part of the original FAC policy.

## Zero-event bounds

The conservative bound `1 - 0.05^(1/n)` concerns the probability that an independent unit contains any regression. It is not an interval for weighted FAC loss.

| Independent units n | 95% upper bound with zero events |
|---:|---:|
| 24 | 0.117346 |
| 48 | 0.060503 |
| 96 | 0.030724 |
| 290 | 0.010277 |

Pushing this bound below 0.001 takes 2,995 independent units. The continuation has 48 confirmation families and 290 tuning templates, so it cannot certify a 0.1-percentage-point rare-regression guarantee.

## Regression gate: what can pass

One tuning-eval case carries an official FAC weight between 0.001190 and 0.002778, which is above the margin. Each tuning-noex case weighs 0.000298 to 0.000694. Scenarios, with the losing or gaining case placed in distinct templates:

| Case losses | Case gains | tuning-eval lower bound | tuning-eval status | tuning-noex lower bound | tuning-noex status |
|---:|---:|---:|---|---:|---|
| 0 | 0 | 0 | inconclusive | 0 | inconclusive |
| 0 | 1 | 0 | non-inferior | 0 | non-inferior |
| 1 | 0 | −0.006250 | inconclusive | −0.001563 | inconclusive |
| 1 | 1 | −0.004167 | inconclusive | −0.001042 | inconclusive |
| 1 | 3 | −0.002083 | inconclusive | −0.000521 | non-inferior |
| 2 | 2 | −0.006250 | inconclusive | −0.001563 | inconclusive |
| 3 | 0 | −0.010417 | inconclusive | −0.002604 | inconclusive |

**Limiting assumption.** On tuning-eval, the frozen gate passes only if the candidate loses no final answer anywhere and gains at least one, relative to the contemporary R4 comparator. Historical R4 scored 580/580 final answers on this panel. If the contemporary R4 is also perfect, no candidate can show a gain, and every candidate is inconclusive regardless of quality. One unlucky sampled loss also makes the gate inconclusive. This follows from the 0.001 margin combined with per-case weights above it. It is not a property of any candidate.

**Sparse-discordance limitation.** When a gain or loss sits in only a few templates, the percentile bootstrap is coarse. Its lower bound often sits exactly at 0 or at a multiple of one case weight, and it is anti-conservative relative to unseen templates. Every regression view will therefore also report:

- the number of discordant templates;
- the zero-event or Clopper–Pearson 95% upper bound on the share of templates with a net FAC loss;
- a **sparse-discordance** flag when fewer than ten templates are discordant.

These are sensitivity analyses. They do not replace the frozen gate.

## Confirmation: what a positive claim needs

Scenarios on 48 families, with each changed family moving by one instance (±0.25) or two instances (±0.5):

| Improved families | Regressed families | ±0.25: 95% interval | Positive? | ±0.5: 95% interval | Positive? |
|---:|---:|---|---|---|---|
| 2 | 0 | [0, 0.026042] | no | [0, 0.052083] | no |
| 3 | 0 | [0, 0.036458] | no | [0, 0.072917] | no |
| 4 | 0 | [0.005208, 0.041667] | yes | [0.010417, 0.083333] | yes |
| 4 | 1 | [−0.005208, 0.041667] | no | [−0.010417, 0.083333] | no |
| 5 | 1 | [0, 0.046875] | no | [0, 0.09375] | no |
| 6 | 1 | [0, 0.052083] | no | [0, 0.104167] | no |
| 8 | 1 | [0.010417, 0.067708] | yes | [0.020833, 0.135417] | yes |
| 8 | 2 | [0, 0.0625] | no | [0, 0.125] | no |

A positive claim therefore needs at least four net-improved families with no regression, or about eight with one regression. The initial pilot had R4 errors in 1 of 24 families. At that rate, 48 confirmation families would contain about two families where R4 errs at all. That is too few for any candidate to meet the positive gate, even if it corrected every one.

## Consequences for the design

1. The first 24 new development families are the diagnostic checkpoint. The design counts as at **ceiling** if fewer than 5 of those 24 families contain an R4 final error, which is about the rate needed to expect four or more improvable confirmation families. It counts as **concentrated** if at least 75% of informative families share one mechanism class. Either outcome triggers the single permitted development-only design revision before the remaining families are generated. If the revised design is still at ceiling, the study reports that limitation, confirmation stays unscored, and R4 is retained.
2. Regression gates are likely to be **inconclusive** rather than failed. Inconclusive is not a pass. Under the frozen policy, it means R4 is retained. Changing the risk policy is a user decision, and the continuation will not make it.
3. No estimator, margin, seed or unit definition will be changed after outcomes are seen. More instances per family or template add no independent units.
