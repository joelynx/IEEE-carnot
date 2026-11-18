# S2 safeguard result: P on tuning-eval (forced novel route, S and H)

Sources:

- the frozen rule in `preregistration.json` (plan `docs/task1-safeguard-v2-plan.md`, option A, chosen by the user on 22 October 2026);
- `run_matrix.json`;
- `replay_proof.json`;
- `report.json`;
- the run directories `tuning_eval_S` and `tuning_eval_H`.

## Integrity

- **Runner v2 replay check.** Runner v2 reproduced the continuation's tuning-eval S records exactly in cache-only mode: 580 cases and 5,800 cached calls, with no fresh calls.
- **Fresh identities.** The identities R4a 700–704, R4b 710–714 and P 720–724 had never been used before. All three arms ran interleaved per case in a single run for each mode.
- **Usage.**
  - S: 8,700 fresh calls, 28.02 USD cost equivalent.
  - H: 90 fresh calls, 0.33 USD cost equivalent; it shares every other request with S.
  - No retries, no failures and no usage-limit stops occurred.

## Gates (identical in S and H)

| Gate | Result |
|---|---|
| G1: no final-answer loss vs R4a | **Pass.** 0 losses and 0 gains; all three arms 580/580 |
| G2: 95% upper bound on the template loss rate ≤ 1.1% | **Pass.** 0 of 290 templates, bound 1.0277% |
| G3: R4 self-consistency (R4a vs R4b discordance ≤ 2) | **Valid.** 0 final and 0 slot discordances |
| G4: checkpoint net change ≥ −max(2, R4 slot noise) | **Pass.** Net 0 against a tolerance of 2 |
| G5: tuning-noex repeat | **Pass** (see Gate 5 below) |

**S2 verdict: pass on all five gates.**

## Disclosed detail

R4a, R4b and P each scored 1033/1036 slots, but not on the same cases.

- **Both R4 samples** missed checkpoints on `…2xpua6`, `…3uwjbe` and `…t5okie`.
- **P** fixed `…t5okie`, the annual-versus-cumulative multiplier slot, and missed `…igrn52` instead, a case both R4 samples got right.
- **Net result.** The net checkpoint change is therefore zero, but it contains one checkpoint loss. That loss is within the frozen G4 tolerance.

## What this does and does not mean

- **What a pass means.** Fresh sampling shows no observed final-answer harm from P on tuning-eval. With 95% confidence, fewer than about 1 in 97 tuning-like templates would newly lose a final answer.
- **What it does not show.** It is not evidence that P improves anything: P and R4 tied on every final answer. It says nothing about hidden templates or the private Test.
- **What promotion still needs.**
  - evidence of benefit on fresh, sealed material under a separate preregistered test.
  
  The continuation showed that explicitly worded synthetic families cannot currently supply that evidence, because R4 is at ceiling on them.
- **R4 remains the accepted submission.**

## Gate 5: tuning-noex (forced novel route, S and H)

Sources: `gate5_addendum.json`, frozen before any Gate 5 call; `gate5_report.json`; the run directories `tuning_noex_S` and `tuning_noex_H`. The user approved this step on 22 October 2026.

- **Execution.**
  - Claude Code stopped the background run twice because the machine was low on memory: once at 377 saved S cases and once at 679. Completed cases were kept, and no identity changed.
  - The remaining cases finished in runs outside Claude Code, launched with the identical frozen commands. They completed on 23 October 2026. The run identity checks accepted every saved case.
  - S made 25,945 fresh calls (83.46 USD cost equivalent). H made 225 (0.84 USD). There were no retries and no failures.
- **Results.** The results are identical in S and H.
  - R4a, R4b and P each scored 2,314/2,314 final answers.
  - On the full panel and on the 1,734 cases outside tuning-eval, P lost no final answer, and R4a and R4b never disagreed.
  - The 95% upper bound on the template loss rate is 1.0277% (0 of 290 templates). This adds instances but no new independent templates.
- **Checkpoints.** P scored 4,122/4,129 slots; R4a and R4b each scored 4,120/4,129. P gained a checkpoint on `…zdikaq`, `…t5okie` and `…5jdana`, and lost one on `…igrn52`. That is the same loss already seen on tuning-eval, and it is within the tolerance.

**Gate 5: pass.** S2 is satisfied on all five gates: P shows no observed harm to final answers on all 2,314 tuning-noex cases. That is the no-harm half only. P tied R4 on every final answer, so nothing here shows improvement. Promotion still needs a separately designed and preregistered benefit test. Until then R4 remains the accepted submission.
