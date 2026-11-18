# R5 execution protocol

Execution authorized by the user after reviewing `docs/task1-improvement-agent-plan.md`.
This amendment preserves R4, its accepted submission and all prior experimental records.

Sequence: historical tuning audit; current-backend training smoke; independently checked
synthetic pilot; isolated R5-P comparison; generation/selection ablations only if the
diagnostics justify them. No Test-output selection or direct FinChain matching.

R5-P changes only the novel-route system prompt. Its exact definition is in
`configs/r5p.json` and `carnot/prompts/pot_system_v2.txt`. The existing R4 seen route
remains unchanged. Hashes are frozen in preregistration before model comparisons.

Primary regression panel: 580 tuning-eval questions, forced novel route, S and H modes.
Secondary regression panel: tuning-noex, used only if the initial candidate survives.
Synthetic pilot: 24 new families across 12 domains, intermediate/advanced balanced;
four instances per family. Pilot findings are development evidence, not confirmation.
Do not expand the proposed 96-family panel if pilot gold quality or difficulty is
insufficient to distinguish candidates.

Promotion requires the plan's confirmation and regression gates. Margin for prospective
FAC non-inferiority: 0.001. Report the one-sided 95% lower bound, and require it to
exceed -0.001. A degenerate no-change bootstrap does not certify unknown-regression
risk; label such evidence inconclusive absent a valid conservative bound. Positive
proxy improvement requires a paired family-clustered 95% interval strictly above zero.
The historical heuristic remains labelled as historical, with its original behavior.

Limit new initial comparison work to R4 and R5-P. Five samples per question on the
novel route; existing retries capped at two. Fixed sample identities and response
cache permit resumption. Stop on exhausted subscription allowance, backend/model
identity mismatch, invalid oracle, failed isolation or unsuccessful confirmation.
Record the event and preserve partial work.

Reserve historical lockbox looks and portal submissions for a selected candidate.
Do not inspect Test predictions beyond existing artifact hashes. All generated
code executes through the existing WSL isolation.
