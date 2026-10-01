# Frontend verification

Environment: remote `conda activate 5glosvp`.

- Frontend tests: **72 passed across 16 files**.
- Candidate-builder test verifies a page-2 request uses server offset 20 and carries the same query identity.
- TypeScript: `tsc --noEmit` passed.
- Production Vite build: passed.
- Lifecycle archive/delete confirmations use the application-scoped Ant Design modal API; the browser check found no modal-context warning after this change.
