# R5 improvement campaign

The user authorized implementation and local experiments after the literature-backed
plan in `docs/task1-improvement-agent-plan.md`. R4 remains the accepted submission.

## Evidence and reproducibility

- `baseline_audit.json`: historical tuning-only generation/selection audit and
  protected R4 artifact hashes. No final-answer selection losses were found.
- `preregistration.json`: the original 24-family design, author/checker recipe,
  candidate recipes and prospective statistical policy, frozen before model calls.
- `preflight.json`: successful current-backend training smoke, exact model/CLI identity.
- `pilot/family_*/`: original author records, four deterministic pilot instances,
  blind solutions and parameter endpoint checks. Twelve parameter draws were
  validated during authoring for each family.
- `execution_seal.json`: validated data and implementation hashes frozen before
  the first R4/R5-P candidate evaluation. Resume checks reject stale artifacts.
- `pilot_report.json` and `.md`: generated after comparison; development evidence,
  never a private-Test or confirmation result.

The blind checker is a separate Fable call without the author's program or gold.
It shares the author's model family, so agreement is not independent human review.
The checker uses the revised v2 semantic prompt without exemplars. This is a label
validation procedure with shared modeling assumptions, not a neutral estimate of
either candidate's performance. All 24 planned families were retained; corrections
were made for explicit oracle defects before candidate evaluation.
Endpoint execution tests robustness and rendering, not semantic correctness.

## Oracle adjudication before evaluation

Twenty-two families initially agreed in all fields. Two required correction:

1. Family 03: the reference program canceled the underwriting fee when subtracting
   repurchase proceeds, contradicting the question's explicit post-repurchase equity
   definition. The corrected program applies that definition first and reconstructs
   pre-repurchase equity from the remaining equity and net proceeds.
2. Family 04: vesting percentages could refer to either initial or remaining maximum
   supply after a burn. The question now explicitly uses initial maximum supply;
   the reference program is unchanged.

The original artifacts are preserved under each family's `before_adjudication_v1/`.
`adjudication.json` records rationale and before/after hashes. Seeds, parameters and
case identities were preserved. Separate exact-arithmetic calculations verified all
12 generated instances per corrected family. All 24 families subsequently passed
the blind and endpoint gates. Five endpoint combinations were rejected by explicit
validity guards; none failed unexpectedly. Candidate outputs did not exist during
these corrections.

## Comparison and decision policy

The comparison uses the novel route, fixed H-mode examples and five samples for
each of 96 questions under each recipe. R5-P changes only the novel-route system
prompt. Family-level paired bootstrap intervals use 24 independent family units;
the 96 descendants are not treated as independent families.

Report both final-answer correctness and checkpoint correctness. A zero-difference
bootstrap does not certify generalization safety. Promotion needs the separately
specified confirmation and regression gates. Stop expansion if the pilot cannot
distinguish candidates. Diversity and verifier work depend on generation/selection
diagnostics, rather than being added automatically.

Usage records are subscription usage and list-price equivalents, not API invoices.
No historical lockbox look or portal submission has been spent in this campaign.
No Test predictions were inspected or used for candidate selection.

## Initial pilot result

The initial comparison is complete. R4 scored 93/96 final answers and 320/324
checkpoint fields; R5-P scored 94/96 and 321/324. Family-macro checkpoint scores
were 0.989583 and 0.992188 respectively. All selected-score differences occur in
the amortizing-bond family, where models sometimes applied the coupon change
again in year three rather than retaining the changed rate from year two onward.
The FAC difference is +0.010417, with family-clustered 95% interval [0, 0.03125].
It does not establish an improvement under the prospective confirmation gate.

R4 had two final selection losses; R5-P had none, but its candidate pool lacked
correct finals on two cases. Complete-row selection of either existing pool
changed no scores. These observations motivate the planned generation-diversity
ablation, rather than assuming a selector alone can solve the remaining errors.

`cache_replay.json` verifies identical selected rows, votes, candidate outputs and
request identities on the first case of every family under both recipes:
48 cases, 240 cached calls and zero fresh model calls.

## Bounded follow-up results

The full regression suite passed 91 tests on 21 October 2026. The accepted R4
artifact remains protected by hash checks. No candidate has been promoted.

`diversity_preregistration.json` freezes five independent roles: three Sonnet
medium samples and two Opus medium samples. The direct Sonnet role reuses R5-P's
sample-zero request. The other roles focus on output interpretation, alternative
derivation and quantity auditing. Role wording is development-informed, including
the one-time versus recurring-change distinction exposed by the initial pilot.
This is not fresh confirmation evidence. Opus passed a training-only preflight.

The diversity run is complete on the same 96 questions. R5-D uses existing
field plurality; R5-J selects a complete row supporting final-answer plurality,
with the existing row as its abstention fallback. Both use the identical saved
candidate pool. Both scored 95/96 final answers and 323/324 checkpoints. Their
candidate oracle is 96/96 on both final answers and complete rows; one correct
minority answer is still outvoted. All gains remain in the bond family, with
FAC difference +0.020833 and family-clustered 95% interval [0, 0.0625].

That remaining selection loss motivates R5-V, the planned bounded verifier.
It receives deduplicated anonymous candidate programs in deterministic shuffled
order, without vote counts or model identities. It may select an existing row
only if its independently requested supporting program executes and reproduces
every selected output; otherwise it falls back to R5-J. There is at most one
verifier call per disagreement, and every disagreement is evaluated, including
ones R5-J already gets right. It finished at 96/96 finals and 324/324 checkpoints,
with seven calls, one correction and no observed regressions. All seven calls
and their executed evidence passed cache-only replay.

The fixed one-extra-Opus-sample control on those same seven disagreements stayed
at 95/96 and 323/324. Its remaining error was a 3–3 tie under the unchanged voting
rule. Actual token use and cost equivalents differ from the verifier, so the
control does not establish cost-matched superiority. The complete results and
the decision to retain R4 and stop broad expansion are in `DECISION.md`.

The initial comparison and reports can be regenerated with:

```powershell
python -m carnot.improvement_campaign evaluate --concurrency 3
python -m carnot.improvement_report
python -m carnot.improvement_breakdown
```

To resume the bounded diversity comparison:

```powershell
python -m carnot.improvement_diversity evaluate --concurrency 3
python -m carnot.improvement_diversity report
```

Completed verifier and sampling-control reports can be regenerated with:

```powershell
python -m carnot.improvement_verifier report
python -m carnot.improvement_sampling_control report
```

The campaign holds the shared run lock, preserves partial results and reuses model
responses by cache key. Do not start a second campaign while the first is active.
Do not overwrite the preregistration or execution seal.
