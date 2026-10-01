# Day 15.2A — Scenario Catalog Semantics

## Decision

The primary product catalog is the persisted Day15 `ConfiguredScenario` store. It represents explicitly saved definitions and does not synthesize entries from taxonomy products. The existing `/scenarios` route already reads this store; Day15.2A makes the adjacent advanced route a candidate assistant and removes the generated first-N catalog from normal UI traffic.

`ConfiguredScenario` remains the canonical persisted definition model for this slice. It gains explicit classification and source/lineage values where necessary, but is not renamed or duplicated as a second `ScenarioDefinition` class. A future schema/version migration can choose a stable public name after the object/identity contract is settled.

## Candidate lifecycle

```text
Taxonomy filters
  → bounded, stateless ScenarioCandidate preview
  → explicit user promote
  → persisted ConfiguredScenario (DRAFT, source=CANDIDATE_PROMOTED)
  → user fills actual Environment / Site / Cell / Antenna / UE / Traffic / Radio config
```

Preview returns a candidate DTO with a deterministic candidate ID/hash. It is not persisted and does not affect configured counts, coverage, evidence, or acceptance. Promotion sends both ID and full dimensions; the server recomputes identity, rejects mismatches/invalid combinations/duplicates, and writes one draft definition with classification and lineage. It does not imply that taxonomy tags have become physical network configuration or that the new definition is runnable.

## Historical Day12 boundary

Day12 taxonomy, combination rules, first-120 semantic definitions, verifier and evidence remain unchanged as historical records. The legacy catalog/materialize/coverage endpoints remain available for compatibility, are explicitly marked `LEGACY_CANDIDATE_CATALOG` and `NOT_ACCEPTANCE_SCENARIO_SET`, and are not called by the normal Scenario UI. No Day12 definition is automatically imported or promoted.

## Count and coverage semantics

- `configured_scenario_count`: non-archived persisted Day15 definitions, including explicit DRAFT definitions; candidate previews are excluded.
- `runnable_scenario_count`: only definitions whose state is `READY`; a structurally valid definition is not made READY while the Day15 execution adapter is absent.
- `executed_scenario_count`, `experiment_verified_count`, and `acceptance_evidence_count`: remain zero until their authoritative execution/evidence stores are integrated. Definition validation cannot increment them.
- Configuration coverage is computed from persisted, non-archived definitions and their saved family/classification/problem fields. It never reads the Day12 candidate product.

## Explicitly deferred to Day15.2B

This package does not consolidate the two existing `ScenarioInstance` classes, alter `ExperimentRecord`, introduce ExperimentPlan/Task/Run persistence, change ExecutionManager, or migrate historic experiment records. The current ExperimentService remains the legacy execution path. Day15.2B must define a compatibility adapter and prove that new experiments reference an immutable frozen workspace instance before connecting the two lifecycles.

## Safety constraints

- Do not modify Day12 frozen evidence, Day13 A-Matrix hashes/lookup/normalization, Day14 radio semantics, or Day11.1 ExecutionManager.
- Do not turn preview, instance seed, algorithm parameter, optimization problem, network-function selection, or antenna provider selection into an implicit new business scenario.
- Do not advertise blank promoted drafts as READY, executed, experiment-verified, typical, or acceptance-selected.
- Browser promotion smoke, if used against the shared service, must archive its generated smoke definition afterward and preserve its audit record.
