# R5 baseline audit

Historical tuning only; no fresh model calls or test-output analysis.

## 20261012T163028Z_r4_tuning-noex_S

Official scores: {"combined_fac": null, "seen_fac": "1", "hidden_fac": null, "combined_checkpoint": null, "seen_checkpoint": "0.9983035714285714", "hidden_checkpoint": null}

| Diagnostic | Count |
|---|---|
| cases | 2314 |
| wrong_final | 0 |
| slot_misses | 6 |
| samples | 2314 |
| incomplete_samples | 0 |
| oracle_final_cases | 2314 |
| oracle_all_fields_cases | 2308 |
| final_selection_losses | 0 |
| all_fields_selection_losses | 0 |
| unanimous_wrong_final | 0 |
| mixed_rows | 0 |
| whole_row_final_delta | 0 |
| whole_row_slot_delta | 0 |

Errors (tuning only):

```json
[
  {
    "case_id": "t1_472ozqqabomeezdxqdav6",
    "template": "fp.risk_management.stress_testing.portfolio_single_factor.basic.v1",
    "final_correct": 1,
    "missed_slots": 1,
    "oracle_all_fields": false
  },
  {
    "case_id": "t1_dze57qquqcc7cqr2xpua6",
    "template": "fp.risk_management.sensitivity_analysis.portfolio_single_factor.basic.v1",
    "final_correct": 1,
    "missed_slots": 1,
    "oracle_all_fields": false
  },
  {
    "case_id": "t1_f2lheggpykeirevhfczrc",
    "template": "fp.investment_analysis.ci.interest_from_known_total.intermediate.v1",
    "final_correct": 1,
    "missed_slots": 1,
    "oracle_all_fields": false
  },
  {
    "case_id": "t1_mnoow45exwjcadw45uyem",
    "template": "fp.risk_management.sensitivity_analysis.portfolio_single_factor.basic.v1",
    "final_correct": 1,
    "missed_slots": 1,
    "oracle_all_fields": false
  },
  {
    "case_id": "t1_nqiw7jr3ilup6jczvymzm",
    "template": "fp.risk_management.sensitivity_analysis.portfolio_single_factor.basic.v1",
    "final_correct": 1,
    "missed_slots": 1,
    "oracle_all_fields": false
  },
  {
    "case_id": "t1_rwz5ybiy42flbtv3uwjbe",
    "template": "fp.risk_management.sensitivity_analysis.portfolio_single_factor.basic.v1",
    "final_correct": 1,
    "missed_slots": 1,
    "oracle_all_fields": false
  }
]
```

## 20261012T163526Z_r4_tuning-eval_S_forced-novel

Official scores: {"combined_fac": null, "seen_fac": "1", "hidden_fac": null, "combined_checkpoint": null, "seen_checkpoint": "0.9976190476190476", "hidden_checkpoint": null}

| Diagnostic | Count |
|---|---|
| cases | 580 |
| wrong_final | 0 |
| slot_misses | 2 |
| samples | 2900 |
| incomplete_samples | 0 |
| oracle_final_cases | 580 |
| oracle_all_fields_cases | 578 |
| final_selection_losses | 0 |
| all_fields_selection_losses | 0 |
| unanimous_wrong_final | 0 |
| mixed_rows | 0 |
| whole_row_final_delta | 0 |
| whole_row_slot_delta | 0 |

Errors (tuning only):

```json
[
  {
    "case_id": "t1_dze57qquqcc7cqr2xpua6",
    "template": "fp.risk_management.sensitivity_analysis.portfolio_single_factor.basic.v1",
    "final_correct": 1,
    "missed_slots": 1,
    "oracle_all_fields": false
  },
  {
    "case_id": "t1_rwz5ybiy42flbtv3uwjbe",
    "template": "fp.risk_management.sensitivity_analysis.portfolio_single_factor.basic.v1",
    "final_correct": 1,
    "missed_slots": 1,
    "oracle_all_fields": false
  }
]
```

No Test correctness is known. Diagnostic oracle scores use public tuning gold only.
Protected hashes and cache snapshot identity are in baseline_audit.json.
