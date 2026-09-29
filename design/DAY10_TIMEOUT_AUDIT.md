# Day 10 Timeout Audit

Status: PASS WITH DOCUMENTED LIMITATIONS  
Scope: trusted external algorithm onboarding V0.1 and the Day 10 benchmark run.

## Audit decision

Day 10 does not impose a hidden wall-clock timeout on an algorithm run. The
experiment API accepts `time_limit_seconds: null | number`; `null` is the
default and means that the run is governed by the platform evaluation budget
and lifecycle stop signal. A numeric value is an explicit user/configuration
choice and is recorded in the run evidence.

The implementation does not call `kill -9`, fake force termination, or claim
that a running Python package was cancelled. `cancel_requested` is reserved
for Day 11 execution management. Day 10 reports a post-run explicit time-limit
violation as `time_limit_exceeded` when the configured limit is exceeded; it
does not mislabel an interrupted process as cancelled.

## Classification

| Location / concept | Timeout or wait | Classification | Day 10 decision |
| --- | --- | --- | --- |
| `AlgorithmDriver` | evaluation budget / stop signal | lifecycle bound | PASS; platform controls the number of evaluations |
| `AlgorithmPackageService.run_and_wait` | short polling sleep | local status observation | PASS; not an algorithm timeout |
| experiment `time_limit_seconds` | optional explicit run limit | user/configuration limit | PASS; default is `null`, value is recorded |
| HTTP API | request/response handling | transport concern | separate from algorithm lifecycle; no API timeout is used as a run limit |
| subprocess / `asyncio` / `wait_for` | none introduced by Day 10 | not applicable | PASS |
| dependency installation | no automatic install | package policy | PASS; `requirements.txt` is informational only |
| cancellation | no force terminate in V0.1 | reserved lifecycle | deferred to Day 11; preserve `cancel_requested` field concept |

## Evidence requirements

Every completed external experiment records `evaluation_budget`,
`time_limit_seconds`, `evaluations_used`, `stop_reason`, runtime details and
the package identity hashes. The reference verifier must reject a claim of
algorithm correctness or paper reproduction based only on this integration
evidence.

## Follow-up

Day 11 must define cooperative cancellation, queued/running/terminal state
transitions, stale-run handling, resource ownership, and a real process
boundary before any hostile or untrusted package execution is considered.
