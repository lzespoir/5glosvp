# Day 9.1 Benchmark Closure Audit

Base commit: `e2004d5`

Reference benchmark: `BENCH-DAY9-3C12U001`

Protocol: `ALGORITHM_BENCHMARK_V0_1`

This closure adds only evidence and read-only navigation around the existing Day 9 benchmark. It does not add algorithms, rerun Sionna RT, regenerate the frozen channel, change the protocol, or rewrite historical results.

## Runtime semantics

The persisted runtime object contains `total_wall_time`, `simulation_evaluation_time`, and `optimizer_overhead_time`. `total_wall_time` is the elapsed wall clock for the complete benchmark run and includes simulator evaluations. It is not a pure algorithm-compute metric. The UI uses the label `Total wall time (includes simulator evaluations)`.

## TD-009 — Deterministic Replay of Sionna RT

Re-running Sionna RT with the same nominal seed/configuration may produce a different channel artifact/hash. Therefore `same seed` is provenance metadata only. Directly comparable algorithm runs require the same frozen `artifact_id` and the same `artifact_hash`; independent propagation regeneration per algorithm is forbidden.

## Runtime environment

The closure record captures hostname/environment ID, OS, CPU model/count, GPU model/count, Python, Sionna, Sionna RT, Torch, and CUDA availability. The host exposes two RTX 3090 devices through `nvidia-smi`, but CUDA initialization is unavailable for this Torch build because the installed driver is too old; this is recorded as a limitation rather than inferred away.

## Browser closure

The persisted benchmark detail surface exposes Overview, Comparison, Convergence, Runs, Run Drilldown, and Evidence. Live smoke reached all six routes, clicked a persisted run ID into Run Drilldown, and found zero browser console errors. Comparison and Evidence screenshots were captured during the smoke run; the closure JSON records those captures and the verified route list.
