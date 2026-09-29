# Day 11 Execution Manager Migration

New managed runs follow:

`API → Run Service → Execution Manager → owned Worker Process → problem evaluation adapter`

Run records persist `run_id`, `worker_id`, `pid`, `process_group_id`, status, start time, heartbeat, device/GPU cleanup status, and cancellation request state. Cancellation is graceful first; force termination requires a second confirmation and targets only the owned process group.

`time_limit_seconds` is an explicit run limit. It triggers cancellation and grace handling; a slow objective is not relabeled failed merely because an HTTP request waited too long. Legacy synchronous system/optimization services remain behind their migration boundary until a later task.

CUDA cleanup is reported honestly. When the current environment cannot verify CUDA cleanup, the record says `NOT VERIFIED IN CURRENT ENVIRONMENT`.
