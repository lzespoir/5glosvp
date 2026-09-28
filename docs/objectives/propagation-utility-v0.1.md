# PROPAGATION_UTILITY_V0_1 — 传播效用目标函数 / Propagation Utility

| 字段 / Field | 值 / Value |
| --- | --- |
| Objective ID | `PROPAGATION_UTILITY_V0_1` |
| Version | `0.1`（冻结 / frozen） |
| Direction | `maximize` |
| 实现 / Implementation | `src/optimization/objectives/propagation_utility.py` |
| 计算位置 / Computed by | 后端 Objective Evaluator（前端只展示，不计算） |

> 这是**传播层工程目标函数**，用于验证参数优化闭环。它**不是**项目最终的吞吐率、边缘用户速率或优化速度验收指标，也不是网络覆盖率。
>
> A propagation-level engineering objective for validating the optimization loop. It is **not** a throughput, edge-user-rate, optimization-speed or acceptance KPI, and not a network coverage rate.

## 1. 公式 / Formula

```text
J(P) = C_sinr(P) − λ · c_P(P)

C_sinr(P) = N_covered(P) / N_cells
N_covered(P) = |{ cell : SINR(cell; P) is finite  AND  SINR(cell; P) ≥ τ }|

c_P(P) = (P − P_min) / (P_max − P_min)      (c_P = 0 when P_max = P_min)
```

| 符号 | 含义 | 单位 | 来源 / Source |
| --- | --- | --- | --- |
| `P` | 候选发射功率，作用于场景中所有发射机 | dBm | 候选参数 |
| `SINR(cell; P)` | Sionna RT `RadioMap.sinr`，多发射机时取最佳服务小区（max over TX），转换为 dB | dB | 真实 Sionna RT 仿真（`radio_map.npz` 中 `layer_sinr`） |
| `τ` | SINR 覆盖阈值 = **0 dB** | dB | **[A] Assumption**，V0.1 固定 |
| `N_cells` | 测量平面全部格点数（含无传播路径的格点） | — | Radio Map 网格 |
| `P_min`, `P_max` | 本次运行 **搜索空间 ∪ 基线功率** 中的最小/最大发射功率 | dBm | 运行配置 |
| `λ` (`lambda_power`) | 功率成本权重，默认 **0.10** | — | **[A] Assumption — Engineering Demonstration Parameter**，不是标准值 |

`J` 无量纲；`C_sinr ∈ [0, 1]`，`c_P ∈ [0, 1]`，因此 `J ∈ [−λ, 1]`。

## 2. SINR 覆盖比例的冻结定义 / Frozen coverage definition

- **输入**：候选实验的 `radio_map.npz` → `layer_sinr`（形状 `(ny, nx)`，单位 dB）。
- **覆盖**：`SINR` 为有限值且 `≥ 0 dB` 的格点计为覆盖；`NaN`（该格点无传播路径，例如位于建筑内部或无射线到达）计为**未覆盖**。
- **分母**：全部格点（不排除无路径格点），与平台已有的 `coverage_ratio` 分母一致。
- **SINR 的噪声/干扰**：由 Sionna RT 按场景带宽（`scene.bandwidth = bandwidth_hz`）与默认噪声温度计算热噪声；单发射机场景中干扰为 0，SINR 即 SNR。未建模接收机噪声系数。

### 与平台已有 “Radio Map Coverage” 的区别

平台已有的 `metrics.radio_map.coverage_ratio`（前端显示为 “Radio Map Coverage 无线电地图覆盖比例”）定义为：

```text
coverage_ratio = |{ cell : value(cell) is finite }| / N_cells
```

即“存在传播路径的格点比例”。路径是否存在只取决于几何与射线追踪，**与发射功率无关**：用它作为目标项时，`J` 只随功率成本单调下降，优化器必然选择最低功率，仿真结果对选择没有任何影响。因此 V0.1 使用带阈值的 SINR 覆盖比例（功率变化会改变 SINR，从而改变覆盖），并以不同的名称展示，避免与 “Radio Map Coverage” 混淆。两者都由后端计算，前端不重新计算。

## 3. 比较规则 / Comparison rules

- **基线 / Baseline**：场景原始配置（`configs/*.yaml` 中的发射功率），独立运行并保存为一次实验；它不是网格搜索的第一个候选。
- **公共随机条件 / Common random numbers**：基线和所有候选配置使用相同的 Scenario Seed（`random_seed`），以降低随机采样差异对参数比较的影响。
- **基线复用**：候选参数与基线完全相同时复用基线实验结果（`reused_baseline = true`），不重复调用 Sionna。
- **最优候选**：`J` 最大者；`J` 完全相同时选择**较低发射功率**（确定性 tie-breaker）。
- **改善 / Improvement**：
  - `absolute_improvement = J_optimized − J_baseline`
  - `relative_improvement_percent = (J_optimized − J_baseline) / |J_baseline| × 100%`；`|J_baseline| < 1e-9` 时为 `null`（不除零）
  - 允许为 0（No Improvement / 未获得改善）或负值，平台如实展示。

## 4. 假设汇总 / Assumptions

| 项 | 值 | 标记 |
| --- | --- | --- |
| `lambda_power` | 0.10（可在创建优化时覆盖，范围 0–10，实际值记录在优化结果中） | [A] Assumption |
| SINR 阈值 `τ` | 0 dB（V0.1 固定，不可覆盖） | [A] Assumption |
| 演示搜索空间 | 38, 40, 42, 44, 46 dBm | [A] Assumption — 工程演示值，不是 5G 标准值或华为现网配置 |
| 功率归一化区间 | 搜索空间 ∪ 基线功率 | 定义 |

## 5. 已知设计局限 / Known design limitations

- **功率成本相对覆盖收益较大**：在 `etoile` 演示场景中，SINR 覆盖比例在 38→46 dBm 区间仅变化约 1–2 个百分点，而功率成本项在同一区间变化 `λ = 0.10`。因此在默认 λ 下，最优解为搜索空间中的最低功率。实测（[`OPT-E56D9514`](../../reference/optimization/OPT-E56D9514/README.md)，Sionna RT 2.1.0）：C_sinr 在 38/40/42/44/46 dBm 分别为 55.54% / 56.14% / 56.66% / 56.94% / 57.16%，38 dBm 以 J = 0.5554 胜出（基线 44 dBm J = 0.4944），但其 SINR 覆盖比例比基线低 1.4 个百分点。这是 V0.1 目标函数的设计局限（Objective Design Limitation），按规定**不调整 λ 或阈值来制造更好看的结果**；如需修改，将发布 `PROPAGATION_UTILITY_V0_2`。
- 覆盖阈值基于 SINR（宽带），不是 3GPP RSRP / SS-RSRP 覆盖定义。
- 未建模接收机噪声系数、多小区干扰（当前场景为单发射机）。

## 6. 版本规则 / Versioning

公式、阈值、分母或归一化方式的任何改变都必须使用新的 Objective ID（如 `PROPAGATION_UTILITY_V0_2`），禁止在 `V0_1` 下悄悄修改。
