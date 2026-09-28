# UE_THROUGHPUT_V0_1 — 用户吞吐率 / UE Throughput

| 字段 | 值 |
|---|---|
| Metric ID | `UE_THROUGHPUT_V0_1` |
| Version | 0.1（冻结 / frozen） |
| Unit | Mbps |
| Scope | 单 UE / per UE |
| Source | System Simulation Result（系统级仿真结果中的成功译码比特数） |
| Measured | No — 仿真生成，不是实测 |
| Acceptance KPI | No |
| Code | `src/evaluation/kpi/definitions.py` · `evaluators.py::UeThroughputEvaluator` |

## 定义 / Definition

\[
T_u = \frac{B_u}{T_{\text{sim}}} \cdot 10^{-6}
\]

- \(B_u\)：仿真时长内 UE \(u\) **成功译码（HARQ ACK）** 的比特总数 = Σ 每时隙 PHY Abstraction 返回的 `decoded_bits`。
- \(T_{\text{sim}}\) = 时隙数 × 时隙长度（例如 200 × 0.5 ms = 0.1 s）。

## 口径说明 / Notes

- 这是**仿真时长内的平均吞吐率**，被调度与未被调度的时隙都计入分母。
- 不是 Shannon 容量、不是 PHY 峰值速率、不是频谱效率 × 带宽。
- 被 NACK 的传输块不计入 \(B_u\)；HARQ 重传合并由 Sionna SYS `PHYAbstraction` 建模。
- 从未被调度或全部失败的 UE，\(T_u = 0\)（不是缺失值），仍计入所有网络级 KPI 的样本。

## Assumptions

- [A] Full Buffer 下行业务（所有 UE 始终有数据待发）。
- 其他场景假设见 `docs/assumptions.md`。
