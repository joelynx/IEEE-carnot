# R5 synthetic pilot report

Development evidence only. No confirmation or private Test accuracy.

Paired families: 24/24; missing: []; unresolved oracles: [].

| Config | Family-macro FAC | Family-macro checkpoints |
|---|---|---|
| r4 | 0.96875 | 0.9895833333333334 |
| r5p | 0.9791666666666666 | 0.9921875 |

```json
{
  "fac": {
    "delta": 0.010416666666666666,
    "ci95": [
      0.0,
      0.03125
    ],
    "one_sided_95_lower": 0.0,
    "families": 24,
    "replicates": 10000,
    "prospective": {
      "delta": 0.010416666666666666,
      "one_sided_95_lower": 0.0,
      "margin": 0.001,
      "status": "non_inferior",
      "zero_event_95_upper": null,
      "note": "Zero-event bound concerns independent family-level regression events; it is not evidence of correctness on the private Test distribution."
    }
  },
  "checkpoint": {
    "delta": 0.0026041666666666665,
    "ci95": [
      0.0,
      0.0078125
    ],
    "one_sided_95_lower": 0.0,
    "families": 24,
    "replicates": 10000,
    "prospective": {
      "delta": 0.0026041666666666665,
      "one_sided_95_lower": 0.0,
      "margin": 0.001,
      "status": "non_inferior",
      "zero_event_95_upper": null,
      "note": "Zero-event bound concerns independent family-level regression events; it is not evidence of correctness on the private Test distribution."
    }
  }
}
```

Full candidate-generation/selection diagnostics and per-family results are in pilot_report.json.
