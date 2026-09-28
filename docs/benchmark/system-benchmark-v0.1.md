# SYSTEM_BENCHMARK_V0_1 — 系统级公平评价协议 / System Benchmark Protocol

| 字段 / Field | 值 / Value |
| --- | --- |
| Protocol ID | `SYSTEM_BENCHMARK_V0_1` |
| Version | `0.1`（冻结 2026-09-28 / frozen） |
| Simulation slots | **500** |
| Warm-up slots | **0** |
| Repeats | **1** |
| Aggregation | `single_run` |
| Common channel / UE population / traffic | Yes / Yes / Yes |
| Seed policy | 场景种子对全部评估固定；每次优化运行只做一次 Sionna RT 信道实现 |
| Observed variability | **6.9 %**（NETWORK_THROUGHPUT_V0_1） |
| 实现 / Implementation | `src/system_optimization/protocols.py` |
| Evidence | [`reference/day6_horizon_study/`](../../reference/day6_horizon_study/README.md) |

## 1. 目的 / Purpose

保证系统级优化中基线与每个候选在**完全相同的条件**下评估，使目标值的差异只来自优化变量，而不是 UE 位置、
信道实现、业务或仿真长度的差异。

## 2. 公共评估上下文 / CommonEvaluationContext

每次优化运行开始时构造一次，随记录持久化（`optimization.json` → `evaluation_context`，信道写入 `context/channel.npz`）：

| 项 | 内容 | 哈希 / ID |
|---|---|---|
| UE population | UE id、服务小区、位置 | `UEP-<sha8>`，sha256(JSON{ue_ids, serving_cell_ids, positions}, sort_keys, compact) |
| Channel realization | Sionna RT CFR `[UE,1,1,BS_ant,sym,subc]` complex64 | `CH-<sha8>`，sha256：按 key 排序，逐 key 写入 key、dtype、JSON shape、C-order bytes |
| Traffic | 业务模型（Day 6：full buffer） | `FULL_BUFFER_V0_1`，sha256(JSON model) |
| Horizon | slots、warm-up、slot duration | 来自本协议 |
| Backend | backend id + version | — |

所有候选实验通过 `run(channel=...)` 复用该信道（跳过 RT），实验记录中写入 `evaluation_context` 链接与 `channel_reused = true`。
后端从所消费的 CFR 以 float64 重新计算每 UE 平均信道增益，公平性检查要求与上下文逐位相同。

## 3. 公平性检查 / Fairness checks（每次运行自动执行并持久化）

`same_ue_population`、`same_channel_realization`（含增益逐位相同）、`same_traffic`、`same_simulation_horizon`、
`same_backend_version`、`only_variable_changed`（调度配置除优化变量外完全一致）。任一失败都会显示在 UI 的
“Fair Evaluation Conditions” 中。

## 4. 参数选择依据 / Why these settings

来自 Horizon Study（β ∈ {0.1, 0.3, 0.6, 0.9, 0.99}，一个冻结信道，200/500/1000 slots）：

- **500 slots**：最短的、候选排序与 1000 slots 相同的时长（200 slots 前两名互换，差 0.1%）；各候选相对 1000 slots
  的偏差 ≤ 3.2%（网络）/ 4.4%（P5），200 slots 时达 7.9% / 8.3%。CPU 上约 0.195 s/slot ⇒ 每次评估约 97 s。
- **warm-up 0**：保持 Day 5 KPI 的时间窗（全部仿真时隙）；warm-up 20/50/100 在 500 与 1000 slots 下都不改变排序。
- **1 次重复**：冻结信道下 SYS 逐比特确定（重复运行结果完全相同），重复不增加信息。
- **observed variability 6.9%**：`SYSTEM-DEMO-001` 三次独立完整运行（各自重新 RT + SYS，200 slots）网络吞吐率
  130.42–139.40 Mbps 的 (max−min)/min；两次 RT 实现在 200 slots 下只差 0.60%，取较大者作保守界。
  若 `|ΔJ%|` 不超过该值，结果附加“改善幅度处于已观测仿真波动范围内 / Improvement is within observed simulation variability.”

选择依据是稳定性与运行时间，而不是哪个设置显示更大的改善。

## 5. 限制 / Limitations

- 500 slots 时绝对 KPI 水平未完全收敛（相对 1000 slots 最多 3.2%）。
- 无 warm-up 时初始 OLLA/PF 瞬态使 β = 0.99 在 500 slots 下偏高至多 4.7%，排序不受影响。
- 单场景、单信道实现、full-buffer、每基站单小区；variability 只来自 3 次运行，是经验界而非置信区间。
- GPU 光线追踪存在微小数值漂移：不同优化运行的上下文（不同 RT 实现）之间的差异不能当作优化收益。

## 6. 版本规则 / Versioning

改变 slots、warm-up、repeats、aggregation、公共条件或 observed variability 必须发布新版本（`SYSTEM_BENCHMARK_V0_2`），
不得修改 V0.1，也不得覆盖用 V0.1 生成的 reference 结果。
