# Lifecycle contract

- `GET /api/v1/workspace/scenarios` and `state=ACTIVE` return active definitions only; archived definitions are excluded by default.
- `state=ARCHIVED` is the explicit archived view.
- `POST /api/v1/workspace/scenarios/{id}/archive` soft-archives and records `pre_archive_state`, timestamp, and source (`API`). It does not delete definitions, instances, or history.
- `POST /api/v1/workspace/scenarios/{id}/restore` restores the captured state. Historical archived records without a captured state safely fall back to DRAFT; the fallback is documented in code.
- `DELETE /api/v1/workspace/scenarios/{id}` permits DRAFT, INVALID, and ARCHIVED definitions only. VALID/READY definitions must first be archived. Every deletion is checked server-side.
- A referenced definition returns HTTP 409 with `SCENARIO_REFERENCED`, `scenario_id`, and a reference summary. Delete never cascades.
- UI permanent-delete confirmation says it cannot be recovered, is allowed only when unreferenced, and will not delete related objects.
