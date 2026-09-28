# Day 5 System Spike — Sionna RT → Sionna SYS

**结论 / Conclusion: GO** — 真实的 Sionna RT → Sionna SYS 系统级链路可以在本机运行，
无需 FastSystemBackend 回退。

| 项 | 值 |
|---|---|
| 脚本 | `scripts/day5_system_spike.py`（一次性探针，允许直接 import Sionna） |
| 环境 | Python 3.11.16 · Sionna 2.1.0 · sionna-rt 2.1.0 · Mitsuba 3.9.1（`cuda_ad_mono_polarized`）· Dr.Jit 1.5.0 · PyTorch 2.14.0+cu130 |
| 计算设备 | RT：GPU（Dr.Jit CUDA）；SYS：**CPU**（PyTorch cu130 与驱动 CUDA 12.9 不兼容，`torch.cuda.is_available() = False`） |
| 场景 | etoile，1 BS（[-150.3, 21.63, 42.5]，44 dBm，2×4 TR 38.901），6 UE，3.5 GHz，100 MHz（30 kHz × 273 PRB），200 时隙 |
| UE 生成 | seed 20260927 均匀撒 60 个候选，保留前 6 个有传播路径的：候选索引 [0, 1, 3, 12, 19, 21] |
| 耗时 | RT ≈ 1.0 s · SYS ≈ 41 s · 总计 ≈ 42.5 s |
| 文件 | `environment.json`、`result.json`、`run.log` |

## 链路 / Chain（官方教程 `tutorials/sys/SYS_Meets_RT`，按 2.1.0 API）

`PathSolver` → `paths.cfr(out_type="numpy")` → `PFSchedulerSUMIMO` → `downlink_fair_power_control`
→ `RZFPrecodedChannel` + `LMMSEPostEqualizationSINR` → `OuterLoopLinkAdaptation` → `PHYAbstraction`。
UE 吞吐率 = Σ 成功译码比特 / 仿真时长（不是 Shannon 公式）。

## 结果 / Result（两次运行）

| 运行 | 网络吞吐率 | 平均 UE | P5 UE |
|---|---|---|---|
| Run 1 | ≈ 131.29 Mbps | ≈ 21.88 Mbps | ≈ 12.55 Mbps |
| Run 2（`result.json`） | 130.42 Mbps | 21.74 Mbps | 12.02 Mbps |

每时隙分配 RE 总数 = 39 312 = 12 符号 × 3276 子载波（资源全部分配，自洽）。

## 确定性发现 / Determinism finding

- UE 候选位置由种子决定，逐位一致。
- 相同信道输入下 Sionna SYS（CPU）输出逐位一致（平台服务后续重复运行得到与 Run 2 完全相同的 130.41744 Mbps）。
- 非确定性来源是 **Sionna RT 在 GPU 上的路径求解**：个别 UE 的平均信道增益在少数离散值之间漂移（约 0.003 dB），
  经 OLLA / HARQ 反馈放大为单 UE 数个百分点的吞吐率差异。平台 5 次运行网络吞吐率范围约 130.4–139.4 Mbps。
- 处理方式：如实记录，不调种子；集成测试不断言固定数值。

## 科学边界 / Scientific boundary

Measured: **NO** · Huawei Data: **NO** · Acceptance Evidence: **NO**。仅用于技术可行性判断。

## 已处理的环境问题

- `paths.cfr(out_type="torch")` 走 DLPack 需要 CUDA 版 torch → 改用 `out_type="numpy"` 再 `torch.from_numpy`。
- SYS 张量在 CPU 上运行；RT 仍使用 GPU。
