# Package E commands (recorded before execution)

```powershell
python -m carnot.continuation_families_v1 panel --select partition=development,wave=1 --name wave1
python -m carnot.continuation_stress_v1 panel --name stress1
python -m carnot.improvement_validation_v1 generate --panel experiments/improvement_continuation_20261021/data/development/panels/wave1.json --mode H --run-dir experiments/improvement_continuation_20261021/ablations/results/wave1 --arms r4,p,d5,x1,v --r4-offset 0 --routing routed --concurrency 3
python -m carnot.improvement_validation_v1 generate --panel experiments/improvement_continuation_20261021/data/stress/panels/stress1.json --mode H --run-dir experiments/improvement_continuation_20261021/ablations/results/stress1 --arms r4,p,d5,x1,v --r4-offset 0 --routing routed --concurrency 3
python -m carnot.improvement_validation_v1 score --run-dir experiments/improvement_continuation_20261021/ablations/results/wave1
python -m carnot.improvement_validation_v1 score --run-dir experiments/improvement_continuation_20261021/ablations/results/stress1
python -m carnot.continuation_analysis_v1 families --run experiments/improvement_continuation_20261021/ablations/results/wave1 --run experiments/improvement_continuation_20261021/ablations/results/stress1 --seed carnot-continuation-v1-development --out experiments/improvement_continuation_20261021/ablations/wave1_report.json
```

Projected fresh calls: (96 + 88) cases x (5 R4 + 5 P + 4 D5) = 2,576, plus at most one X1 and one V call per triggered case. The Package E cap is 5,000.

## Wave 2 (design_revision_v1)

```powershell
python -m carnot.continuation_families_v1 panel --select partition=development,wave=2 --name wave2
python -m carnot.improvement_validation_v1 generate --panel experiments/improvement_continuation_20261021/data/development/panels/wave2.json --mode H --run-dir experiments/improvement_continuation_20261021/ablations/results/wave2 --arms r4,p,d5,x1,v --r4-offset 0 --routing routed --concurrency 3
python -m carnot.improvement_validation_v1 score --run-dir experiments/improvement_continuation_20261021/ablations/results/wave2
```
