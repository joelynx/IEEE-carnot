# Package C: tuning-eval forced-novel regression (S and H)

Source data: `report.json`, `error_review.json`, the run directories `tuning_eval_S`, `tuning_eval_H`, `historical_r4_tuning_eval_S` and `historical_r4_tuning_eval_H`, and the commands in `COMMANDS.md`. All 580 tuning-eval cases were run with a forced novel route. This is a familiar-family stress test, not hidden-template confirmation.

## Engineering

- **Historical reproducibility.** Cache-only R4 with identities 0–4 reproduced both historical runs exactly in S and H. That is 2,900 cached calls per mode, with identical exemplars, request keys, candidate outputs, votes and rows.
- **Contemporary comparison.** One interleaved run per mode covered R4c (fresh identities 500–504), P, the D5 pool, and the triggered X1 and V calls. S made 8,130 fresh calls: 2,900 R4c, 2,900 P, 2,320 D5 (role 0 reused P's sample 0 by identical key), 5 X1 and 5 V. H made 84 fresh calls.
- **S/H overlap.** 2,870 of 2,900 requests per generator are shared between S and H. Only the 6 cases whose template matches a primary exemplar differ, so S and H are not independent replications.
- **Failures.** No generation retries, no failures, no model substitution. Both modes completed under the original team login.
- **Toolkit check.** Official `seen_fac` and `seen_checkpoint` were recomputed from probed per-case weights. The recomputation matched the toolkit report for every recipe.

## Results (identical in S and H)

| Recipe | Finals | Slots | Official FAC | Official checkpoint | Δ checkpoint vs R4c | Template-cluster 95% interval |
|---|---:|---:|---:|---:|---:|---|
| R4c | 580/580 | 1032/1036 | 1 | 0.995952 | — | — |
| P | 580/580 | 1034/1036 | 1 | 0.997619 | +0.001667 | [0, 0.005] |
| D, J, JB, X1, X1C | 580/580 | 1033/1036 | 1 | 0.996786 | +0.000833 | [0, 0.0025] |
| V | 580/580 | 1034/1036 | 1 | 0.998333 | +0.002381 | [0, 0.007143] |
| Historical R4 (0–4) | 580/580 | 1034/1036 | 1 | 0.997619 | (+0.001667 vs R4c) | — |

### Gates against R4c (preregistered)

- **FAC gate: inconclusive for every candidate, in both modes.** No final answer differed anywhere. The frozen policy treats an all-zero difference as inconclusive because the zero-event bound over 290 templates is 0.010277, above the 0.001 margin. This is the limiting assumption stated in advance in `statistical_feasibility.md`. It is not a regression.
- **Checkpoint gate: non-inferior for every candidate in both modes.** The one-sided lower bound is 0 > −0.001, with no checkpoint losses. Each comparison has only one discordant template, so the sparse-discordance flag is set. The bootstrap bound is therefore not reliable evidence of a real gain.
- **No introduced tuning regression.** No candidate lost a final answer or a checkpoint field relative to R4c.

## Every error (all checkpoint-only)

1. **`interest_from_known_total`**, cases `coev…` and `ov6v…`; class **annual vs cumulative**. The slot is described as "Exact annual compound multiplier", but gold is the cumulative factor (1+r)^n. Samples split on this.
   - R4c missed both cases.
   - P got both right.
   - D, J, JB, X1 and X1C missed `coev`.
   - V missed both. On `ov6v`, V overrode a correct J row because it read the wording as the per-year factor. That is the only harmful override recorded. Its rationale is defensible on the wording, but it was wrong against gold.
2. **`portfolio_single_factor`**, cases `dze…` and `rwz…`; class **sign**. R4c and P were unanimous on folding the sensitivity's sign into the factor ratio. Only the D5 pool held the correct value, as a 2-of-5 minority. Field plurality (D, J, JB, X1, X1C) kept the wrong value. V selected the correct minority, with executed evidence, in both cases.

## Diagnostics

- **Pool coverage.** A complete correct row existed in 578/580 cases for the R4c pool, 578 for P and 580 for D5. Every pool contained a correct final answer for every case.
- **Verifier.** It made 5 calls per mode. All 5 were checkpoint-only disagreements in which J already had the correct final. Every selection was supported by executed evidence, with no abstentions. It overrode J three times: two helpful slot changes and one harmful one. Selected anonymous positions: 4 × index 1 and 1 × index 0.
- **Run-to-run noise.** Contemporary R4c scored two slots lower than historical R4 on identical prompts, both on the `interest_from_known_total` template. The size of that noise equals P's measured "gain". Checkpoint differences on this panel are therefore within sampling variation.
- **End-to-end cost equivalents in S.** These are usage proxies, not invoices: R4c 11.32 USD, P 11.94, the D5-based recipes 55.86, X1/X1C 55.88 and V 55.98. Fresh output tokens were R4c 362,174, P 418,804 and D5 557,729.

## Implication

Every candidate is eligible under the preregistered selection rule: FAC delta ≥ 0 and checkpoint delta ≥ −0.001 in both modes. None can pass the frozen FAC regression gate on this panel, because contemporary R4 is at ceiling here. Promotion would therefore still require the risk-policy decision described in `statistical_feasibility.md`. The development families (Package E) decide which candidate, if any, is nominated.
