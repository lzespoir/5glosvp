"""
冻结的 KPI 定义 V0.1 / Frozen KPI definitions V0.1.

详见 docs/kpi/*.md；代码与文档必须一致。
"""

from __future__ import annotations

from .models import KpiDefinition, KpiScope

UE_THROUGHPUT_V0_1 = "UE_THROUGHPUT_V0_1"
NETWORK_THROUGHPUT_V0_1 = "NETWORK_THROUGHPUT_V0_1"
AVG_UE_THROUGHPUT_V0_1 = "AVG_UE_THROUGHPUT_V0_1"
P5_UE_THROUGHPUT_V0_1 = "P5_UE_THROUGHPUT_V0_1"

MBPS = "Mbps"
BITS_PER_MEGABIT = 1e6
P5_PERCENTILE = 5.0
# NumPy percentile method（Hyndman & Fan type 7，线性插值）；改变 method 必须发布新版本
P5_PERCENTILE_METHOD = "linear"

FULL_BUFFER_ASSUMPTION = "[A] Full Buffer 下行业务（所有 UE 始终有数据待发）"
SYSTEM_SIMULATION_SOURCE = "System Simulation Result（系统级仿真结果中的成功译码比特数）"

UE_THROUGHPUT = KpiDefinition(
    id=UE_THROUGHPUT_V0_1,
    version="0.1",
    name_zh="用户吞吐率",
    name_en="UE Throughput",
    unit=MBPS,
    scope=KpiScope.UE,
    formula="T_u = B_u / T_sim / 10^6",
    measurement_method=(
        "B_u：仿真时长内 UE u 成功译码（HARQ ACK）的比特总数；"
        "T_sim：仿真时长 = 时隙数 × 时隙长度。"
    ),
    required_inputs=["decoded_bits", "simulated_duration_s"],
    source=SYSTEM_SIMULATION_SOURCE,
    assumptions=[FULL_BUFFER_ASSUMPTION],
    doc="docs/kpi/ue-throughput-v0.1.md",
)

NETWORK_THROUGHPUT = KpiDefinition(
    id=NETWORK_THROUGHPUT_V0_1,
    version="0.1",
    name_zh="网络吞吐率",
    name_en="Network Throughput",
    unit=MBPS,
    scope=KpiScope.NETWORK,
    formula="T_network = Σ_u T_u",
    measurement_method="场景中全部 active UE 的 UE_THROUGHPUT_V0_1 之和。",
    required_inputs=[UE_THROUGHPUT_V0_1],
    source=SYSTEM_SIMULATION_SOURCE,
    assumptions=[FULL_BUFFER_ASSUMPTION],
    doc="docs/kpi/network-throughput-v0.1.md",
)

AVG_UE_THROUGHPUT = KpiDefinition(
    id=AVG_UE_THROUGHPUT_V0_1,
    version="0.1",
    name_zh="平均用户吞吐率",
    name_en="Average UE Throughput",
    unit=MBPS,
    scope=KpiScope.NETWORK,
    formula="T_avg = (1 / N) Σ_u T_u",
    measurement_method="N 为场景中全部 active UE 数（包含吞吐率为 0 的 UE）。",
    required_inputs=[UE_THROUGHPUT_V0_1],
    source=SYSTEM_SIMULATION_SOURCE,
    assumptions=[FULL_BUFFER_ASSUMPTION],
    doc="docs/kpi/average-ue-throughput-v0.1.md",
)

P5_UE_THROUGHPUT = KpiDefinition(
    id=P5_UE_THROUGHPUT_V0_1,
    version="0.1",
    name_zh="P5 用户吞吐率",
    name_en="P5 UE Throughput",
    unit=MBPS,
    scope=KpiScope.NETWORK,
    formula="T_P5 = percentile({T_u}, 5, method='linear')",
    measurement_method=(
        "样本：场景中全部 active UE 的 UE_THROUGHPUT_V0_1（包含吞吐率为 0 的 UE）；"
        "NumPy percentile，method='linear'（Hyndman & Fan type 7 线性插值）。"
    ),
    required_inputs=[UE_THROUGHPUT_V0_1],
    source=SYSTEM_SIMULATION_SOURCE,
    assumptions=[FULL_BUFFER_ASSUMPTION],
    note_zh="当前为系统级工程评价指标。尚未确认其与项目验收口径中的“边缘用户速率”完全等价。",
    doc="docs/kpi/p5-ue-throughput-v0.1.md",
)

ALL_DEFINITIONS = (UE_THROUGHPUT, NETWORK_THROUGHPUT, AVG_UE_THROUGHPUT, P5_UE_THROUGHPUT)
