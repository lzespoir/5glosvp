# AVG_UE_THROUGHPUT_V0_1 — 平均用户吞吐率 / Average UE Throughput

| 字段 | 值 |
|---|---|
| Metric ID | `AVG_UE_THROUGHPUT_V0_1` |
| Version | 0.1（冻结 / frozen） |
| Unit | Mbps |
| Scope | 网络 / network |
| Input | `UE_THROUGHPUT_V0_1`（全部 active UE） |
| Measured | No |
| Acceptance KPI | No |
| Code | `evaluators.py::AverageUeThroughputEvaluator` |

## 定义 / Definition

\[
T_{\text{avg}} = \frac{1}{N} \sum_{u=1}^{N} T_u
\]

- 算术平均；\(N\) 包含吞吐率为 0 的 UE。
- 没有 UE 结果时不可用（`value = null`）。
