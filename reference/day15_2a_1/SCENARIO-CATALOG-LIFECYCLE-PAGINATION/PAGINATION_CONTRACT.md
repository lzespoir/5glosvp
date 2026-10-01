# Pagination contract

## Configured library

- Server-side `offset`, `limit`, `total`, and `items`; default page size 20, maximum 100.
- Stable order: `updated_at` descending, then `scenario_id` descending.
- Search/status/family/problem/traffic filters are applied before total and page slicing. Archived is included only for the explicit archived filter.

## Candidate assistant

- Stateless POST preview accepts selection, filters, offset, limit, and optional `query_hash`; default page size 20, maximum 100.
- `valid_candidate_count` is before optional filters; `filtered_candidate_count` and `total` are after filters. `has_more` indicates another page.
- Enumeration is deterministic in taxonomy dimension order and taxonomy option order. Candidate IDs remain derived from definition identity.
- `query_hash` binds taxonomy version, normalized selection, and normalized filters; stale submitted hashes return 409.
- The 5,000-combination cap is a per-request search safety bound, not a scenario-capacity limit. Exceeding it returns 422 rather than truncating.
- Only requested-page candidate DTOs are retained; candidate previews are not persisted.
