# Package C commands (recorded before execution)

Panel: `regression/panels/tuning-eval.json`, which is the 580 frozen tuning-eval cases (`python -m carnot.improvement_validation_v1 panel --kind tuning --split tuning-eval --out ...`).

## Historical reproducibility baseline (cache-only, completed)

```powershell
python -m carnot.improvement_validation_v1 generate --panel experiments/improvement_continuation_20261021/regression/panels/tuning-eval.json --mode S --run-dir experiments/improvement_continuation_20261021/regression/historical_r4_tuning_eval_S --arms r4 --r4-offset 0 --cache-only --concurrency 3
python -m carnot.continuation_replay_v1 check-historical --run-dir experiments/improvement_continuation_20261021/regression/historical_r4_tuning_eval_S --mode S
python -m carnot.improvement_validation_v1 score --run-dir experiments/improvement_continuation_20261021/regression/historical_r4_tuning_eval_S
```

The H commands are the same with `--mode H` and `_H` directories.

## Contemporary interleaved comparison

Every case job runs R4c (identities 500–504), P, the D5 pool, and the triggered X1 and V calls, three cases at a time, in the frozen shuffled order. S runs first; then H reuses identical requests from the cache.

```powershell
# backend smoke: first three cases of the frozen order; the full run resumes from them
python -m carnot.improvement_validation_v1 generate --panel experiments/improvement_continuation_20261021/regression/panels/tuning-eval.json --mode S --run-dir experiments/improvement_continuation_20261021/regression/tuning_eval_S --arms r4,p,d5,x1,v --r4-offset 500 --concurrency 3 --limit 3
python -m carnot.improvement_validation_v1 generate --panel experiments/improvement_continuation_20261021/regression/panels/tuning-eval.json --mode S --run-dir experiments/improvement_continuation_20261021/regression/tuning_eval_S --arms r4,p,d5,x1,v --r4-offset 500 --concurrency 3
python -m carnot.improvement_validation_v1 generate --panel experiments/improvement_continuation_20261021/regression/panels/tuning-eval.json --mode H --run-dir experiments/improvement_continuation_20261021/regression/tuning_eval_H --arms r4,p,d5,x1,v --r4-offset 500 --concurrency 3
python -m carnot.improvement_validation_v1 score --run-dir experiments/improvement_continuation_20261021/regression/tuning_eval_S
python -m carnot.improvement_validation_v1 score --run-dir experiments/improvement_continuation_20261021/regression/tuning_eval_H
python -m carnot.continuation_analysis_v1 regression --run S=experiments/improvement_continuation_20261021/regression/tuning_eval_S --run H=experiments/improvement_continuation_20261021/regression/tuning_eval_H --historical S=experiments/improvement_continuation_20261021/regression/historical_r4_tuning_eval_S --historical H=experiments/improvement_continuation_20261021/regression/historical_r4_tuning_eval_H --out experiments/improvement_continuation_20261021/regression/report.json
```

Interrupted runs are resumed by re-running the same command; saved cases are verified against the run identity and skipped. Projected fresh calls: about 8,200 for S and about 100 for H, before retries. The preregistered cap is 10,000.
