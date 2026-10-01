# Source integrity

Changed scope is limited to Workspace scenario lifecycle/listing, candidate-preview pagination/filtering, corresponding frontend/API types, the independent Day15 definition-hash verifier's lifecycle-metadata exclusions, and tests/evidence.

- Day12 taxonomy and historical catalog evidence: unchanged; legacy 120 are not counted as configured scenarios.
- Day13 A-Matrix assets/hash/normalization/angular grid/lookup: unchanged.
- Day14 Radio Observation scientific semantics: unchanged.
- Day11.1 ExecutionManager/process ownership/cancellation/time-limit logic: unchanged.
- Scenario→Experiment/Task/RunAttempt refactor (Day15.2B): not started.

The verifier change excludes the new lifecycle timestamps/state-provenance fields from the scientific definition hash, matching `definition_digest`; lifecycle metadata does not alter scenario identity.
