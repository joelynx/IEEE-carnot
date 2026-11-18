# Initial pilot: coupon schedule interpretation

This is development error analysis, written after the R4/R5-P pilot. It is not
confirmation evidence. No question, gold value or candidate recipe in the frozen
initial comparison was changed after observing these results.

The amortizing-bond question specifies a year-one coupon rate and says that
"from year 2 onward the rate changes by" a stated number of basis points.
The reference and blind checker interpret this as one persistent change:
`r2 = r1 + change; r3 = r2`. Several Sonnet programs instead implemented
`r3 = r2 + change`, repeating the change despite no explicit annual-repeat
instruction. Their later cash flows and the year-three value at year two changed.

This is sensitivity to the description of the rate schedule, not evidence of
an inability to calculate discounted cash flows. The distinction between the two
interpretations is central to this family's result; agreement between the author
and blind checker is not independent human adjudication of the wording.

| Case suffix | R4 correct final samples | R5-P correct final samples | R4 selected final | R5-P selected final |
|---|---:|---:|---|---|
| `0b529d0937fb315a5b49` | 1/5 | 3/5 | wrong | correct |
| `30f0228fd1157020e7f3` | 5/5 | 5/5 | correct | correct |
| `d3f1679bf5d5f2426a93` | 0/5 | 0/5 | wrong | wrong |
| `bca3bbaeb9cd75eb431c` | 1/5 | 0/5 | wrong | wrong |

The full case IDs prepend `t1_syn`. Sources: `pilot/family_09/instances.jsonl`,
`template.json`, `blind_check.json`, `evaluation_r4.json` and `evaluation_r5p.json`.

R4's two final selection losses occur here. R5-P improves one selected answer but
has fewer cases with any correct final candidate (94 versus R4's 95 across the
96-question pilot). Selecting a complete row from either original pool changes
no selected scores. A selector cannot recover an answer absent from the pool.

All other 23 families have perfect selected answers and checkpoints under both
initial recipes. The observed gain therefore represents one reasoning family,
not 96 independent pieces of evidence. Its paired family-bootstrap 95% interval
includes zero. The subsequent diversity experiment is development-informed and
must not be presented as fresh confirmation of this finding.
