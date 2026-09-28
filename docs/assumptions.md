# 假设清单 / Assumptions Register

标签：`[A]` Assumption（假设）· `[S]` Simulation（仿真生成）· `[M]` Measured（实测，当前没有）。
当前平台**没有任何实测或华为数据**。

## 传播层（Day 1–4）

| ID | 假设 | 用于 |
|---|---|---|
| A-P1 | 场景为 Sionna 内置 `etoile`，材料为场景默认值 | 全部 |
| A-P2 | SINR 覆盖阈值 τ = 0 dB | PROPAGATION_UTILITY_V0_1 |
| A-P3 | 功率代价权重 λ = 0.10 | PROPAGATION_UTILITY_V0_1 |

## 系统级（Day 5，`SYSTEM-DEMO-001`）

| ID | 假设 | 值 |
|---|---|---|
| A-S1 | 业务模型 | Full buffer 下行 |
| A-S2 | 数据符号 | 每时隙 14 个 OFDM 符号中 12 个承载数据（2 个符号为控制/DMRS 开销） |
| A-S3 | UE 噪声系数 / 温度 | 7 dB / 290 K |
| A-S4 | UE 移动性 | 静止；仿真期间每时隙复用同一 CFR |
| A-S5 | 天线 | BS 2×4 TR 38.901 平面阵（V 极化）；UE 单天线全向 |
| A-S6 | 干扰 | 单小区，无小区间干扰 |
| A-S7 | 仿真时长 | 200 时隙 × 0.5 ms = 0.1 s |
| A-S8 | UE 位置 | 850 m × 670 m 区域内均匀撒点（seed 20260927），保留前 6 个存在传播路径的位置 |
| A-S9 | 调度 / 链路自适应 / 功率 | PF（β 0.9）/ OLLA（BLER 目标 0.1，MCS 表 1）/ 下行公平功率控制（保证功率比 0.5） |
| A-S10 | 带宽 | 100 MHz 信道，30 kHz SCS × 273 PRB（占用 98.28 MHz） |
| A-S11 | P5 口径 | 线性插值百分位，样本包含零吞吐率 UE；**不等同于验收口径的边缘用户速率** |
