# Arithmetic replay (18 November 2026)

The stored programs of two R0 runs are executed again, once in the frozen exact sandbox and once in IEEE binary64, without a model call. The paper reports the result in Section VI and Table V; the supplement has the full tables.

The two runs are not two samples. The run on tuning-noex took its responses for the 580 tuning-eval questions from the response cache, so it holds the 580 programs of the first run and 1,734 others: 2,314 distinct programs, executed 2,894 times per arm. The pre-registration said otherwise; amendment A1 in it records the correction.

| File | What it is |
|---|---|
| `preregistration.json` | The design, approved by the author before any stored program was executed, and sealed by hash before the first binary64 execution. Its `amendments` list holds one correction made after the run |
| `amend_preregistration.py` | Appended that amendment; the original wording was left in place |
| `run_arith_replay.py` | The runner. `--selftest` runs toy programs only; `--exact-only` runs the reproduction check; without options it runs everything and requires the sealed pre-registration |
| `seal_preregistration.py` | Writes the hashes of the runner and of the two twin modules into the pre-registration |
| `sandbox_binary64/` | The sandbox files of the binary64 arm. `worker.py` and `policy.py` are byte-identical copies of `carnot/sandbox/`; `finq.py` and `runner.py` are the binary64 twins |
| `run.log` | Console output of the full run |
| `results/exact_reproduction.json`, `results/overview_exact_only.json` | The gate: every program reproduces its stored fields and rows. The second file was written by the reproduction step before the sealing; the first was rewritten by the full run |
| `results/overview.json` | Scores, paired differences and field-level changes of every arm |
| `results/<split>/<arm>/` | `summary.json`, `cases.jsonl` and `predictions.jsonl` of one arm, in the layout that `carnot.compare` reads |
| `results/<split>/binary64_execution.jsonl` | The values each program returned in binary64 |
| `results/<split>/comparison_<arm>.json`, `field_transitions_<arm>.json` | Paired comparison with the stored run; fields kept, lost and gained by kind |
| `analyse_replay.py`, `results/posthoc_analysis.json` | A descriptive analysis written after the results were seen (why fields were lost). Not part of the pre-registration |

The replay needs the WSL sandbox described in `carnot/sandbox/executor.py` and the organisers' data and toolkit, as the rest of the repository does. It writes only under `results/`.
