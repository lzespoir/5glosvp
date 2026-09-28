# P5_UE_THROUGHPUT_V0_1 — P5 用户吞吐率 / P5 UE Throughput

| 字段 | 值 |
|---|---|
| Metric ID | `P5_UE_THROUGHPUT_V0_1` |
| Version | 0.1（冻结 / frozen） |
| Unit | Mbps |
| Scope | 网络 / network |
| Input | `UE_THROUGHPUT_V0_1`（全部 active UE，**包含吞吐率为 0 的 UE**） |
| Measured | No |
| Acceptance KPI | No |
| Code | `evaluators.py::P5UeThroughputEvaluator` |

> **注意**：当前为系统级工程评价指标。尚未确认其与项目验收口径中的“边缘用户速率”完全等价。
> 平台中不得将其命名为 `EDGE_USER_RATE_ACCEPTANCE` 或作为验收结论。

## 定义 / Definition

\[
T_{P5} = \operatorname{percentile}\big(\{T_u\}_{u=1}^{N},\ 5\big)
\]

百分位方法冻结为 **线性插值（Hyndman & Fan type 7，`numpy.percentile(..., method="linear")`）**：

1. 将 \(N\) 个 UE 吞吐率升序排列为 \(x_0 \le \dots \le x_{N-1}\)。
2. \(r = 0.05 \cdot (N-1)\)，\(\ell = \lfloor r \rfloor\)，\(h = \lceil r \rceil\)。
3. \(T_{P5} = x_\ell + (x_h - x_\ell)(r - \ell)\)。

例：\(N = 6\) 时 \(r = 0.25\)，\(T_{P5} = x_0 + 0.25\,(x_1 - x_0)\)。

## 小样本说明 / Small-sample caveat

Day 5 场景只有 3–10 个 UE，P5 实际上是最差两个 UE 之间的插值，统计意义有限；
它用于验证 KPI 链路，而不是给出网络边缘性能结论。

## 变更规则

改变百分位方法、样本口径（例如排除零吞吐率 UE）或单位，必须发布新版本 ID。
