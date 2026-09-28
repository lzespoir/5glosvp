# NETWORK_THROUGHPUT_V0_1 — 网络吞吐率 / Network Throughput

| 字段 | 值 |
|---|---|
| Metric ID | `NETWORK_THROUGHPUT_V0_1` |
| Version | 0.1（冻结 / frozen） |
| Unit | Mbps |
| Scope | 网络 / network |
| Input | `UE_THROUGHPUT_V0_1`（全部 active UE） |
| Measured | No |
| Acceptance KPI | No |
| Code | `evaluators.py::NetworkThroughputEvaluator` |

## 定义 / Definition

\[
T_{\text{network}} = \sum_{u=1}^{N} T_u
\]

- \(N\)：场景中全部 active UE（包含吞吐率为 0 的 UE）。
- 单小区场景中等于该小区的下行小区吞吐率。

## 不可用 / Unavailable

没有 UE 结果时 `available = false`，`value = null`，并给出 `unavailable_reason`；不会返回 0。
