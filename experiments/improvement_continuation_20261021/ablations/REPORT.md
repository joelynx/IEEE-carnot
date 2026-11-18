# Package E: development families and stress panel

Sources:

- `wave1_report.json` and `wave2_report.json` (`python -m carnot.continuation_analysis_v1 families`);
- `../selection_decision.json`;
- the runs under `results/` and the commands in `COMMANDS.md`.

Everything here is development evidence. Wave 1 is assessed in detail in `WAVE1_ASSESSMENT.md`.

## Panels

| Panel | Families | Cases | Generator |
|---|---:|---:|---|
| Wave 1 | 24 | 96 | `synth_author_v5` |
| Wave 2 | 24 | 96 | `synth_author_v6` (design_revision_v1: brief composed with a secondary mechanism, at least six dependent operations) |
| Stress | 22 variants (4 bond, 18 from 6 wave-1 families) | 88 | hand-written bond variants; Fable paraphrase, minimal-pair and distractor variants |

Every family passed the oracle gates before scoring. Pre-scoring adjudications for three families and three stress variants are recorded in `data/quality_decisions.jsonl` and amendments A4–A7:

- `c1_04` and its three variants: accepted after a blind-solver arithmetic error;
- `c1_57`: signed-versus-magnitude wording clarified;
- `c1_66`: share-count scale clarified.

No gold value changed. No family was replaced, and no family was dropped.

## Results (correct finals; slots)

| Recipe | Wave 1 | Wave 2 | 48-family macro FAC | 48-family macro checkpoint | Stress |
|---|---|---|---:|---:|---|
| R4 | 95/96; 299/300 | 96/96; 348/348 | 0.994792 | 0.998264 | 83/88; 275/280 |
| P | 96/96; 300/300 | 96/96; 348/348 | 1.000000 | 1.000000 | 84/88; 275/280 |
| D, J, JB, X1, X1C | 96/96; 300/300 | 96/96; 348/348 | 1.000000 | 1.000000 | 85/88; 277/280 |
| V | 96/96; 300/300 | 96/96; 348/348 | 1.000000 | 1.000000 | 88/88; 280/280 |

**Development comparison.** Each candidate's advantage over R4 rests on one family (`c1_13`, a units/scale slip by R4): FAC +0.005208, paired family interval [0, 0.015625], 1 improved family and 0 regressed. The five-role pool disagreed on a final answer in no wave-1 family and in one wave-2 family (`c1_07`). The verifier made 0 calls in wave 1 and 2 in wave 2, changing nothing. Every pool contained a correct complete row for every development case.

**Stress panel.** All candidate errors are on the bond family's ambiguous wording: the original wording with new seeds, and its paraphrase. With explicit one-time or recurring schedules, every recipe is correct. The revised prompt did not harm the recurring case. There were no candidate errors on any paraphrase, minimal pair or distractor of the six wave-1 families. V's 88/88 comes from selecting the one-time reading on the ambiguous bond wording: 7 calls, 3 helpful overrides, 0 harmful.

**Resources.** The five-role recipes cost about 3.7 times R4 per case: development end-to-end cost equivalents were R4 0.0343, P 0.0360, D/J/JB 0.1266, X1/X1C 0.1268 and V 0.1271 USD per case. These are usage proxies, not invoices.

## Preregistered rules

- **Wave 1:** ceiling and concentration both held, which triggered the single permitted design revision (A6).
- **Wave 2, revised design:** the ceiling still holds, with 0 of 24 families having any R4 final error. Under the frozen rule, the limitation is delivered, confirmation stays unscored, and R4 is retained. Confirmation families were never authored, so no confirmation data exists to protect.
- **Selection rule:** applied for the record, it would nominate P. All seven candidates tie at macro FAC and checkpoint 1.0, and P has the lowest cost. The stop rule precedes Packages F and G, so P was not taken to the wider regression or to confirmation.
