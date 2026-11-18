# Experiment results

Generated from experiments/log.jsonl by carnot.run. Official = toolkit hierarchical score; micro = raw share.

| run | config | split | mode | n | complete | seen FAC | seen steps | micro FAC | micro steps | input tok | output tok | cost-equiv $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261011T184257Z_r0_tuning-eval_S | r0 | tuning-eval | S | 580 | True | 1 | 0.9956746031746032 | 1 | 0.9951737451737452 | 1160 | 71460 | 7.51 |
| 20261011T193429Z_r0_tuning-eval_H | r0 | tuning-eval | H | 580 | True | 1 | 0.9956746031746032 | 1 | 0.9951737451737452 | 2 | 188 | 0.01 |
| 20261011T190219Z_r0_tuning-eval_H | r0 | tuning-eval | H | 580 | True | 1 | 0.9956746031746032 | 1 | 0.9951737451737452 | 10 | 863 | 0.07 |
| 20261011T193529Z_r0_test928_S | r0 | test928 | S | 928 | True | – | – | – | – | 1870 | 172227 | 12.75 |
| 20261011T201016Z_r0_leaderboard580_S | r0 | leaderboard580 | S | 580 | True | – | – | – | – | 1160 | 71910 | 7.51 |
| 20261011T201038Z_r0_lockbox_S | r0 | lockbox | S | 870 | True | 0.9966666666666667 | 0.9965079365079365 | 0.996551724137931 | 0.9961389961389961 | 1740 | 106689 | 11.26 |
| smoke_sample_offset | r0 | tuning-eval | S | 3 | True | – | – | – | – | 6 | 334 | 0.04 |
| 20261011T203538Z_r0_tuning-eval_S_rep1 | r0 | tuning-eval | S | 580 | True | 0.9983333333333333 | 0.9965079365079365 | 0.9982758620689655 | 0.9961389961389961 | 1154 | 70719 | 7.47 |
| 20261011T204616Z_r0_tuning-eval_S_rep2 | r0 | tuning-eval | S | 580 | True | 1 | 0.9956746031746032 | 1 | 0.9951737451737452 | 1160 | 71409 | 1.81 |
| 20261012T044724Z_r1_leaderboard580_S | r1 | leaderboard580 | S | 580 | True | – | – | – | – | 0 | 0 | 0.00 |
| smoke_r1_forced_novel | r1 | tuning-eval | S | 5 | True | – | – | – | – | 50 | 2591 | 0.11 |
| 20261012T051314Z_r1_tuning-eval_S_forced-novel | r1 | tuning-eval | S | 580 | True | 1 | 0.9965079365079365 | 1 | 0.9961389961389961 | 4216 | 265031 | 8.16 |
| 20261012T055322Z_r1_tuning-eval_H_forced-novel | r1 | tuning-eval | H | 580 | True | 1 | 0.9965079365079365 | 1 | 0.9961389961389961 | 60 | 5349 | 0.13 |
| 20261012T055828Z_r1_test928_S | r1 | test928 | S | 928 | True | – | – | – | – | 3486 | 515632 | 9.98 |
| 20261012T065838Z_r2_leaderboard580_S | r2 | leaderboard580 | S | 580 | True | – | – | – | – | 0 | 0 | 0.00 |
| 20261012T065939Z_r2_tuning-eval_S_forced-novel | r2 | tuning-eval | S | 580 | True | 1 | 0.9955555555555556 | 1 | 0.9951737451737452 | 5760 | 381916 | 22.85 |
| 20261012T074942Z_r2_tuning-eval_H_forced-novel | r2 | tuning-eval | H | 580 | True | 1 | 0.9955555555555556 | 1 | 0.9951737451737452 | 60 | 5395 | 0.27 |
| 20261012T075604Z_r2_test928_S | r2 | test928 | S | 928 | True | – | – | – | – | 3480 | 492051 | 19.39 |
| 20261012T102730Z_e_base_tuning-noex_H | e_base | tuning-noex | H | 2314 | True | 0.99875 | 0.997281746031746 | 0.9987035436473639 | 0.9966093485105352 | 3468 | 219056 | 22.52 |
| 20261012T105448Z_e_conv_tuning-noex_H | e_conv | tuning-noex | H | 2314 | True | 0.9979166666666667 | 0.9967261904761905 | 0.9978392394122731 | 0.9973359166868491 | 1896 | 134106 | 14.24 |
| 20261012T124058Z_e_hint_tuning-noex_H | e_hint | tuning-noex | H | 2314 | False | – | – | – | – | 64 | 4146 | 0.42 |
| 20261012T125649Z_e_hint_tuning-noex_H | e_hint | tuning-noex | H | 2314 | True | 0.99875 | 0.9986011904761905 | 0.9987035436473639 | 0.9987890530394769 | 0 | 0 | 0.00 |
| 20261012T130052Z_e_base_lockbox_H | e_base | lockbox | H | 870 | True | 0.9955555555555556 | 0.9965079365079365 | 0.9954022988505747 | 0.9961389961389961 | 1740 | 111576 | 11.31 |
| 20261012T131457Z_e_hint_lockbox_H | e_hint | lockbox | H | 870 | True | 0.9955555555555556 | 0.9970634920634921 | 0.9954022988505747 | 0.9974259974259974 | 84 | 5115 | 0.55 |
| 20261012T132359Z_r3_leaderboard580_S | r3 | leaderboard580 | S | 580 | True | – | – | – | – | 0 | 0 | 0.00 |
| 20261012T132507Z_r3_tuning-eval_S_forced-novel | r3 | tuning-eval | S | 580 | True | 1 | 0.9976190476190476 | 1 | 0.9980694980694981 | 224 | 13871 | 0.42 |
| 20261012T133010Z_r3_tuning-eval_H_forced-novel | r3 | tuning-eval | H | 580 | True | 1 | 0.9976190476190476 | 1 | 0.9980694980694981 | 0 | 0 | 0.00 |
| 20261012T133458Z_r3_test928_S | r3 | test928 | S | 928 | True | – | – | – | – | 180 | 20328 | 0.45 |
| replaycheck_r3_test928 | r3 | test928 | S | 928 | True | – | – | – | – | 0 | 0 | 0.00 |
| 20261012T155533Z_r0_tuning-noex_S | r0 | tuning-noex | S | 2314 | True | 0.9991666666666667 | 0.9971924603174603 | 0.9991356957649092 | 0.9966093485105352 | 3480 | 211342 | 22.22 |
| 20261012T163028Z_r4_tuning-noex_S | r4 | tuning-noex | S | 2314 | True | 1 | 0.9983035714285714 | 1 | 0.9985468636473722 | 258 | 15114 | 1.67 |
| 20261012T163526Z_r4_tuning-eval_S_forced-novel | r4 | tuning-eval | S | 580 | True | 1 | 0.9976190476190476 | 1 | 0.9980694980694981 | 40 | 2165 | 0.04 |
| 20261012T163913Z_r4_tuning-eval_H_forced-novel | r4 | tuning-eval | H | 580 | True | 1 | 0.9976190476190476 | 1 | 0.9980694980694981 | 0 | 0 | 0.00 |
| 20261012T164501Z_r4_leaderboard580_S | r4 | leaderboard580 | S | 580 | True | – | – | – | – | 64 | 3894 | 0.42 |
| 20261012T165330Z_r4_test928_S | r4 | test928 | S | 928 | True | – | – | – | – | 64 | 3803 | 0.42 |
| replaycheck_r4_test928 | r4 | test928 | S | 928 | True | – | – | – | – | 0 | 0 | 0.00 |
