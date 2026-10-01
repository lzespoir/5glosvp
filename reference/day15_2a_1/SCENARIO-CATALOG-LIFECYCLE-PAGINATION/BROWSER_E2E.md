# Browser E2E

Application: `http://10.20.14.69:5176`, with Vite proxy to project API port 8000.

## Candidate paging and explicit promotion

- Selected a valid 24-candidate taxonomy slice (2 environments × 4 topologies × 3 UE groups; remaining dimensions fixed to supported values).
- Page 1 contained 20 candidates; page 2 contained 4. IDs did not overlap. Returning to page 1 yielded the same 20 IDs and first ID.
- Configured count remained 1 during preview and pagination. Explicitly promoting one candidate increased it to 2 and opened a DRAFT ConfiguredScenario. The temporary test definition was then removed through the safe-delete API; count returned to 1.

## Lifecycle and confirmation UX

- Created a temporary DRAFT through the library UI; opened the dynamic archive confirmation and archived it.
- It disappeared from the default active list, appeared under “已归档”, restored to the prior DRAFT state, and reappeared in the active list.
- The temporary unreferenced record was deleted afterward; the unrelated active and archived records were preserved.

## Captured errors

- After the confirmation-modal correction and a fresh lifecycle rerun: `console_error_count=0`, `page_error_count=0`, `unexpected_failed_request_count=0`.
- A separate direct GET of the just-deleted temporary ID returned the expected 404 as a deletion-verification assertion; it was not a browser failed request.
