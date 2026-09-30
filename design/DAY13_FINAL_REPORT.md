# Day 13 Final Report — A-Matrix / UE Twin / Radio Geometry

1. Day 12 frozen base: `477a047220cadd0a9d132e53c1e8be9fd18b34b7`.
2. Day 13 implementation commit: `3627a73` (`feat: add Day13 A-Matrix and UE Twin radio geometry`).
3. Evidence and final-report commit: the post-implementation documentation commit recorded by `git log`.
4. Final HEAD/origin/worktree state is recorded by the closing verification below.
5. Read-only A-Matrix source: `/home/ubuntu/h2/sionnatest/webapp/data/a_matrix`.
6. Source files: two `.npy` libraries; no raw source file is copied into Git.
7. Raw source modified: NO.
8. Raw source committed: NO.
9. Supported libraries: `a_matrix_spread.npy` and `a_matrix_phase_power.npy`.
10. `phase_power`: supported through the same read-only, relative-response path; no absolute radio-unit claim.
11. `spread`: supported through the same read-only, relative-response path; no special unverified formula.
12. Leaf counts: spread `1216`; phase_power `1310`.
13. Container/leaf structure: object container with numeric finite `float64` leaves.
14. Angular-grid version: `D13-ANGULAR-GRID-0.1`.
15. Grid: axis 0 elevation `-90..90` step `2°`; axis 1 azimuth `0..355` step `5°`; shape `[91,72]`.
16. Axis convention source: `SIONNATEST_IMPLEMENTATION`, not owner-confirmed metadata.
17. Raw interpretation: nonnegative linear/gain-like signal strength; not dB and not an absolute calibrated unit.
18. Normalization: peak normalization `raw / max(raw)`.
19. Normalized peak: exactly `1` for valid nonzero patterns.
20. Field amplitude compatibility value: `sqrt(max(normalized_response, 0))`.
21. Quality policy: shape/numeric/finite/NaN/Inf/negative/max/all-zero checks; negatives warn and remain auditable; all-zero is an explicit error; no absolute-value repair.
22. Profile mapping: read from `profiles.json` through the adapter; mapping is partial where authoritative semantics are not proven.
23. Observed profiles include AAU5270E, AAU5619, AAU5636 and AAU5639; the source exposes spread SSB multi×8 and phase_power seven-beam families.
24. Core adapter/model implementation: `src/antenna/`.
25. Manifest evidence: `reference/day13/SCN-DAY13-AMATRIX-UE-TWIN/amatrix-manifest.json`.
26. UE Twin implementation: `src/ue_twin/`.
27. UE and AAU positions are explicit Cartesian coordinates.
28. Coordinate convention: Sionna scene Cartesian coordinates in metres.
29. Geometry computes distance, wrapped azimuth and elevation from `dx/dy/dz`.
30. Direction lookup: nearest grid point only.
31. Geometry tests cover azimuth wrap, elevation bounds and same-position rejection.
32. Interpolation: NOT implemented.
33. Query output: per-beam normalized relative response and lookup method.
34. Strongest beam: relative strongest beam only; no serving-beam or KPI inference.
35. Serving/neighbor context is carried as context only; no handover decision is executed.
36. Day 8 integration: overlay/context only; no historical association experiment was rerun.
37. Day 8 frozen channel: unchanged.
38. Scenario binding: A-Matrix identity endpoint/service is implemented.
39. Identity binds scenario payload, artifact, source hash, profile, normalization, grid and lookup policy.
40. Identity hash changes with the bound A-Matrix artifact/configuration; missing calibration remains explicit rather than inferred.
41. TD-012-01: fixed in the API/UI count vocabulary.
42. `definition_verified_count`: `120`.
43. `experiment_verified_count`: `0` for the new Day 13 catalog.
44. `acceptance_evidence_count`: `0`.
45. AcceptanceScenarioSet schema/status: `DRAFT` / `NOT_SELECTED`.
46. Final acceptance scenario set selected: NO.
47. A-Matrix Explorer, profile/beam selectors and normalized 2D heatmap: implemented.
48. UE Twin Viewer and geometry query: implemented.
49. UI labels the beam values as normalized relative response.
50. UI shows the calibration warning and provenance boundary.
51. Absolute RSRP: NOT claimed or calculated.
52. Absolute SINR: NOT claimed or calculated.
53. Calibration gate: `ABSOLUTE_RADIO_KPI_NOT_CALIBRATED`.
54. Backend regression: `324 passed`.
55. Frontend regression: `15` test files, `67 passed`.
56. Runtime: conda environment `5glosvp`; Node `v22.23.2`; npm `10.9.8`.
57. Frontend typecheck and production build: PASS.
58. Browser E2E: PASS for Explorer, UE Twin query, geometry, response table and calibration boundary.
59. Clean Day 13 browser console errors: `0`.
60. Adapter loading: lazy per-library loading with warm-query cache; no performance benchmark claim.
61. Independent evidence verifier: `verified: true`.
62. Day 4–12 regression: PASS through the full backend/frontend suites above.
63. Evidence root: `reference/day13/SCN-DAY13-AMATRIX-UE-TWIN/`.
64. Limitations: owner semantic confirmation, absolute calibration, interpolation, dynamic mobility, handover and large-scale RT rerun remain out of scope.
65. Technical debt: authoritative profile/axis/unit metadata, formal phase_power/spread semantics, coverage-driven acceptance selection, and full comparison-service binding.
66. Day 13 disposition: `PASS WITH TECHNICAL DEBT`.
67. Day 13 freeze: YES after final documentation commit, push and clean-worktree verification.
68. Day 14 readiness: YES, pending review; no acceptance route is preselected.

## Allowed claim boundary

This Day 13 implementation supports read-only A-Matrix inspection, explicit angular-grid convention, peak-normalized relative beam response, Cartesian UE/AAU geometry, nearest-grid lookup, relative beam ranking, and provenance-bound scenario identity. It does not support absolute RSRP, absolute SINR, calibrated link-budget claims, interpolation, handover, mobility execution, or acceptance evidence by itself.
