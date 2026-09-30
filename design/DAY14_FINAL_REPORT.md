# Day 14 Final Report — Multi-site Radio Observability

## Freeze status

**Status: PASS WITH DOCUMENTED LIMITATIONS / OBSERVABILITY FOUNDATION READY**

Day 14 establishes a real multi-site/multi-cell radio observation path on top of the Day 13 UE Twin and A-Matrix implementation. It does not claim calibrated RSRP/SINR, measured data, handover execution, or a Sionna RT rerun.

Base after history rebuild: `21d58f0dceed485fff26a69392e2928ebd26c60a`.

## Delivered

- `RadioMetricValue`, calibration status, semantic type, source type, model version, artifact id/hash and notes.
- `CellRadioConfig` with explicit site/cell/AAU positions, tx power, carrier frequency, bandwidth, antenna profile, A-Matrix artifact/hash, beam and propagation configuration.
- `ScenarioRadioContext` with one Scenario definition/instance context, 2 sites, 3 cells and 3 UEs. The service is collection based and has no hardcoded three-cell execution loop.
- Existing Day 13 `UETwin` extended with a `radio_observations` reference; the returned `RadioObservationSet` carries the attached UE Twin representation.
- Existing Day 13 geometry and `nearest_grid` A-Matrix lookup reused for every cell.
- `FastPropagationBackend` version `D14-FAST-PROPAGATION-0.1` with explicit distance, path-loss, transmit-power and relative antenna-response components.
- `SIM_RECEIVED_POWER`, aggregate interference, explicit noise floor and `SIM_SINR` with `UNCALIBRATED_SIMULATION` status.
- Scenario-defined serving cell and ranked neighbors; no handover claim.
- Context-bound observation, serving/neighbor and interference APIs under `/api/v1/radio`.
- Chinese-first Multi-cell Radio View at `/radio-observability`, including UE state, multi-cell table, serving/neighbor, decomposition, calibration and provenance.
- Independent payload verifier and Day14 evidence bundle.

## Scientific boundary

The A-Matrix remains peak-normalized relative directional response. `SIM_RECEIVED_POWER` is a Fast-backend simulation comparison value, not RSRP. `SIM_SINR` is derived from the simulated signal, declared neighbor contributions and an explicit Fast-backend noise assumption. No measured data, absolute antenna gain, calibrated KPI, Sionna RT execution, or handover execution is represented as complete.

## Evidence and verification

Evidence is under `reference/day14/SCN-DAY14-MULTISITE-RADIO/`. The independent verifier checks identity reconstruction, multi-site/cell cardinality, serving binding, geometry units, metric naming, calibration boundary, A-Matrix provenance and UE Twin attachment without calling the production observation service.

Regression results at freeze:

- Backend: `329 passed`.
- Day14 backend tests: `3 passed`.
- Frontend: `15 passed`, `67 passed`.
- Frontend typecheck and production build: passed.
- Browser E2E: Radio View loaded, displayed 3 cells and 3 UEs, switched UE-D14-001 to UE-D14-002, and console errors were `0` on the clean run.

## Explicit limitations / next work

- Fast propagation is an observability backend, not a calibrated propagation or RT result.
- The current scenario is an explicit Day14 integration fixture and is not acceptance evidence for measured network performance.
- The UI currently exposes the Radio View as a platform entry; a later scenario-detail deep link can reuse the same API contract.
- Beam Explorer linkage and full Sionna backend remain architectural/next-stage work.
