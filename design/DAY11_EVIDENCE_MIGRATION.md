# Day 11 Evidence Migration Note

Day 4–10 reference directories are historical evidence and are not rewritten by Day 11. Some of those references use the earlier `independently_verified` or `PASS` wording; that is retained as `legacy_verification_semantics` for auditability and is not reinterpreted as a new Day 11 verifier result.

New benchmark and external algorithm records use:

`UNVERIFIED → PENDING → VERIFIED / FAILED`

Only the independent verifier may write `verified=true`, `verifier_id`, `verified_at`, and `verification_hash`. Platform validation, package registration, smoke tests, and successful execution are not independent verification.

Day 9 and Day 10 numerical values, protocol hashes, channel references, and historical benchmark membership remain unchanged.
