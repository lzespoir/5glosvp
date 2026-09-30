# Day 15.1 — Navigation & Route Cleanup

**Status: Navigation cleanup implemented; product IA remains partial.** This package is intentionally limited to menu exposure, legacy entry points, route selection, documentation, and browser verification. It does not modify scenario scientific identity, A-Matrix calculations, radio calculations, execution, or comparisons.

## Target top-level navigation

Overview · Scenarios · Experiments · Algorithms · Analysis · Acceptance · System.

Scenario navigation exposes the configured scenario library, candidate-combination view, and the shared antenna pattern library. Environment, cell, antenna, and UE configuration remain sections of a specific configured scenario editor; the shared antenna library is not a substitute for per-scenario antenna binding.

## Route inventory

| Route / route family | Decision | Rationale |
| --- | --- | --- |
| `/overview` | KEEP | Platform overview. |
| `/scenarios` | KEEP | Configured definitions/library. |
| `/scenarios/advanced` | KEEP | Candidate combinations; distinct from configured definitions. |
| `/scenarios/:scenarioId` | KEEP | The scenario-specific configuration editor. |
| `/scenarios/assets/antenna` | KEEP + RENAME IN NAV | Shared A-Matrix pattern library/visualizer, not scenario configuration. |
| `/scenarios/ue` | REMOVE-FROM-NAV; KEEP DIRECT URL | Day13 UE Twin demonstration reads its existing independent data; it is not bound to the selected scenario. |
| `/scenarios/radio` | REMOVE-FROM-NAV; KEEP DIRECT URL | Day14 radio observation demonstration remains available, but is not an experiment-result context view. |
| `/scenarios/association` | REMOVE-FROM-NAV; KEEP DIRECT URL | Existing association optimization demonstration is not a scenario-editor subsection. |
| `/a-matrix` | REDIRECT | Compatibility redirect to the shared antenna library. |
| `/ue-twin` | REDIRECT | Compatibility redirect to the retained Day13 demonstration URL. |
| `/radio-observability` | REDIRECT | Compatibility redirect to the retained Day14 demonstration URL. |
| `/user-association` | REDIRECT | Compatibility redirect to the retained association demonstration URL. |
| `/experiments`, `/experiments/:experimentId`, `/system`, `/system/experiments/:experimentId`, `/optimizations/**` | KEEP | Experiment and execution-related surfaces. |
| `/algorithms`, `/algorithms/**`, `/algorithm-onboarding` | KEEP | Algorithm directory and onboarding. |
| `/benchmarks/**`, `/comparisons` | KEEP | Analysis and comparison surfaces. |
| `/acceptance` | KEEP | Acceptance surface. |
| `/platform-status` | KEEP | Platform capability status. |

The three retained `/scenarios/{ue,radio,association}` pages are compatibility-only direct routes. Their compatibility status must not be confused with contextual migration. The Workspace Editor no longer links to the unbound UE Twin or Day14 observation pages, and the Day13 demonstration no longer presents a shortcut as though it opened a scenario-bound Radio View. No attempt is made here to fake scenario/experiment binding or redirect to a semantically unrelated page.

## Explicitly not completed

- UE Twin bound to a selected `ScenarioInstance`.
- Radio observation separated into scenario preview versus experiment result and bound to the respective object.
- Shared map/coordinate state across scenario, UE, and radio views.
- Dedicated environment-asset route or upload/import workflow.

These are follow-up domain/UI integrations, not route aliases; they need their own acceptance criteria. Day15 product IA is therefore **PARTIAL / NOT FULLY FROZEN** even though the duplicate legacy navigation entries have been removed.

## Verification

- Frontend unit tests assert that configured scenarios and the shared antenna library remain navigable, while the legacy UE/radio/association URLs are absent from navigation and do not select an unrelated menu item.
- Browser check verifies the seven top-level destinations, absence of duplicate UE/radio/association links, and that direct legacy URLs still load their compatibility pages.
- No radio algorithms, scenario identities, experiment lifecycle, or comparison code is changed by this package.
