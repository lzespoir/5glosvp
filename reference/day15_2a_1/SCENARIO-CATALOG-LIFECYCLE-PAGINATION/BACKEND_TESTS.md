# Backend verification

Environment: remote `conda activate 5glosvp`.

- Focused lifecycle/candidate/workspace tests: **23 passed** after the final test addition (covered by the complete run below).
- Full backend suite: **352 passed in 215.24 s**.
- Includes 53-record catalog pagination, active/archived list and counts, archive/restore provenance, state restoration, safe deletion, referenced-delete rejection/no-cascade, candidate filters, stable query hash, offset validation, and synthetic 327-valid-candidate pagination (17 pages, 327 unique IDs, none missing).
- `git diff --check`: passed.
