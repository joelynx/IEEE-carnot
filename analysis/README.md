# Read-only analysis scripts (PLAN.md §2)

These scripts reproduce the observed statistics in PLAN.md. They only read data; none of them calls a model or writes outside the paths you pass. Run them with `python -I -X utf8`.

| Script | Produces | Usage |
|---|---|---|
| `data_stats.py` | split counts, spec distributions, gold formats, overlaps, slot vocabulary (§2.4) | `python -I -X utf8 analysis/data_stats.py development_files test_questions` |
| `conventions.py` | percent/ratio conventions, rational slots, test seen/hidden proxy (§2.4) | `python -I -X utf8 analysis/conventions.py development_files test_questions` |
| `score_any.py` | toolkit `score_submission` on any split (targets/baselines) | `python -I analysis/score_any.py . development_files/train_questions.jsonl development_files/train_gold.jsonl development_files/train_manifest.jsonl development_files/train_targets.jsonl` |
| `finchain_pairs.py` | sampled train template vs FinChain function, side by side (§2.8) | `python -I -X utf8 analysis/finchain_pairs.py <finchain_146eaa8>/data/templates development_files --show 0,1,2` |
| `finchain_repro.py` | FinChain-convention reproduction on 30 train cases (§2.8) | `python -I -X utf8 analysis/finchain_repro.py development_files` |
| `html2text.py` | visible text of a fetched web page (§2.1) | `python -I analysis/html2text.py page.html page.txt` |

`<finchain_146eaa8>` is the pinned FinChain tree, extracted without running any of its code:
`git -C finchain archive 146eaa8225bf867fe7386c2d4727b59e03170235 data/templates | tar -x -C <dir>`.
