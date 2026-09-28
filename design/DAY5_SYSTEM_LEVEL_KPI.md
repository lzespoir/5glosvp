# Day 5 — System-Level KPI & First 5G User Story
# 系统级 KPI 与首个完整 5G 用户故事

> 项目：5G 网络学习优化仿真验证平台
>
> Day 4 冻结基线：
> Commit: e2f9100
>
> Day 4 Reference Optimization:
> OPT-E56D9514
>
> Day 5 阶段目标：
> 从“传播层仿真优化平台”迈入“5G 系统级仿真验证平台”。
>
> 本文档是 Cursor Auto 的直接开发任务书。
> 必须实际修改代码、运行测试、执行真实系统级仿真、完成浏览器验证、保存 Reference Evidence、提交 Git。
>
> 不要只输出设计方案。

---

# 0. Day 5 核心目标

Day 4 已经证明：

Scenario
→ Parameter
→ Optimizer
→ Sionna RT
→ Objective
→ Best Configuration
→ Before / After
→ Evidence

真实优化闭环成立。

Day 5 不继续扩展 Optimization。

Day 5 只解决新的纵向链路：

Network Scenario
网络场景
    ↓
Base Station / Cell
基站 / 小区
    ↓
UE
用户设备
    ↓
Radio / Channel Condition
无线 / 信道条件
    ↓
SINR
    ↓
Link Adaptation
链路自适应
    ↓
Resource Allocation / Scheduling
资源分配 / 调度
    ↓
UE Throughput
用户吞吐率
    ↓
Network-Level KPI
网络级 KPI

Day 5 完成后，平台第一次允许真实展示：

- UE Throughput
- Average UE Throughput
- Network Throughput
- UE Throughput Percentile

而不再全部显示：

Not Available

---

# 1. Day 5 的第一原则：不伪造系统 KPI

禁止使用类似：

throughput = bandwidth * log2(1 + sinr)

然后直接称为：

5G Network Throughput

除非它被明确实现为独立的：

Fast Approximation Backend
快速近似模型

并清楚标记为：

Approximation / Engineering Model

Day 5 主验证链应优先使用：

Sionna RT
+
Sionna SYS

提供的真实系统级能力。

如果当前安装版本/API 导致完整 RT→SYS 链暂时无法工作：

允许实现明确标记的 fallback。

但必须：

1. 不伪装成 Sionna SYS；
2. provenance 中明确 backend；
3. UI 明确显示模型来源；
4. 测试和 Reference Evidence 明确记录。

---

# 2. Day 5 第一用户故事

建立第一个完整用户故事：

“Multi-UE Downlink System Simulation”
“多用户下行系统级仿真”

用户能够：

选择一个多用户场景
    ↓
运行系统级仿真
    ↓
查看 UE
    ↓
查看 Serving Cell
    ↓
查看 SINR
    ↓
查看资源分配 / 调度结果
    ↓
查看 UE Throughput
    ↓
查看 Network Throughput
    ↓
查看 Average UE Throughput
    ↓
查看 P5 UE Throughput
    ↓
点击某个 UE
    ↓
查看该 KPI 的计算链和来源

---

# 3. Day 5 场景规模

第一版保持非常小。

建议：

1 Base Station / Cell

3–10 UEs

Downlink

3.5 GHz

100 MHz

Fixed Seed

Day 5 的目标是：

Correctness
正确性

Traceability
可追溯性

Architecture
架构正确

而不是：

Scale
规模

因此禁止为了展示：

1000 BS

1000 Cells

10000 UE

Day 5 不做规模验收。

---

# 4. 不破坏 Day 4

Day 4：

Commit e2f9100

必须保持可运行。

尤其：

Simulation Experiment

Optimization Run

Grid Search

PROPAGATION_UTILITY_V0_1

OPT-E56D9514 evidence

全部不得因为 Day 5 重构而失效。

运行现有全部 regression tests。

---

# 5. 长期架构原则

平台不得被设计成：

5G Platform
=
Sionna GUI

必须保持：

Platform
    ↓
Canonical Domain Model
    ↓
Simulation Interface
    ↓
Simulation Adapter
    ↓
Specific Simulator

当前：

Specific Simulator
=
Sionna

未来允许：

Sionna

Fast System Model

MATLAB

ns-3

External Simulator

Research Simulator

Measured Data Replay

其他仿真工具或平台

Day 5 不实现这些未来 Backend。

只保证接口不会把未来堵死。

---

# 6. Simulation Backend 分层

不要把所有仿真能力都塞进当前：

SionnaBackend

建议逐渐形成：

PropagationSimulationBackend

SystemSimulationBackend

当前概念：

SionnaRTBackend
    implements
PropagationSimulationBackend

SionnaSystemBackend
    implements
SystemSimulationBackend

如果现有命名修改成本过高：

允许保持 SionnaBackend 名称。

但业务层必须开始区分 capability。

---

# 7. Capability / 能力声明

Backend Descriptor 增加 capability。

例如：

{
  "id": "sionna_system",
  "capabilities": [
    "propagation",
    "system_simulation",
    "ue_metrics",
    "throughput"
  ]
}

不要让前端：

if backend == "sionna"

决定功能。

应该：

if capability contains "throughput"

决定是否能够运行相应系统实验。

---

# 8. 不要现在做插件系统

禁止 Day 5 开发：

Plugin Marketplace

Dynamic Python Plugin Loader

MATLAB Adapter

ns-3 Adapter

Remote Simulator Protocol

Docker Plugin Runtime

Algorithm Marketplace

Universal Simulator SDK

这些属于未来增强。

Day 5 只建立：

正确 interface
+
正确 metadata
+
第一个真实 implementation

---

# 9. Canonical Domain Model

平台必须拥有自己的领域模型。

禁止：

Frontend
→
Sionna Object

也禁止：

Database
→
直接序列化内部 Sionna Python Object

建立平台自己的 canonical models。

---

# 10. BaseStation

建立或完善：

BaseStation

建议字段：

bs_id

name

position

metadata

如果 Cell 已经包含足够信息：

BaseStation 可以保持轻量。

不要过度设计。

---

# 11. Cell

建立：

Cell

至少：

cell_id

bs_id

position

carrier_frequency_hz

bandwidth_hz

tx_power_dbm

metadata

未来可能增加：

antenna

azimuth

tilt

load

但 Day 5 不要求全部实现。

---

# 12. UserEquipment / UE

正式建立：

UserEquipment

至少：

ue_id

position

serving_cell_id

traffic_demand

metadata

仿真结果不要全部混进输入模型。

建议区分：

UserEquipmentConfig

与：

UserEquipmentResult

---

# 13. UE Result

建立：

UserEquipmentResult

至少能够表达：

ue_id

serving_cell_id

sinr

mcs / link_adaptation_state

allocated_resources

throughput

bler / decoding result（如果 Backend 提供）

metadata

其中某字段如果当前 Backend 无法可靠提供：

使用：

null

+
availability reason

不要造值。

---

# 14. Traffic Demand

Day 5 建立最小：

TrafficDemand

至少支持：

full_buffer

或当前 Sionna SYS 最容易稳定实现的业务模式。

Day 5 优先：

Full Buffer Downlink

原因：

先验证无线资源和吞吐率链。

暂时不做：

复杂业务到达过程

视频模型

URLLC

VoIP

泊松业务

全用户业务预测

这些后续增加。

---

# 15. Traffic Model 必须有 provenance

例如：

traffic_model:
  type: full_buffer
  source: assumption

标记：

[A] Assumption

不要把 Full Buffer 称为真实用户业务。

---

# 16. System Scenario

新增或扩展：

SystemScenario

至少：

scenario_id

base_stations

cells

ues

traffic

simulation_config

seed

metadata

Day 5 不强制完全替换现有 ScenarioConfig。

可以通过：

extension

composition

adapter

实现。

优先保持 Day 4 兼容。

---

# 17. System Simulation Result

建立：

SystemSimulationResult

不要强行把所有字段塞进现有：

SimulationResult

推荐：

SimulationResult
    ├── propagation
    └── system

或者：

SystemSimulationResult

作为新的 result type。

核心要求：

类型语义清晰。

---

# 18. System Result 至少包含

experiment_id

scenario_id

backend

seed

ue_results

network_metrics

runtime

provenance

artifacts

warnings

---

# 19. 五层模型

Day 5 代码和文档必须明确五层：

Layer 1 — Scenario

BS
Cell
UE
Traffic

Layer 2 — Propagation

Channel
Path Gain
Radio Condition

Layer 3 — PHY

SINR
Link Adaptation
MCS
BLER / decoding state

Layer 4 — System

Scheduling
Resource Allocation

Layer 5 — KPI

UE Throughput
Average UE Throughput
Network Throughput
Percentile Throughput

---

# 20. 每层责任不要混淆

禁止：

KPI module
→
直接调用 Sionna RT

禁止：

Frontend
→
计算 throughput

禁止：

Scheduler
→
生成假的 SINR

正确方向：

Simulation Backend
    ↓
Canonical Result
    ↓
KPI Engine
    ↓
Frontend

---

# 21. Sionna RT → Sionna SYS

Day 5 优先探索并实现：

Sionna RT
    ↓
Propagation / Channel Information
    ↓
Sionna SYS
    ↓
PHY Abstraction
    ↓
Link Adaptation
    ↓
Scheduling
    ↓
UE Rate / Throughput

Cursor 必须首先阅读：

当前安装 Sionna 版本

现有 Day 4 Backend

当前 Sionna SYS API

官方示例

特别是：

SYS Meets RT

相关官方示例。

禁止凭记忆猜 API。

---

# 22. Spike First

正式编码前先做：

Day 5 System Spike

建立：

scripts/day5_system_spike.py

目标：

在最小场景中证明：

Sionna RT
+
Sionna SYS

能够得到至少一个可用于系统级 KPI 的真实结果。

输出：

reference/day5_spike/

包括：

environment.json

result.json

run.log

README.md

不要先写大量 UI 再发现系统链跑不通。

---

# 23. Day 5 Go / No-Go

如果 4 小时内：

RT → SYS

主链无法稳定工作：

不要无限修 Sionna。

执行 fallback：

FastSystemBackend

但必须明确：

backend = fast_system

model_type = engineering_approximation

measured = false

acceptance_evidence = false

并继续完成平台系统级链路。

同时：

SionnaSystemBackend
=
experimental / unavailable

记录原因。

但第一优先级仍是：

真实 Sionna SYS。

---

# 24. FastSystemBackend 只是备用

如果必须实现：

FastSystemBackend

它的目的只是：

验证平台系统级数据流。

必须版本化模型，例如：

FAST_SYSTEM_MODEL_V0_1

文档中写清：

SINR mapping

spectral efficiency mapping

resource allocation assumptions

throughput formula

limitations

禁止叫：

5G Standard Model

除非有明确标准依据。

---

# 25. KPI Engine

新增：

src/evaluation/kpi/

或符合现有项目结构的位置。

建立：

KPI Definition

KPI Evaluator

KPI Registry

不要把 KPI 计算散落在 API 和 React 中。

---

# 26. KPI Versioning

每个 KPI：

必须：

id

version

name

unit

formula / measurement method

required inputs

source

assumptions

availability

---

# 27. UE Throughput

定义：

UE_THROUGHPUT_V0_1

单位：

Mbps

来源：

System Simulation Result

如果 Sionna SYS 已直接给出符合语义的 rate：

记录它如何转换为 Mbps。

如果需要由：

successfully delivered bits / simulation time

计算：

明确记录公式。

禁止只保存最终数字。

---

# 28. Network Throughput

第一版冻结：

NETWORK_THROUGHPUT_V0_1

定义：

T_network = Σ T_u

即所有 UE throughput 之和。

单位：

Mbps

文档：

docs/kpi/network-throughput-v0.1.md

---

# 29. Average UE Throughput

冻结：

AVG_UE_THROUGHPUT_V0_1

定义：

T_avg = (1 / N) Σ T_u

单位：

Mbps

文档：

docs/kpi/average-ue-throughput-v0.1.md

---

# 30. P5 UE Throughput

冻结：

P5_UE_THROUGHPUT_V0_1

定义：

UE Throughput Distribution 的第 5 百分位数。

必须明确：

percentile calculation method

sample population

是否包含 throughput = 0 的 UE

Day 5 推荐：

包含场景中的全部 active UE。

文档：

docs/kpi/p5-ue-throughput-v0.1.md

---

# 31. P5 不等于验收“边缘用户速率”

UI：

P5 UE Throughput
P5 用户吞吐率

必须显示说明：

“当前为系统级工程评价指标。
尚未确认其与项目验收口径中的‘边缘用户速率’完全等价。”

禁止：

Edge User Rate Acceptance KPI

除非以后得到正式 KPI 定义。

---

# 32. KPI Provenance

每个 KPI Result 至少：

metric_id

version

value

unit

source_experiment

backend

dataset/scenario

seed

calculation_method

measured

assumptions

---

# 33. KPI Availability

继续保留：

available

unavailable_reason

不要为了 Day 5 把所有：

—

都强制变成数字。

例如：

RSRP

如果仍然没有严格定义：

继续 unavailable。

---

# 34. System Experiment

Day 5 建议扩展现有 Experiment：

experiment_type:

propagation
system

默认旧实验：

propagation

新：

system

必须保持旧记录兼容。

---

# 35. Experiment Purpose 与 Type 分开

不要混：

experiment_type
=
optimization_candidate

推荐：

experiment_type:
propagation | system

purpose:
standalone | baseline | optimization_candidate | reference

这是不同维度。

Day 5 只在成本低时实现 purpose。

---

# 36. System Experiment API

至少：

POST /api/v1/system-experiments

GET /api/v1/system-experiments

GET /api/v1/system-experiments/{id}

如果复用现有：

/experiments

也可以。

例如：

POST /experiments

{
  "experiment_type": "system"
}

关键：

API 语义清晰。

不要为了统一而破坏 Day 4。

---

# 37. System Backend Registry

Backend Registry 需要支持：

backend category / capability

例如：

sionna_rt

category:
propagation

sionna_system

category:
system

不要在 API Route 中：

if sionna_system:
    ...

业务层通过 interface 调用。

---

# 38. Simulation Backend Future Compatibility

Day 5 必须留出未来：

FastSystemBackend

MatlabSystemBackend

NS3SystemBackend

ExternalSystemBackend

但不要实现。

代码中不要：

enum Simulator {
    SIONNA
}

写死只有一个实现。

---

# 39. Algorithm Future Compatibility

Day 5 不开发新算法。

但不能破坏：

Optimizer Interface

Optimizer Registry

GridSearchOptimizer

未来算法可能：

自动输出连续参数

输出向量参数

处理约束

拥有算法超参数

远程运行

这些能力 Day 5 不实现。

只确保 Day 5 的 domain model 不要求：

parameter must be list[float]

---

# 40. ParameterDefinition

如果 Day 5 修改参数模型：

建立或预留：

ParameterDefinition

概念字段：

name

type

unit

default

bounds

choices

shape

constraints

editable

source

支持未来：

continuous

integer

discrete

categorical

vector

Day 5 不需要做通用 Parameter UI。

---

# 41. Network Variable 与 Algorithm Hyperparameter 分离

未来：

Network Variable:

tx_power
antenna_tilt
cell_association
resource_allocation

Algorithm Hyperparameter:

learning_rate
iterations
tolerance
population_size

Day 5 数据模型禁止把两者混成：

parameters

一个无语义 dict。

如果当前 Day 4 已经使用 parameters：

不要大重构。

记录 technical debt，并逐步演进。

---

# 42. Day 5 Frontend 核心入口

增加：

System Simulation
系统级仿真

不要把它藏在开发菜单。

新用户应该可以：

首页
↓
系统级仿真
↓
选择 Demo Scenario
↓
Run
↓
查看 System Result

---

# 43. 首页增加“我想做什么”

在不大改视觉设计的前提下：

Overview 增加 Quick Start / 快速开始。

至少：

运行传播仿真

运行系统仿真

运行参数优化

验收验证（Coming Soon）

目的：

让第一次进入系统的人知道下一步。

---

# 44. System Scenario 页面

显示：

Scenario Name

BS / Cell Count

UE Count

Frequency

Bandwidth

Traffic Model

Simulation Backend

Seed

Data Source

---

# 45. Network View

Day 5 不要求复杂 3D。

可以用简单 2D：

BS / Cell
+
UE positions

例如：

▲ BS

● UE

能够让用户看到：

网络里确实有多个 UE。

禁止伪造地图背景。

---

# 46. System Result 页面

页面顶部：

System Experiment
系统级实验

EXP-XXXXXXXX

Backend

Scenario

Status

Seed

Runtime

Source Type

---

# 47. KPI Cards

真实结果：

Network Throughput

Average UE Throughput

P5 UE Throughput

UE Count

所有数字必须来自 API。

禁止 frontend fixture 泄漏到生产模式。

---

# 48. UE Throughput Distribution

ECharts：

X:
UE Throughput

Y:
UE Count / Density

或者：

UE 排名
vs
Throughput

选择最简单清晰的。

不要过度可视化。

---

# 49. UE Table

至少：

UE

Serving Cell

SINR

MCS

Allocated Resource

Throughput

如果某字段不可用：

—

并提供 unavailable reason。

---

# 50. UE Detail

点击 UE：

打开 Drawer / Modal：

UE ID

Position

Serving Cell

SINR

MCS

Resource Allocation

Throughput

Provenance

---

# 51. Computation Chain / 计算链

UE Detail 必须包含：

Computation Chain
计算链

例如：

UE-003
    ↓
Serving Cell
    ↓
Propagation / Channel
    ↓
SINR
    ↓
Link Adaptation
    ↓
Scheduling
    ↓
Allocated Resource
    ↓
Throughput

其中每一步：

有数据则显示真实值。

无数据：

Not Available

禁止前端补算。

---

# 52. KPI Detail

点击：

Network Throughput

弹出：

Metric ID

Version

Definition

Value

Unit

Source Experiment

Simulation Backend

Seed

Assumptions

Measured:
No

Acceptance KPI:
No

---

# 53. Scientific Boundary Banner

System Result 页面必须有：

“当前结果来自系统级仿真，不是华为实测网络数据。”

如果使用 Sionna：

“Sionna Simulation Generated”

如果 fallback：

“Fast Engineering Approximation”

两者必须视觉上可区分。

---

# 54. 不要出现“真实网络性能”

禁止文案：

Real Network Performance

Actual 5G Throughput

Huawei Network Result

除非以后真的有对应数据。

---

# 55. Acceptance Boundary

Day 5 的：

Network Throughput

Average UE Throughput

P5 UE Throughput

属于：

System Simulation KPI

不是最终：

Acceptance KPI

尤其：

P5 != 已确认的 Edge User Rate

必须明确。

---

# 56. System Experiment Artifacts

至少：

config.yaml

result.json

ue_results.json 或 parquet

kpi.json

metadata.json

run.log

如果存在：

system_summary.png

可以保存。

---

# 57. Metadata

至少记录：

platform_version

git_commit

experiment_id

experiment_type

backend

backend_version

scenario

seed

traffic_model

scheduler

link_adaptation

kpi_versions

source_type

measured

created_at

runtime

---

# 58. Provider Version

如果 Sionna：

记录：

Sionna version

如果 RT 和 SYS 使用同一版本：

仍可记录：

sionna_version

如果未来拆开：

provider_versions

---

# 59. Scheduler Provenance

Scheduler 是系统 KPI 的重要来源。

必须记录：

scheduler:
  id:
  name:
  version/config:

不要只显示：

default

而不知道是什么。

---

# 60. Link Adaptation Provenance

同样记录：

link_adaptation:
  id:
  config:
  source:

如果由 Sionna SYS 提供：

明确：

provider = sionna_sys

---

# 61. Assumption Registry

建议建立轻量：

docs/assumptions.md

或者：

metadata.assumptions

Day 5 至少记录：

[A] Full Buffer Traffic

[A] UE positions / generation method

[A] Scenario geometry if synthetic

[A] scheduler configuration if engineering-selected

不要建立复杂数据库。

---

# 62. UE Generation

如果 UE 是程序生成：

必须：

seed

generator

bounds

count

记录。

例如：

ue_generator:
  type: uniform_area
  seed: 20260927

不要：

np.random
然后不保存 seed。

---

# 63. Determinism

同：

Scenario

Seed

Backend Version

Configuration

应尽量产生可重复结果。

如果底层 GPU / Sionna 存在非完全确定性：

README 明确：

determinism limitation

不要假装 bit-exact reproducibility。

---

# 64. Test Fixture

Unit Test 使用：

FakeSystemBackend

输出确定性 UE 数据。

必须：

source_type = test_fixture

不能进入 production evidence。

---

# 65. FakeSystemBackend

用途：

Unit/API/Frontend Tests

可以返回：

UE-001 → deterministic throughput

UE-002 → deterministic throughput

...

用于验证：

KPI Engine

Percentile

UI

API

禁止用于 Reference System Result。

---

# 66. Unit Tests — Domain

至少：

test_system_scenario_model

test_ue_config_model

test_ue_result_model

test_system_result_model

test_backend_capabilities

test_unknown_backend_capability

---

# 67. Unit Tests — KPI

至少：

test_network_throughput_sum

test_average_ue_throughput

test_p5_ue_throughput

test_p5_includes_zero_throughput_ue

test_empty_ue_population

test_kpi_units

test_kpi_version

test_kpi_provenance

test_unavailable_metric

---

# 68. Percentile Test

P5 的 NumPy / Python percentile method：

必须冻结。

不同 percentile interpolation / method：

可能产生不同结果。

文档和代码必须一致。

---

# 69. Unit Tests — Backend

至少：

test_fake_system_backend

test_system_backend_interface

test_system_backend_registry

test_capability_query

test_result_canonicalization

---

# 70. API Tests

至少：

test_list_system_backends

test_create_system_experiment

test_get_system_experiment

test_list_system_experiments

test_system_experiment_not_found

test_invalid_backend

test_backend_without_system_capability

test_failed_system_experiment_persisted

---

# 71. Sionna Integration Test

如果 RT + SYS 主链成功：

建立：

@pytest.mark.integration
@pytest.mark.sionna

最小真实场景：

1 BS

>= 3 UE

验证：

system experiment succeeds

ue_results not empty

throughput finite

network throughput == sum UE throughput

average throughput correct

P5 correct

provenance backend == sionna_system

source != test_fixture

measured == false

---

# 72. Integration Test 不要求 KPI 数值固定

不要测试：

throughput == 37.4921

除非底层确定性已经充分验证。

优先验证：

finite

non-negative

internal consistency

correct count

correct provenance

correct formula relationships

---

# 73. Independent Verification Script

Day 5 必须增加：

scripts/verify_system_experiment.py

输入：

Experiment ID

独立读取：

artifact

UE results

KPI results

重新计算：

Network Throughput

Average UE Throughput

P5 UE Throughput

输出：

PASS / FAIL

注意：

该脚本不要直接调用生产 KPI Evaluator。

否则不算独立复核。

---

# 74. Browser Smoke Test

真实浏览器：

打开首页

查看 Quick Start

进入 System Simulation

选择 Multi-UE Demo

运行真实 System Experiment

打开结果

查看 Network KPI

查看 UE Table

点击 UE

查看 Computation Chain

点击 KPI

查看 KPI Definition / Provenance

返回 Experiment Center

再次打开该实验

Console Errors = 0

---

# 75. Reference Evidence

真实运行完成后：

reference/system/

例如：

reference/system/EXP-XXXXXXXX/

保存：

README.md

result.json

kpi.json

verification.json

system-summary.png

不要提交巨大原始 tensor / channel 文件。

大文件保持 artifacts storage。

---

# 76. Reference README

必须：

Experiment ID

Commit

Scenario

Backend

Sionna Version

BS Count

Cell Count

UE Count

Traffic Model

Scheduler

Seed

Network Throughput

Average UE Throughput

P5 UE Throughput

Measured:
NO

Huawei Data:
NO

Acceptance Evidence:
NO

Purpose:
System-Level Simulation Validation

---

# 77. Day 5 不做 Optimization + Throughput

非常重要：

Day 5 不允许顺手做：

Grid Search
→
Network Throughput Optimization

原因：

先验证：

System Model

KPI

Evidence

下一阶段再合并。

---

# 78. Day 5 不做 Edge User Acceptance KPI

不要实现：

EDGE_USER_RATE_ACCEPTANCE_V1

只实现：

P5_UE_THROUGHPUT_V0_1

并记录：

candidate metric only

pending acceptance definition

---

# 79. Day 5 不做 1000 BS

规模扩展以后单独做：

Scale Benchmark

不要让 Day 5 因规模问题失败。

---

# 80. Day 5 不做 100 Business Scenarios

同理。

先跑通一个：

Multi-UE Downlink Demo

---

# 81. Day 5 不做复杂 Traffic

只：

Full Buffer

未来：

TrafficModel Interface

可以扩展：

Measured Traffic

Synthetic Traffic

Predicted Traffic

Replay Traffic

但现在不实现。

---

# 82. Day 5 不做复杂 Cell Association

第一版：

固定 serving cell

或当前 Sionna 系统链最自然的 association。

如果只有 1 Cell：

所有 UE serving_cell 相同。

Day 6 再进入：

User Association Optimization

---

# 83. Day 5 不做复杂 Resource Optimization

Scheduler 可以真实工作。

但不开发：

PRB Optimization Algorithm

Resource Learning Algorithm

Day 6+ 再做。

---

# 84. Day 5 不做 Authentication

继续不做：

Login

RBAC

User Management

---

# 85. Day 5 不做数据库迁移

继续：

filesystem store

除非现有代码已使用 DB。

不要因为 System Experiment 引入 PostgreSQL。

---

# 86. Day 5 不做 Celery / Redis

继续同步运行。

如果真实 System Experiment 时间较长：

允许：

loading spinner

明确等待。

不要假 progress。

---

# 87. Timeout

如果 Sionna SYS 仿真耗时明显超过当前 timeout：

可以调整合理 timeout。

但必须：

记录 technical debt。

不要 Day 5 引入复杂 distributed task system。

---

# 88. Error Model

增加：

SYSTEM_BACKEND_NOT_FOUND

SYSTEM_CAPABILITY_NOT_SUPPORTED

SYSTEM_SIMULATION_FAILED

INVALID_SYSTEM_SCENARIO

NO_UE_RESULTS

KPI_CALCULATION_FAILED

保持现有 API error 风格。

---

# 89. Frontend API

继续：

single API client

不要页面自己：

axios.get(...)

所有 API 走现有 client abstraction。

---

# 90. TypeScript

继续：

no any

Canonical API types。

Backend 返回：

null

前端不能擅自：

0

代替。

---

# 91. UI 语言

继续：

中文优先

关键专业术语：

中文 + English

例如：

系统级仿真
System Simulation

用户吞吐率
UE Throughput

链路自适应
Link Adaptation

---

# 92. 不要把 UI 做成通信专家才能操作

新用户路径：

首页

“运行系统级仿真”

↓

选择 Demo Scenario

↓

查看场景摘要

↓

Run

↓

Result

不要要求第一次使用的人理解：

Mitsuba

Dr.Jit

TensorFlow internals

Sionna internal class names

---

# 93. Advanced Details

技术细节放：

Advanced / 高级信息

或：

Provenance

而不是占据主页面。

---

# 94. Day 5 Documentation

至少新增：

docs/system/system-model-v0.1.md

docs/kpi/ue-throughput-v0.1.md

docs/kpi/network-throughput-v0.1.md

docs/kpi/average-ue-throughput-v0.1.md

docs/kpi/p5-ue-throughput-v0.1.md

docs/architecture/simulation-provider.md

---

# 95. simulation-provider.md

明确：

Platform
owns canonical model.

Simulator
provides implementation.

当前：

Sionna RT / SYS

未来：

Other Simulator

前端、Experiment、KPI、Evidence 不应依赖具体 simulator object。

---

# 96. README 更新

README 增加：

Current Capabilities

Propagation Simulation
✓

Optimization Loop
✓

System-Level Simulation
✓ after Day 5

Measured Data Validation
Not Yet

Acceptance KPI Validation
Not Yet

---

# 97. Day 5 Definition of Done

全部满足才算完成：

[ ] Day 4 regression PASS

[ ] System Spike 完成

[ ] RT→SYS 可行性得到真实结论

[ ] Canonical BS Model

[ ] Canonical Cell Model

[ ] Canonical UE Model

[ ] TrafficDemand Model

[ ] SystemScenario Model

[ ] SystemSimulationResult

[ ] Backend Capability Model

[ ] SystemSimulationBackend Interface

[ ] SionnaSystemBackend 或明确 fallback

[ ] 不在业务层写死 Sionna

[ ] KPI Registry

[ ] UE_THROUGHPUT_V0_1

[ ] NETWORK_THROUGHPUT_V0_1

[ ] AVG_UE_THROUGHPUT_V0_1

[ ] P5_UE_THROUGHPUT_V0_1

[ ] KPI 文档冻结

[ ] P5 未冒充验收 Edge User Rate

[ ] KPI Provenance

[ ] System Experiment

[ ] System Experiment API

[ ] System Experiment Artifacts

[ ] System Result UI

[ ] Quick Start

[ ] Network / UE View

[ ] KPI Cards

[ ] UE Table

[ ] UE Detail

[ ] Computation Chain

[ ] KPI Detail

[ ] Scientific Boundary Banner

[ ] FakeSystemBackend

[ ] Unit Tests PASS

[ ] API Tests PASS

[ ] Integration Test PASS

[ ] Independent Verification PASS

[ ] Frontend Typecheck PASS

[ ] Frontend Tests PASS

[ ] Frontend Build PASS

[ ] Browser Smoke PASS

[ ] Console Error = 0

[ ] Real System Experiment 完成

[ ] Reference Evidence 保存

[ ] README 更新

[ ] Git Commit

---

# 98. Cursor 最终验收报告

完成后必须输出：

1. Git Commit Hash

2. Changed Files

3. Sionna Version

4. RT→SYS Spike 结论

5. System Backend ID

6. Backend Capabilities

7. Scenario ID

8. BS Count

9. Cell Count

10. UE Count

11. UE Generation Method

12. Seed

13. Traffic Model

14. Scheduler

15. Link Adaptation

16. UE Throughput Definition

17. Network Throughput Definition

18. Average UE Throughput Definition

19. P5 Definition

20. Real System Experiment ID

21. Per-UE Results

22. Network Throughput

23. Average UE Throughput

24. P5 UE Throughput

25. Independent Verification Result

26. Unit Test Result

27. API Test Result

28. Sionna Integration Test Result

29. Frontend Test Result

30. Browser Smoke Result

31. Console Error Count

32. Reference Evidence Path

33. Screenshot Paths

34. Provenance

35. Assumptions

36. Known Limitations

37. Day 4 Regression Result

38. Day 6 Ready: YES / NO

---

# 99. Cursor 执行顺序

A. git pull

B. 确认 HEAD 基于 e2f9100

C. 跑 Day 4 全部 regression

D. 检查当前 Sionna version

E. 阅读官方 Sionna SYS / RT→SYS 示例

F. 编写 day5_system_spike.py

G. 真实运行 Spike

H. 根据真实 API 确定 SionnaSystemBackend

I. 建 Canonical System Models

J. 建 SystemSimulationBackend

K. 建 Backend Capability

L. 写 FakeSystemBackend

M. 写 Domain Unit Tests

N. 实现 SionnaSystemBackend

O. 写 Sionna Integration Test

P. 冻结 KPI Definitions

Q. 实现 KPI Registry / Evaluators

R. 写 KPI Unit Tests

S. 实现 System Experiment Service / Store / API

T. API Tests

U. Independent Verification Script

V. 运行真实 System Experiment

W. 独立复核 KPI

X. 开发 Quick Start

Y. 开发 System Simulation 页面

Z. 开发 System Result

AA. UE Table

AB. UE Detail

AC. Computation Chain

AD. KPI Detail

AE. Scientific Boundary

AF. Frontend Tests

AG. Typecheck

AH. Build

AI. 启动真实 Backend / Frontend

AJ. Browser Smoke

AK. 从浏览器运行真实 System Experiment

AL. 检查所有 KPI / UE / Provenance

AM. Console Error 检查

AN. 保存 Reference Evidence

AO. README / docs

AP. git diff review

AQ. regression

AR. commit

AS. push

AT. 输出最终验收报告

---

# 100. Go / No-Go 特别规则

不要为了完成 Day 5：

伪造 Sionna SYS 输出。

如果 RT→SYS 不工作：

记录真实失败原因。

然后选择：

FastSystemBackend

完成平台系统链。

但：

FastSystemBackend
!=
SionnaSystemBackend

UI、metadata、evidence 必须明确区分。

---

# 101. Future Extension Contract

Day 5 完成时，只要求证明未来可以自然扩展：

Simulation Provider:
Sionna → Others

Optimizer:
Grid Search → Research Algorithms

Parameter Space:
Discrete List → Continuous / Integer / Categorical / Vector

Traffic:
Full Buffer → Synthetic / Predicted / Measured

Dataset:
Simulation → Huawei Measured Data

不要实现这些未来功能。

只避免当前设计阻塞它们。

---

# 102. Day 5 成功后的平台能力

Day 5 前：

Scenario
→
Propagation
→
SINR
→
Optimization

Day 5 后：

Scenario
→
BS / Cell / UE
→
Propagation
→
PHY
→
Scheduling
→
Throughput
→
System KPI

此时平台第一次具备：

“5G 系统级性能仿真”

的真实基础。

---

# 103. Day 6 Preview — 不要实现

Day 6 才把：

Day 4 Optimization Loop

与：

Day 5 System-Level KPI

合并。

形成：

Network Parameters
        ↓
Optimizer
        ↓
System Simulation
        ↓
UE Throughput
        ↓
Network Throughput
        ↓
P5 Throughput
        ↓
Objective
        ↓
Best Configuration

并开始实现第一个真正的：

5G Network Optimization Case

候选优先：

User Association / Load Balancing

或者：

Resource Allocation

具体选择 Day 5 完成后再决定。

不要现在开发。

---

# 104. 最终执行指令

现在执行 Day 5。

不要开发新 Optimization Algorithm。

不要调整 Day 4 Objective。

不要为了漂亮结果调 seed。

不要伪造 Throughput。

不要把 P5 叫 Edge User Acceptance KPI。

不要把 Sionna 写死进平台业务层。

不要开发万能插件框架。

不要开发 1000 BS。

不要开发 100 Business Scenarios。

只完成：

BS / Cell / UE
      ↓
Propagation
      ↓
PHY
      ↓
Scheduling
      ↓
UE Throughput
      ↓
Network KPI
      ↓
Evidence

这一条真实、可解释、可追溯的系统级链路。

完成后：

Tests
↓
Real System Experiment
↓
Independent Verification
↓
Browser Validation
↓
Reference Evidence
↓
Git Commit
↓
Final Acceptance Report

然后停止。

# END OF DAY 5