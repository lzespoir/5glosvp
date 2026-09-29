# DAY11.1 Browser Evidence Index

本目录索引 DAY11.1 Freeze Gate 的浏览器与运行证据。所有 E2E 均在真实浏览器页面执行，浏览器 console errors 为 `0`。

| Case | Run / Comparison | Expected result | Evidence |
|---|---|---|---|
| A Positive Comparison | `AEXP-DAY11-9EC6CB01`, `AEXP-DAY11-AE42414B` / `COMP-DAY11-8E994A2912` | `comparable`, independent verification PASS | `/comparisons` UI + verifier record |
| B Known Mismatch | `AEXP-DAY11-REF-MISMATCH` / `COMP-DAY11-738BA4DBD4` | `not_directly_comparable`, reason `channel_hash` | `/comparisons` UI + verifier record |
| C Missing Identity | `AEXP-DAY11-REF-MISSING` / `COMP-DAY11-EBB7F881CE` | `insufficient_context`, verifier FAIL | `/comparisons` UI + failed verifier record |
| D Graceful Cancel | `AEXP-DAY11-6943FFF4` | `CANCELLED`, evidence retained | `/algorithm-onboarding?run_id=...` |
| E Force Terminate | `AEXP-DAY11-REF-UNRESPONSIVE` | `TERMINATED`, owned group cleanup | `/algorithm-onboarding?run_id=...` |
| F Explicit Time Limit | `AEXP-DAY11-6694FBF8` | automatic `TIME_LIMIT_EXCEEDED` | `/algorithm-onboarding?run_id=...` |
| G Refresh Independence | `AEXP-DAY11-REF-REFRESH` | refresh leaves Run `RUNNING` | `/algorithm-onboarding?run_id=...` |

## Screenshot note

Screenshots for A–G were captured in the CUA browser session while each case was verified. The current execution environment exposes those captures in the session output but does not provide a supported byte-stream export to the remote checkout; no synthetic PNG is claimed or added. The run JSON, comparison JSON, verifier output, UI routes, and this index are the committed, reproducible evidence.

## Runtime evidence

- API runs: `reference/algorithm_onboarding/runs/`
- run bundles: `reference/algorithm_onboarding/AEXP-DAY11-*/`
- comparison records: `reference/comparisons/`
- synthetic browser fixtures: `reference/day11_1/fixtures/`
- final report: `design/DAY11_1_FINAL_REPORT.md`

