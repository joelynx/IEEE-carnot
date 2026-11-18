# Replay check: R3 test predictions regenerated from the response cache

Run on 2026-10-12T14:11:49.181038+00:00 with
`python -m carnot.run --config configs/r3.json --split test928 --run-id replaycheck_r3_test928`.

| | Value |
|---|---|
| Fresh model calls | 0 |
| Cached calls replayed | 2323 |
| Toolkit validate / package / validate-zip | True / PASS / True |
| Regenerated ZIP SHA-256 | `ea49187356a3f5d056ecfc7ca3ffbeaf767b96097b5dbd84153167569f77da2f` |
| Uploaded R3 ZIP SHA-256 (receipt `test-20261012T134339Z-cc2674e5…`) | `ea49187356a3f5d056ecfc7ca3ffbeaf767b96097b5dbd84153167569f77da2f` |
| **ZIP byte-identical** | **True** |
| Predictions byte-identical | True |

The submitted file is reproduced exactly from the logged configuration, code and cached model responses, with no model call.


# Replay check: R4 (the final submission)

Run on 2026-10-12T17:09:11.660408+00:00 with
`python -m carnot.run --config configs/r4.json --split test928 --run-id replaycheck_r4_test928`.

| | Value |
|---|---|
| Fresh model calls | 0 |
| Cached calls replayed | 2323 |
| Toolkit validate / package / validate-zip | True / PASS / True |
| Regenerated ZIP SHA-256 | `cec784e29f40f277d86ee6a38701e22ca117f1102abd5541083cefc8c60e0cc3` |
| Uploaded R4 ZIP SHA-256 (receipt `test-20261012T170418Z-811e06a0…`) | `cec784e29f40f277d86ee6a38701e22ca117f1102abd5541083cefc8c60e0cc3` |
| **ZIP byte-identical** | **True** |
| Predictions byte-identical | True |
