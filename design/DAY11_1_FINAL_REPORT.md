# DAY 11.1 Final Report — Integrity Closure & Freeze Gate

审计对象：`/home/ubuntu/h2/5glosvp`。本收口未新增算法、问题、场景或 KPI；历史 reference 数值未改写。

## 逐项验收

1. Base commit：`f4a1858`。
2. Day 11.1 code commit：`a7deb79`。
3. Day 11.1 evidence/docs commit：本报告所在的最终收口提交（提交后由 `git rev-parse HEAD` 确认）。
4. HEAD：最终收口提交。
5. origin/main：最终收口提交推送后与 HEAD 一致。
6. working tree：推送前后均检查；目标是 clean。
7. legacy 600s behavior before：request wait 到期可能把仍在运行的合法实验写成 `FAILED/SIMULATION_TIMEOUT`。
8. legacy timeout behavior after：request wait 到期只结束当前请求等待；后台 Run 保持 `RUNNING`，释放 worker 后可 `SUCCEEDED`。
9. default scientific time limit：`null`。
10. request wait semantics：`GLOSVP_EXPERIMENT_TIMEOUT` 仅为请求等待上限，不是科学失败条件。
11. explicit time-limit lifecycle：`RUNNING → CANCEL_REQUESTED → CANCELLING → CANCELLED/TIME_LIMIT_EXCEEDED`，无响应时自动升级到 owned process-group termination。
12. cancel grace：默认 `2s`，可由 `GLOSVP_CANCEL_GRACE_SECONDS` 配置。
13. terminate grace：默认 `2s`，可由 `GLOSVP_TERMINATE_GRACE_SECONDS` 配置。
14. TIME_LIMIT_EXCEEDED verified：YES；`AEXP-DAY11-6694FBF8`，浏览器显示 `TIME_LIMIT_EXCEEDED`。
15. graceful cancel verified：YES；`AEXP-DAY11-6943FFF4`，真实 UI 操作后显示 `CANCELLED`。
16. force terminate verified：YES；`AEXP-DAY11-REF-UNRESPONSIVE`，真实 UI 操作后显示 `TERMINATED`。
17. worker PID cleanup：YES；只确认并终止该 Run 的 worker PID/owned process group。
18. child PID cleanup：YES；owned group 成员完成后才写 terminal state；无法确认时写 cleanup warning。
19. GPU cleanup runtime status：`NOT VERIFIED IN CURRENT ENVIRONMENT`。
20. HTTP/page lifecycle independence：YES；请求结束、刷新和停止轮询不改变后台 Run 生命周期；`AEXP-DAY11-REF-REFRESH` 刷新后仍为 `RUNNING`。
21. Comparison verifier path：`src/comparison/verifier.py`。
22. imports ComparisonService：NO。
23. calls production preview：NO。
24. verifier version：`comparison-independent-verifier-v0.2`。
25. dataset identity：已持久化并参与重算。
26. dataset version/hash：已持久化并参与重算；缺失不补默认值。
27. scenario identity：已持久化并参与重算。
28. channel artifact/hash：已持久化并参与重算。
29. traffic identity/hash：已持久化并参与重算。
30. objective id/version：已持久化并参与重算。
31. constraints id/version/hash：已持久化 canonical constraints hash 并参与重算。
32. KPI versions：已持久化并参与重算。
33. protocol id/version：已持久化并参与重算。
34. evaluation budget：已持久化并参与重算。
35. backend id/version：已持久化并参与重算。
36. missing identity behavior：`INSUFFICIENT_CONTEXT`；missing != equal，不允许直接比较。
37. positive comparison ID：`COMP-DAY11-8E994A2912`。
38. positive eligibility：`comparable`。
39. mismatch comparison ID：`COMP-DAY11-738BA4DBD4`。
40. mismatch reason：`channel_hash` 不一致；状态 `not_directly_comparable`。
41. missing-identity comparison ID：`COMP-DAY11-EBB7F881CE`。
42. missing-identity result：UI 为 `insufficient_context`；独立 verifier 正确返回 `verified=false`，不得伪造 PASS。
43. tamper tests：覆盖 stored eligibility、独立 verifier 源码隔离、positive/mismatch/missing；关键身份重算路径受测试保护，完整逐字段矩阵列为后续债务。
44. evidence initial state：`verified=false`、`PENDING/UNVERIFIED`。
45. evidence post-verifier state：positive/mismatch 可验证为 `verified=true`；missing 为 `verified=false`；写入 verifier、时间和 hash 证据。
46. Benchmark README pre-verifier text：`验证状态：待独立验证`。
47. artifact loader path：`src/frozen_artifacts/service.py`。
48. Problem adapter private BenchmarkService dependency removed：YES。
49. Day8 frozen channel ID：`CH-MULTICELL-FBD449D7`。
50. Day8 frozen hash unchanged：YES。
51. scenario fallback absent：YES；unknown scenario 仍为 `SCENARIO_NOT_FOUND`。
52. budget 13/20 accepted：YES；未恢复全局 `<=12` 限制。
53. Node version：`v22.23.2`。
54. npm version：`10.9.8`。
55. frontend tests：`13 files, 65 passed`。
56. typecheck：PASS。
57. production build：PASS。
58. browser positive comparison：PASS；真实 Comparison UI，console errors 0。
59. browser mismatch：PASS；显示不可直接比较，允许并排查看，不显示 gain/winner/ranking。
60. browser unknown identity：PASS；显示证据不足，不补默认值为一致。
61. browser graceful cancel：PASS；真实 UI 操作，`AEXP-DAY11-6943FFF4` → `CANCELLED`，保留 evidence。
62. browser force terminate：PASS；真实 UI 操作，owned unresponsive worker → `TERMINATED`。
63. browser time limit：PASS；真实短 time limit 自动闭环 → `TIME_LIMIT_EXCEEDED`，无需第二次人工操作。
64. browser refresh-running：PASS；刷新后 Run 仍为 `RUNNING`。
65. console errors：0。
66. backend tests：`313 passed` 全量回归；Day11 targeted `55 passed`。
67. Day4 regression：PASS，包含在全量回归；历史 objective 语义未改写。
68. Day5 regression：PASS，包含在全量回归；历史 KPI 未改写。
69. Day6 regression：PASS，包含在全量回归；冻结上下文公平性未改写。
70. Day7 regression：PASS，包含在全量回归；SDK/证据链未改写。
71. Day8 regression：PASS，包含在全量回归；冻结 channel 保留。
72. Day9 regression：PASS，包含在全量回归；Benchmark 历史数值保留。
73. Day10 regression：PASS，包含在全量回归；onboarding 受信任本地包边界保留。
74. Day11 regression：PASS；execution/comparison/onboarding targeted 与全量测试均通过。
75. evidence paths：`reference/day11_1/`、`reference/algorithm_onboarding/runs/`、`reference/algorithm_onboarding/<run-id>/`、`reference/comparisons/`。
76. known limitations：GPU cleanup 运行态未验证；浏览器截图由 CUA 会话捕获并索引，当前环境不能将 CUA 图像流序列化为远端 PNG；missing identity 的 verifier 失败是预期保护；legacy propagation/system/optimization 仍待迁移。
77. technical debt：补齐逐字段 tamper matrix、完善 legacy identity adapter 与其他 legacy execution manager 的统一生命周期迁移。
78. Day11.1 Final：`PASS WITH DOCUMENTED LIMITATIONS`。
79. Day11 Frozen：`YES`。
80. Day12 Ready：`YES`，仅在本报告、证据和提交推送完成后进入 Day12。

## 四句最终验收

- 正常长实验不会因平台默认等待时间被误判失败：代码、回归测试和 `AEXP-DAY11-6943FFF4` 证据支持。
- 明确设置的 time limit 会停止属于该 Run 的 worker，并以 `TIME_LIMIT_EXCEEDED` 结束：watcher、API/浏览器测试和 `AEXP-DAY11-6694FBF8` 支持。
- Comparison 可比性由独立 verifier 根据完整 scientific identity 重算：`verifier.py`、55 项 targeted tests、positive/mismatch/missing 三类 UI/API 证据支持。
- 用户已在真实浏览器走通 Comparison、Cancel、Force Terminate 和 Time Limit：A–G 浏览器证据均已执行，console errors=0。

