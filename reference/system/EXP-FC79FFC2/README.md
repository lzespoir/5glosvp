# System-Level Reference Evidence — EXP-FC79FFC2

| 项 / Item | 值 / Value |
|---|---|
| Experiment ID | `EXP-FC79FFC2` |
| Commit | `fbe2d19` |
| Platform Version | 0.3.0 |
| Scenario | `SYSTEM-DEMO-001` — 多用户下行系统仿真演示 / Multi-UE Downlink System Simulation Demo |
| Backend | `sionna_system` (Sionna Simulation Generated) |
| Sionna Version | 2.1.0 (sionna-rt 2.1.0, torch 2.14.0) |
| BS / Cell / UE | 1 / 1 / 6 |
| Traffic Model | full_buffer · downlink · [A] |
| Scheduler | Proportional Fair SU-MIMO (`sionna.sys.PFSchedulerSUMIMO`, β = 0.9) |
| Link Adaptation | Outer-Loop Link Adaptation (BLER target 0.1, MCS table 1) |
| Seed | 20260927 |
| Simulated Time | 200 slots × 0.5 ms = 0.1 s |
| Compute Device (SYS) | cpu |
| Runtime | RT 0.72 s · SYS 39.98 s · total 40.72 s |
| **Network Throughput** (`NETWORK_THROUGHPUT_V0_1`) | **137.981 Mbps** |
| **Average UE Throughput** (`AVG_UE_THROUGHPUT_V0_1`) | **22.997 Mbps** |
| **P5 UE Throughput** (`P5_UE_THROUGHPUT_V0_1`) | **12.940 Mbps** |
| Independent Verification | **PASS** (38/38 checks) |
| Measured | **NO** |
| Huawei Data | **NO** |
| Acceptance Evidence | **NO** |
| Purpose | System-Level Simulation Validation |

> 当前结果来自系统级仿真，不是华为实测网络数据。
> P5 UE Throughput 尚未确认等同于项目验收口径中的“边缘用户速率”。

## Per-UE Results

| UE | Cell | Position (x, y) [m] | Mean Gain [dB] | Eff. SINR [dB] | Mean MCS | Sched/ACK slots | RE share | Decoded bits | Throughput [Mbps] |
|---|---|---|---|---|---|---|---|---|---|
| UE-001 | CELL-001 | (-342.1, -220.9) | -119.62 | -2.27 | 3.1 | 106/74 | 40.0% | 1,197,064 | **11.971** |
| UE-002 | CELL-001 | (-84.4, 77.8) | -110.08 | 17.50 | 22.9 | 30/26 | 8.4% | 2,245,648 | **22.456** |
| UE-003 | CELL-001 | (338.6, -301.8) | -87.82 | 27.59 | 26.3 | 22/22 | 9.1% | 3,661,064 | **36.611** |
| UE-004 | CELL-001 | (204.1, -167.3) | -105.54 | 9.93 | 15.0 | 46/39 | 16.1% | 2,167,472 | **21.675** |
| UE-005 | CELL-001 | (-243.0, -198.8) | -114.72 | 7.86 | 11.6 | 69/58 | 19.0% | 1,584,952 | **15.850** |
| UE-006 | CELL-001 | (-228.4, 124.6) | -108.61 | 19.52 | 26.1 | 19/18 | 7.5% | 2,941,912 | **29.419** |

UE 吞吐率 = 成功译码比特 / 仿真时长（`UE_THROUGHPUT_V0_1`）；Eff. SINR 与 MCS 为被调度时隙均值。

## Chain

Sionna RT `PathSolver` → CFR → Sionna SYS `PFSchedulerSUMIMO` → `downlink_fair_power_control`
→ RZF precoding + LMMSE post-equalization SINR → `OuterLoopLinkAdaptation` → `PHYAbstraction` (decoded bits / HARQ)
→ platform KPI engine (`src/evaluation/kpi`).

## Files

- `result.json` — canonical `SystemSimulationResult` + KPI results
- `kpi.json` — KPI results with provenance
- `verification.json` — independent recomputation from `slot_trace.npz` (`scripts/verify_system_experiment.py`, does not import the KPI engine)
- `system-summary.png` — network view (BS ▲ / UE ●, no map background) and UE throughput bars

## Determinism

UE positions are fully determined by the seed and Sionna SYS (CPU) is bit-identical for identical channels, but Sionna RT on GPU
shows ~0.003 dB discrete channel-gain drift that OLLA/HARQ amplify; repeated runs of this scenario gave network throughput between
about 130 and 139 Mbps. The numbers above are one real run, not a tuned or averaged value.

## Assumptions

- [A] 业务模型 full buffer：所有 UE 始终有下行数据
- [A] 每时隙 14 个 OFDM 符号中 12 个承载数据（2 个符号为控制/DMRS 开销）
- [A] UE 噪声系数 7 dB，温度 290 K
- [A] UE 静止，信道在仿真期间不变（每时隙复用同一 CFR）
- [A] UE 单天线全向（iso），基站 2×4 TR 38.901 平面阵
- [A] 单小区，无小区间干扰
- [A] 仿真 200 个时隙（0.1 s）

`determinism-repeats.json` — three extra real runs of `SYSTEM-DEMO-001` (per-UE throughput, KPIs, per-UE mean channel gain) showing
that only the RT channel gain differs (≤ 0.003 dB) between runs.

## Browser Smoke Test

Playwright (Chrome, 1920×1080 + 1366×768) against the Vite dev server and the live API. **Console errors: 0.**

| Step | Screenshot |
|---|---|
| Overview → Quick Start | `screenshots/01_overview_quick_start.png` |
| System Simulation page (scenario, network view) | `screenshots/02_system_scenario.png` |
| Run modal → running (real run, 42.0 s) | `screenshots/03_run_modal.png`, `screenshots/04_running.png` |
| Result: KPI cards, UE bar chart, network view | `screenshots/05_result.png`, `screenshots/05_result_full.png` |
| UE table | `screenshots/06_ue_table.png` |
| UE-001 computation chain drawer | `screenshots/07_ue_drawer.png` |
| KPI detail (P5, Network) | `screenshots/08_kpi_detail_p5.png`, `screenshots/09_kpi_detail_network.png` |
| Experiment Center → System tab → reopen (same KPIs) | `screenshots/10_experiment_center_system.png` |
| Result at 1366×768 | `screenshots/11_result_1366.png` |
