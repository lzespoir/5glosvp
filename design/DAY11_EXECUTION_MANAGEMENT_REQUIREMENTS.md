# Day 11 Execution Management Requirements

Day 10 proves trusted package onboarding. Day 11 defines the execution-control
layer required before treating algorithm runs as a managed platform service.

## Required state machine

`QUEUED → RUNNING → COMPLETED | FAILED | TIME_LIMIT_EXCEEDED | CANCEL_REQUESTED → CANCELLED`

The transition must be persisted atomically and be visible through the API and
UI. A terminal run is immutable apart from verifier annotations.

## Required controls

1. Cooperative cancellation must be explicit. The algorithm driver receives a
   cancellation signal between lifecycle phases and the platform records
   `cancel_requested_at`, `cancelled_at`, and the actor/request id.
2. A numeric wall-clock limit must be enforced by the execution manager, not by
   a misleading post-run label. The manager must distinguish transport
   timeouts from algorithm-run limits.
3. Resource ownership, queue position, worker identity, heartbeat, retry
   policy, and stale-worker recovery must be auditable.
4. External package execution must have a process boundary, declared resource
   limits, a read-only package mount, controlled output/evidence paths, and an
   explicit dependency policy. Do not present trusted in-process Python as a
   sandbox.
5. Logs, trace, KPI and evidence export must remain available after failure or
   cancellation, with a structured error code and no silent partial success.
6. Rerun and clone must create new immutable run identities and preserve the
   parent run relationship.

## Required tests

- queued run cancellation before worker start;
- cooperative cancellation during `suggest`, `evaluate`, and `observe`;
- hard wall-clock enforcement with no orphan worker;
- worker crash and heartbeat expiry;
- duplicate requests / idempotency;
- concurrent runs and resource admission;
- terminal evidence completeness for completed, failed, timed-out and cancelled runs;
- Day 4–10 regression, including the frozen-channel benchmark.
