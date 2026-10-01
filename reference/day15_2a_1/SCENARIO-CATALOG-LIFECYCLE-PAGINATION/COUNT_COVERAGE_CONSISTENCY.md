# Count and coverage consistency

- Configured count counts persisted, non-ARCHIVED `ConfiguredScenario` definitions only.
- Coverage source remains `PERSISTED_CONFIGURED_SCENARIOS` and derives from that same active set.
- Candidate Preview, legacy Day12 catalog rows, and archived definitions do not affect configured count or coverage.
- Current workspace snapshot after browser-test cleanup: active configured = 1; archived = 1 (pre-existing); runnable/executed/experiment-verified/acceptance-evidence = 0; coverage active count = 1.
- Lifecycle test: 53 definitions were paged; after archiving 3, active total/count/coverage were 50 and archived total was 3. Restore returns the record to the same active set; deleting an archived unreferenced definition does not change active coverage.
