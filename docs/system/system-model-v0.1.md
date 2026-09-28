# 系统级仿真模型 V0.1 / System-Level Simulation Model V0.1

第一个 5G 用户故事：**多用户下行系统仿真 / Multi-UE Downlink System Simulation**。

```text
BS / Cell / UE  →  传播 Propagation (Sionna RT)  →  PHY: SINR · 链路自适应 MCS · 译码/HARQ
                →  调度 / 资源分配 (Sionna SYS)  →  UE 吞吐率  →  网络 KPI  →  证据 Evidence
```

## 1 场景层 / Scenario (`src/system_simulation/models.py`)

| 模型 | 说明 |
|---|---|
| `BaseStation` | bs_id、位置 [m] |
| `Cell` | cell_id、所属 BS、载频、信道带宽、发射功率 [dBm]、天线阵列 |
| `UserEquipmentConfig` | 显式 UE（ue_id、位置、可选服务小区） |
| `UeGeneratorConfig` | 程序生成 UE：`uniform_area_with_path`，seed、区域中心/尺寸、高度、候选数、count |
| `TrafficDemand` | `full_buffer`、downlink、`[A]` |
| `SystemSimulationConfig` | 时隙数、SCS、PRB 数、每时隙数据符号数、噪声系数、调度/链路自适应/功率控制配置 |
| `SystemScenario` | 以上组合 + backend + scene + seed + assumptions；`ues` 与 `ue_generator` 必须二选一 |

Day 5 演示场景 `configs/system/multi_ue_demo.yaml`（`SYSTEM-DEMO-001`）：
1 BS / 1 Cell / 6 UE，3.5 GHz，100 MHz（30 kHz SCS × 273 PRB），44 dBm，2×4 TR 38.901 阵列，full buffer，seed 20260927。

### UE 生成 / UE generation

1. `numpy.random.default_rng(seed)` 在区域内均匀生成 `max_candidates` 个候选位置（z = height_m）。
2. 后端对全部候选做一次传播计算；按生成顺序保留前 `count` 个**与服务小区存在传播路径**（平均信道增益 > 0）的位置。
3. 保留的候选索引写入结果 `ue_generation.kept_candidate_indices`。

## 2–4 传播 / PHY / 系统层（`SionnaSystemBackend`）

| 步骤 | 实现（Sionna 2.1.0） |
|---|---|
| 信道 | `sionna.rt.PathSolver`（max_depth 5，无折射）→ `paths.cfr()`：每 UE × 每数据符号 × 每子载波的 CFR |
| 调度 | `sionna.sys.PFSchedulerSUMIMO`（比例公平，β = 0.9），输入：已译码比特历史 + 可达速率估计 |
| 功率分配 | `sionna.sys.downlink_fair_power_control`（guaranteed_power_ratio 0.5，fairness 0） |
| 预编码 / SINR | `sionna.phy.ofdm.RZFPrecodedChannel` + `LMMSEPostEqualizationSINR` |
| 链路自适应 | `sionna.sys.OuterLoopLinkAdaptation`（BLER 目标 0.1，MCS 表 1，PDSCH） |
| 译码 / HARQ | `sionna.sys.PHYAbstraction` → 每时隙 decoded_bits、HARQ ACK/NACK、有效 SINR |

每时隙记录 `decoded_bits / harq / mcs / sinr_eff_db / num_re / tx_power_w`，保存为 `slot_trace.npz`，供独立复核。

## 5 KPI 层（`src/evaluation/kpi/`）

KPI 只在评价层计算；后端不计算 KPI，前端不计算 KPI。

| KPI | 定义文档 |
|---|---|
| `UE_THROUGHPUT_V0_1` | `docs/kpi/ue-throughput-v0.1.md` |
| `NETWORK_THROUGHPUT_V0_1` | `docs/kpi/network-throughput-v0.1.md` |
| `AVG_UE_THROUGHPUT_V0_1` | `docs/kpi/average-ue-throughput-v0.1.md` |
| `P5_UE_THROUGHPUT_V0_1` | `docs/kpi/p5-ue-throughput-v0.1.md` |

每个 KPI 结果带溯源：metric_id、version、value、unit、source_experiment、backend、scenario、seed、
calculation_method、measured（恒为 false）、assumptions、acceptance_kpi（恒为 false）、available / unavailable_reason。

## 实验与产物 / Experiment & artifacts

`experiment_type = system`（与 `purpose` 分离）。`POST /api/v1/system-experiments` 同步执行，产物位于
`data/system_experiments/EXP-*/artifacts/`：
`config.yaml`、`result.json`、`ue_results.json`、`kpi.json`、`metadata.json`、`run.log`、`slot_trace.npz`、`system_summary.png`。

## 已知限制 / Known limitations

- **确定性**：UE 位置由种子确定且完全可复现；Sionna SYS（CPU）在信道相同时输出逐位一致。
  但 Sionna RT 在 GPU 上的路径求解存在约 0.003 dB 级的信道增益离散漂移，经 OLLA/HARQ 反馈放大后，
  同一 seed 的重复运行网络吞吐率在约 130–139 Mbps 之间（5 次运行，约 ±3.5%）。测试不断言固定数值。
- **计算设备**：本机 PyTorch（cu130）无法使用 GPU（驱动 CUDA 12.9），Sionna SYS 在 CPU 上运行，200 时隙约 40 s。
- 单小区，无小区间干扰；UE 静止，信道在仿真期间不变；UE 单天线全向。
- 开销仅以“每时隙 14 个符号中 12 个承载数据”近似，未建模 SSB/CSI-RS/PDCCH 细节。
- 仅 full buffer 业务；无移动性、无切换、无上行。
- 结果为系统级仿真，不是华为实测数据，不是验收证据。
