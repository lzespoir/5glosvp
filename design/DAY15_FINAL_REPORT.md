# Day 15 Final Report — Platform IA & Scenario Configuration

**Conclusion: PASS WITH DOCUMENTED LIMITATIONS — foundation frozen.** This freezes the information architecture, configuration model/API, library semantics, and antenna workspace. It does **not** claim that Day15 definitions can run in the experiment engine.

> **Post-freeze IA audit update:** the initial freeze statement above overstated product IA completion. Day15 configuration foundations remain valid, but the unbound UE Twin/Radio demonstration routes were still exposed as scenario submenu entries and linked as if contextual. Day15.1 removes those navigation links and misleading shortcuts; its direct legacy routes remain compatible. Since UE Twin and Radio Observation are not yet bound to a selected ScenarioInstance/Experiment, **the product IA status is PARTIAL / NOT FULLY FROZEN**. See [`DAY15_1_NAVIGATION_ROUTE_CLEANUP.md`](DAY15_1_NAVIGATION_ROUTE_CLEANUP.md). Scientific and execution status claims below are unchanged.

## Provenance

- Base HEAD at start: `54984d6d149649bb13031ea6dcfd5722ac8a9cae`
- Base check: `HEAD == origin/main` before changes.
- Implementation commit: `8fc4d1d` (`feat: add scenario workspace foundation`).
- Final pushed HEAD: recorded by the freeze gate after push; the Git ref is authoritative because a commit cannot embed its own hash in its tree.
- Working tree and `origin/main` must be clean/equal after the freeze commit.

## Object model and status semantics

The workspace preserves `Asset → Definition → Instance → Run → Observation → Evidence`. A Definition has an explicit version and content hash. An Instance pins the exact definition and referenced asset hashes plus seed. A Run is not synthesized from an Instance: provenance currently shows `NOT_CONNECTED`. Observation and Evidence are not created by configuration.

Counts are independent: configured definitions, runnable scenarios, executed scenarios, experiment-verified scenarios, and acceptance evidence. One configured browser smoke definition was used during verification, then archived; current active configured count is `0`. Runnable `0`, executed `0`, experiment verified `0`, acceptance evidence `0`. Its two frozen instances remain `NOT_EXECUTED`. Day12 candidate counts remain in the candidate catalog and are not added to this library.

New workspaces default traffic, UE mobility/profile, and radio model to `UNKNOWN`; these must be selected before structural validation. Radio model registration does not imply execution readiness. Missing secondary cell values remain warnings; missing core frequency, bandwidth, or power and coordinate mismatches are errors. No values are silently converted into calibrated/absolute radio KPI.

## Product surface

- Seven primary destinations: Overview plus Scenarios, Experiments, Algorithms, Analysis, Acceptance, System.
- Scenario library lists configured definitions, not candidate combinations. It supports filters, paging, clone and archive; versioned section edits reject stale writes.
- Workspace sections cover basic information, environment/assets/layers, sites/cells and batch edit, antenna, UE, traffic, radio model, network functions, optimization problems, preview and validation.
- Contextual antenna page defaults to 3D spherical relative response and retains 2D heatmap, 1/4/8 visual overlays, beam navigation, rendering decimation controls, and artifact hash. It performs no physical multi-beam sum.
- Rendering uses a configurable stride (default 3: 31 × 24 samples per beam, 5,952 canvas points for eight beams); the 91 × 72 backend data/query remains intact. Eight-beam visual load was checked, but no FPS benchmark or low-end device stress test is claimed.
- Legacy Day13/Day14 URLs remain redirects to contextual locations; Day14 radio observation itself is preserved.
- Navigation sider is 256px at desktop, sticky/internal-scroll, readable Chinese-first two-line labels, and only the route's active group is expanded.

## Domain and implementation scope

- Environment asset types include OSM, GLTF, GeoJSON, raster, terrain, Sionna scene, and custom mesh. Registration is metadata/hash-only within allowlisted roots; it does not import, transform, render, or alter source bytes.
- Coordinates require explicit system/unit declarations and must agree across environment, sites, cells, and UEs. Map layers reject duplicate or dangling references.
- Network hierarchy is Site → Cell, with antenna binding; core and extension parameters retain source metadata.
- `NetworkImporter` is a contract only. No CSV/GeoJSON/vendor parser, online OSM downloader, GLTF renderer, or 1000-cell physical runner is enabled.
- A-Matrix is served by its existing adapter/profile; alternative providers are contract-only. Existing raw `.npy` artifacts were neither modified nor committed. The `(elevation, azimuth)` 91×72 grid, peak-relative normalization and Day13 nearest-grid semantics are unchanged.
- Current Day13 manifest: `8_BEAM_FAMILY` / `AMX-D13-66F4FA18D1FE` hash `66f4fa18d1fec7b8f19ae388feb9abaaf587f1d076101947c8fe85ee618bc8c0`; `7_BEAM_FAMILY` / `AMX-D13-1D8A986A040D` hash `1d8a986a040d117d389f09ea805f5b8d026cec3699a5cb2a8b19b01701fcbe2f`. Provider registry status: A-Matrix `IMPLEMENTED`; Sionna Built-in, Gaussian, Custom, External `CONTRACT_ONLY`.
- Traffic and handover have explicit workspace slots but are not newly implemented models.
- No Acceptance Scenario Set is selected; the existing first-N candidate materialization is not rebranded as representative coverage.

## Validation evidence

The evidence package is `reference/day15/day15-verification.json`. Verification commands run on the remote host with `conda activate 5glosvp`.

- Day15 backend tests: `12 passed` (including legacy radio-status compatibility, explicit provenance, version conflict, antenna-height batch edit, 1000-cell configuration-only smoke, and independent store verifier).
- Full backend regression: `341 passed` in the final full run.
- Frontend typecheck: passed.
- Frontend tests: `15 files / 67 tests passed`.
- Production build: passed (Vite production bundle generated).
- Browser: scenario create/configure/save/validate/freeze verified; configuration `VALID`, backend `NOT READY`, experiment `NOT READY`, frozen status `NOT_EXECUTED`. Antenna route verified default `3D spherical`, and 4/8 beam visual overlays loaded. `/radio-observability` compatibility and Day14 content were inspected before the final antenna route migration.
- Navigation: screenshots inspected at page top and after vertical scroll; sidebar remains readable and fixed.
- Console error count was not independently captured in this environment; transient API failures encountered while iterating were fixed and the final browser flow succeeded.
- Mobile/narrow viewport layout and quantitative canvas frame-rate were not separately benchmarked.

## Limitations and debt

1. Day15 execution adapter is not connected; no Day15 radio run, experiment, observation, or acceptance evidence exists.
2. Registered `FAST_PROPAGATION` describes the Day14 backend, which uses a fixed fixture; it is not a general Day15 scenario runner.
3. Network importers, OSM/GLTF conversion/rendering, traffic realizations, mobility traces, handover, measured-data integration, and calibrated absolute radio KPI remain unimplemented.
4. Assets remain host-local paths with allowlisted metadata/hash registration; portable object storage and asset upload are future work.
5. The accepted compatibility value `radio.status=AVAILABLE` is legacy-only and is treated as not registered; it never signals runtime readiness.
6. Day12's candidate set and first-N materialized catalog remain separate from a future coverage-driven Acceptance Scenario Set.

## Freeze gate

Freeze only after the final complete backend suite, frontend typecheck/tests/build, browser recheck, independent verifier, and `git status`/`HEAD == origin/main` after push. Day16 choice should be based on owner availability and acceptance gaps; candidates include import/scene integration, a real execution adapter, mobility/handover, or a coverage-driven acceptance set.
