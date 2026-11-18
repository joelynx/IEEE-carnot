# Continuation protocol

This protocol carries out `PLAN.md` (SHA-256 `47913a36…`), which the user instructed on 21 October 2026. The machine-readable freeze is `preregistration.json`; exact recipes are in `candidate_recipes.json`. Where this text and those files differ, the JSON governs.

R4 remains the accepted submission throughout. The instruction authorizes only local experiments (Packages A–G). Historical lockbox looks, Test runs, portal uploads and organizer messages each need separate authorization after the evidence is presented.

## What is being tested

| Recipe | What changes from R4 on the novel route | Extra calls |
|---|---|---|
| P | Revised semantic system prompt (`pot_system_v2`) | 0 |
| D | Five roles: three Sonnet, two Opus (the R5-D pool) and field plurality | 0 |
| J | The same pool, complete-row selection | 0 |
| JB | The same pool, model-balanced complete-row vote (Sonnet roles 1/6 each, Opus roles 1/4 each) | 0 |
| X1 | One extra independent Opus sample on disagreements, original voting | ≤ 1 |
| X1C | The same sixth sample, complete-row selection | ≤ 1 (shared) |
| V | Frozen select-only verifier on disagreements, evidence-checked, J fallback | ≤ 1 |

D, J, JB, X1, X1C and V all derive from one saved five-role pool per case. X1, X1C and V use one trigger: at least two distinct complete executed rows. Gold never enters any trigger or selector.

## Sequence and gates

1. **A, state.** Historical seals, accepted-R4 hashes and ledgers verify (`STATE.md`). Dependency identities are frozen in `baseline_manifest.json` before any continuation code exists.
2. **B, runner.** `carnot/improvement_validation_v1.py` composes the existing solver, client, selectors and verifier without editing them. Exit: replay all 96 pilot cases cache-only with identical request keys, candidate outputs, votes, rows and verifier verdicts. Also required: focused tests for isolation, cache-only behavior, resume, and selector edge cases.
3. **C, tuning regression.** First, a cache-only historical R4 replay. Then one interleaved contemporary run per mode on tuning-eval, forced novel: R4c (fresh identities 500–504), P, the D5 pool and the triggered X1/V calls. Official scores, paired template-clustered intervals, gates, every introduced regression, error classes and usage.
4. **D, families.** Write 96 matched-pair briefs (`data/family_design.json`) and hash them in an addendum before authoring. Author and check wave 1 (24 development families). Apply the oracle quality rule, candidate-blind.
5. **E, ablation.** All recipes on wave 1 and the stress panel, then the wave-1 assessment (ceiling and concentration rule; at most one design revision). Then wave 2. Confirmation is authored, checked and sealed after the development families and remains unscored.
6. **F, nomination.** The frozen selection rule on all 48 development families, restricted to recipes eligible by tuning-eval. Then the wider tuning-noex S/H regression for the nominee only. Stop before confirmation on any net FAC loss.
7. **G, confirmation.** Freeze the nominee and the confirmation run matrix. Run R4 and the nominee once on all 192 confirmation instances, then score once.
8. **Report.** `DECISION.md` and `final_manifest.json`: each gate's status, and whether R4 remains accepted. Package H waits for the user.

## Integrity rules

- Recipes run only on the novel route; the seen route is delegated unchanged. Forced-novel tuning runs are stress tests.
- No Test-output comparison, Test-derived threshold, case-ID exception, manual prediction edit or Test-text adaptation. No FinChain template matching or template-program execution.
- Exemplars come only from the tuning exemplar pool (the R4 file). New families never become exemplars.
- Generation reads question files only. Every recipe's predictions are persisted and hashed before scoring loads gold.
- One model-calling process at a time holds `runs/.run.lock`. Concurrency is 3. Interrupted runs resume only when data, code and recipe identities match.
- Usage exhaustion, a model-identity mismatch, a CLI change, a corrupt cache, a provenance mismatch or a sandbox failure stops the phase. Partial work is kept.
- The prior campaign directory and its sealed modules are never edited. Every post-freeze change is recorded in `amendments.jsonl`.

## Known limits, stated before any result

- The FAC regression gate on tuning-eval passes only with zero final-answer losses and at least one gain against contemporary R4 (`statistical_feasibility.md`). An R4 at ceiling makes every candidate inconclusive. Inconclusive means R4 is retained.
- A positive confirmation claim needs at least four net-improved families of 48 with no regression. At the pilot's baseline error rate, that is unlikely unless the new families are more discriminating.
- The author, second implementation and blind solver all use one model family (Fable). Their agreement is supporting evidence, not independent human review.
