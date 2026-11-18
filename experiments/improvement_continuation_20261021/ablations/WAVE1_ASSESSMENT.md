# Wave-1 assessment (development only)

Sources:

- `wave1_report.json`, from `python -m carnot.continuation_analysis_v1 families`;
- the runs `results/wave1` (24 families, 96 cases) and `results/stress1` (22 variants, 88 cases);
- `COMMANDS.md`.

These are development results. They are not confirmation or private-Test evidence.

## Execution

Both runs stopped once on the new account's session limit (`UsageLimitError`, HTTP 429). The partial cases were kept, and the runs resumed after the reset under identical identities. Both completed: 96/96 and 88/88.

The runner's `completed_now` counter also counted jobs skipped after the stop flag was set. This is a reporting bug only; saved records and predictions are unaffected. The runner was not changed mid-run, because a change would alter its identity and block resumption.

## New wave-1 families

| Recipe | Correct finals | Slots | Family-macro FAC |
|---|---:|---:|---:|
| R4 | 95/96 | 299/300 | 0.989583 |
| P, D, J, JB, X1, X1C, V | 96/96 | 300/300 | 1.000000 |

- **The one R4 error.** It is in `c1_13` (two-stage quarterly dividend model), and its class is **units/scale**: three of five R4 samples misapplied the stated annual-to-quarterly growth conversion. Every pool contained the correct answer, so all eight recipes had full oracle coverage.
- **No disagreements in the D5 pool.** The D5 pool had no final-answer disagreement on any wave-1 case, so no verifier or extra-sample call was triggered.

### Preregistered rule

- **Ceiling holds.** R4 made a final error in 1 of 24 families; the threshold is fewer than 5.
- **Concentration holds.** The one informative family is in a single class (units/scale).

The preregistered action is one documented, development-only design revision for wave 2 and all confirmation families. Wave-1 results are preserved unchanged.

## Stress panel (descendants grouped with their source; not independent units)

| Group | R4 | P | D/J/JB/X1/X1C | V |
|---|---|---|---|---|
| Bond, original wording (new seeds) | 2/4 | 2/4 | 3/4 | 4/4 |
| Bond, neutral paraphrase of the original | 2/4 | 2/4 | 2/4 | 4/4 |
| Bond, explicit one-time change | 4/4 | 4/4 | 4/4 | 4/4 |
| Bond, explicit recurring change | 4/4 | 4/4 | 4/4 | 4/4 |
| Six wave-1 families × (paraphrase, minimal pair, distractor) | 71/72 (miss: `c1_13_dist`) | 72/72 | 72/72 | 72/72 |

- **Recurrence is not harmed.** Prompting against repeated changes did not hurt the variant where recurrence is correct: every recipe solved the explicit recurring schedule.
- **The bond gains come from ambiguous wording.** They appear only when the schedule is left open ("from year 2 onward the rate changes by …" and its paraphrase). There, "correct" means agreeing with the author's and checker's one-time reading. With explicit wording, there is nothing to fix.
- **What V's gain rests on.** On these two variants, V's advantage comes from selecting the minority one-time reading with executed evidence (7 verifier calls, 3 helpful overrides, 0 harmful). That is consistent with the earlier pilot, but it rests on one contested wording.
- **Paraphrases, minimal pairs and distractors** caused no candidate errors.

## Interpretation

Families written to the plan's quality standard state every convention explicitly. On those, R4 is already near ceiling, and the candidates' measurable advantage concentrates on underspecified wording. That is a limitation of the study design, not evidence that the candidates are harmful. It also means further explicit families may stay at ceiling. The revision therefore targets legitimate difficulty, meaning more interacting stated rules and longer state tracking, while staying within the rule that forbids ambiguous gold.
