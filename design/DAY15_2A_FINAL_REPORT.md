# Day 15.2A — Candidate / Configured Scenario Boundary

## Status

**15.2A implementation: READY FOR REVIEW (not frozen).** This closes only the scenario-catalog semantics slice. Stop here for audit before starting Day15.2B.

**Day15.2B is not implemented:** no canonical ScenarioInstance consolidation, ExperimentPlan/Task/RunAttempt lifecycle, ExperimentRecord migration, or ExecutionManager change is claimed.

## Starting point and repository state

- Starting `HEAD`: `7129ba085802d7c7c3a7e78210244f0a594ea9ea` (`main`).
- At final check, `HEAD == origin/main`; the worktree contains the scoped Day15.2A changes and the user-provided untracked Day15.2 task file. No commit or push was performed.
- `git diff --check`: passed.
- Day12 historical evidence, Day13 A-Matrix data/hash/normalization/lookup, Day14 radio semantics, and Day11.1 execution code were not changed.

## Delivered behavior

1. The advanced Scenario route is now a bounded candidate builder. Every taxonomy dimension requires an explicit selection; candidate-space enumeration is capped at 5,000 combinations and returns at most 100 candidates (the UI requests 50). Preview is in-memory only and returns explicit `persisted=false`, `configured_count_changed=false`, and `acceptance_eligible=false` semantics.
2. Saving is an explicit promotion action. The server recomputes candidate identity from the submitted dimensions, rejects unknown/invalid/tampered/duplicate candidates, then writes one Day15 `ConfiguredScenario` in `DRAFT` with taxonomy classification, `CANDIDATE_PROMOTED` source, candidate hash, and lineage. It does not create physical network configuration, an Experiment, a run, or evidence.
3. The Scenario Library is the only primary persisted-definition view. Counts exclude previews and archived records. Coverage is derived only from persisted, non-archived workspace definitions (`PERSISTED_CONFIGURED_SCENARIOS`).
4. Day12 first-N catalog, materialization, and candidate coverage routes remain for compatibility, are marked deprecated where applicable, and identify the catalog as `LEGACY_CANDIDATE_CATALOG` / not acceptance eligible. The primary candidate UI no longer requests the Day12 catalog, materialize, coverage, acceptance mapping, or legacy experiment routes.
5. README and the architecture decision note document this boundary and explicitly defer the Scenario→Experiment→Task→Run contract to 15.2B.

## Verification evidence

- Full backend suite: **345 passed** in the remote `5glosvp` conda environment.
- Focused Day15/candidate/legacy-scenario suite after the final backend route annotation: **22 passed**.
- Full frontend suite: **71 passed** across 16 test files.
- Frontend production build and TypeScript check: **passed**.
- Browser smoke on `/scenarios/advanced`: selected a supported one-point taxonomy slice; preview returned one rule-classified candidate, displayed `候选预览 · 1 条（未保存）`, and `已保存场景变化 = 否`. The API access log records `POST /api/v1/scenario-candidates/preview` → `200 OK`.
- Browser console error check for the tested page: **no errors observed**.
- Post-smoke workspace counts: configured 0, runnable 0, executed 0, experiment-verified 0, acceptance evidence 0. The existing archived browser smoke definition remains archived and is excluded; no new scenario was persisted by browser verification.

## Review gates still open

- Audit this 15.2A diff and its count/candidate semantics before proceeding.
- Day15.2B must define the immutable ScenarioInstance → Experiment relationship, decide compatibility for the existing Day12 and legacy ExperimentService models, and introduce Task/RunAttempt adapters without changing the historical execution guarantees.
- No claim is made that candidate-rule `VALID_EXECUTABLE` means a Day15 scenario is configured, runnable, executed, experimentally verified, or acceptance-ready.
