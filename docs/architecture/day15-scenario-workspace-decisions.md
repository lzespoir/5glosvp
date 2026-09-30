# Day 15 Architecture Decisions

These decisions freeze the configuration foundation without claiming a new simulation backend.

## ADR-015-01 — Business workflows, not development days, organize navigation

The primary entries are Overview, Scenarios, Experiments, Algorithms, Analysis, Acceptance, and System. Scenario-owned capabilities (A-Matrix, UE geometry, and Day14 radio observability) live under Scenarios. Legacy paths redirect to their contextual pages rather than disappearing. Only the active submenu is expanded. The sider is 256px wide on desktop, internally scrollable, and sticky while page content scrolls.

## ADR-015-02 — Candidate combinations are not configured definitions

Day12's combination catalog remains separate from the configured workspace library. Counts distinguish configured, runnable, executed, experiment-verified, and acceptance-evidence objects. Saving or freezing a definition never increments run/verification/evidence counts.

## ADR-015-03 — Definition and frozen instance do not imply execution

Definitions are versioned and content-hashed. A frozen instance pins the definition hash, environment asset hashes, and seed. Run, observation, and evidence links are explicit but remain `NOT_CONNECTED` until an execution adapter exists. Day15 validation always reports `simulation_ready=false` and `experiment_ready=false`.

## ADR-015-04 — Unknown configuration is explicit; defaults carry provenance

Traffic, UE mobility/profile, and radio model start UNKNOWN. Users must select them explicitly. Core radio values require explicit value, unit, and source; unspecified secondary cell values produce warnings rather than invented defaults. A selected radio model is marked `USER_DEFINED` while its registered identity/version and calibration status come from the backend registry; selection does not imply runtime readiness.

## ADR-015-05 — Assets are references, not implicit imports or conversions

Asset registration is limited to configured allowlisted roots and records hash/metadata without mutating source files or converting them. Coordinate system and units are explicit. Map layers reference registered assets and are validated for duplicate identity and dangling references. OSM/GLTF renderer and network-format parsers are not claimed as implemented.

## ADR-015-06 — Antenna providers are extensible and scientifically bounded

A-Matrix is one `AntennaPatternProvider`; other providers are contract-only. Raw A-Matrix files and Day13 angular-grid, peak-normalization, and periodic nearest-grid semantics remain unchanged. The viewer defaults to a 3D spherical projection whose radius is relative response; 2D heatmap remains available. Overlay is visual only, never physical beam combining.

## ADR-015-07 — Browser navigation preserves migration compatibility

The contextual antenna route hosts the spherical viewer; UE and radio pages retain their existing capability through the Scenarios group. `/a-matrix`, `/ue-twin`, and `/radio-observability` remain compatibility redirects. Day14 scientific result identity and fixed-fixture semantics are not modified.
