# NETWORK_THROUGHPUT_MAX_V0_1 — 网络吞吐率最大化 / Network Throughput Maximization

| 字段 / Field | 值 / Value |
| --- | --- |
| Objective ID | `NETWORK_THROUGHPUT_MAX_V0_1` |
| Version | `0.1`（冻结 / frozen） |
| Direction | `maximize` |
| Unit | Mbps |
| Input KPI | `NETWORK_THROUGHPUT_V0_1`（[定义](../kpi/network-throughput-v0.1.md)，Day 5 冻结，未修改） |
| Required experiment | system（Sionna RT → Sionna SYS），backend capability `channel_reuse` |
| 实现 / Implementation | `src/system_optimization/objectives.py` |
| 计算位置 / Computed by | 后端 Objective Evaluator（前端只展示，不计算；Objective 不调用 Sionna） |
| Acceptance KPI / Measured / Huawei data | No / No / No |

> 这是**系统级仿真优化目标**，用于在冻结评估协议下比较调度参数候选。它**不是**项目验收指标，结果不是华为实测网络优化结果。
>
> A system-level simulation objective for comparing scheduler-parameter candidates under a frozen benchmark protocol. It is **not** an acceptance KPI, and results are not Huawei measured network optimization.

## 1. 公式 / Formula

```text
J(x) = NETWORK_THROUGHPUT_V0_1(x)
     = Σ_u  Σ_{t ∈ [warmup, T)} decoded_bits_u(t) / ((T − warmup) · slot_duration) / 1e6     [Mbps]
```

- `x`：候选配置（Day 6：`scheduler_beta`，Sionna `PFSchedulerSUMIMO` 折扣因子，开区间 (0, 1)）。
- `T`、`warmup`：由评估协议给出（[SYSTEM_BENCHMARK_V0_1](../benchmark/system-benchmark-v0.1.md)：T = 500，warmup = 0）。
- `num_repeats > 1` 时 `J` 为各次重复的算术平均（V0.1 为 1）。

## 2. 次要 KPI / Secondary KPIs

`AVG_UE_THROUGHPUT_V0_1` 与 `P5_UE_THROUGHPUT_V0_1` 对每个候选都计算并保存，但**不进入目标函数**。
比较结果中每个 KPI 都给出 `baseline → best`、绝对 / 相对变化与方向（increase / decrease / unchanged）；
下降的 KPI 列入 `negative_kpi_changes`，UI 与报告必须显示，不得隐藏。

最大化网络总吞吐率会倾向于把资源分给信道好的 UE，可能降低 P5（边缘）UE 吞吐率 —— 这是该目标的已知 trade-off。

## 3. 比较规则 / Comparison rules

- **公共评估上下文**：基线与全部候选共享同一 UE 集合、同一信道实现（一次 RT，sha256 固定）、同一业务模型、同一时隙数与后端版本；只有优化变量不同。
- **基线**：场景配置中的参数值，独立评估；候选值与基线相同时复用基线实验（`reused_baseline`）。
- **最优候选**：`J` 最大者；`J` 完全相等时 **基线参数值优先**，其次按候选顺序（先出现者优先）。
- **改善**：`ΔJ = J(best) − J(baseline)`；`ΔJ% = ΔJ / |J(baseline)| · 100`（|J(baseline)| < 1e-9 时为空）。`ΔJ ≤ 0` 显示“当前候选范围内未发现优于基线的配置”。
- **波动提示**：`|ΔJ%| ≤` 协议的 observed variability 时附加警告“改善幅度处于已观测仿真波动范围内”。
- **失败**：基线失败或全部候选失败 ⇒ 优化 FAILED；单个候选失败被保留并显示。

## 4. 允许 / 禁止的表述 / Wording

- 允许：“在当前冻结仿真协议下，网络吞吐率提高 X%”。
- 禁止：“5G 网络性能提升”、“项目指标提升”、“现网提升”。

## 5. 独立复核 / Independent verification

`scripts/verify_system_optimization.py` 不 import 本实现，从 `slot_trace.npz` 独立复算每个候选的 KPI 与 `J`、最优选择、改善量与负向变化。

## 6. 限制 / Limitations

- 单目标；不考虑公平性或能耗。
- Full-buffer 下行业务；单场景 `SYSTEM-DEMO-001`；系统级仿真，非实测。
- 改变公式、输入 KPI 或比较规则必须发布新版本（V0.2），不得修改 V0.1。
