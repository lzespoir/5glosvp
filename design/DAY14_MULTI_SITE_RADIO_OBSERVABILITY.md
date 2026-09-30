# Day 14 --- Multi-site Radio Observability Foundation

**多站无线可观测性 + UE Twin 主区/邻区无线视图 + 验收链路对齐**

-   **Post-Rebuild Base HEAD:**
    `21d58f0dceed485fff26a69392e2928ebd26c60a`
-   **Prerequisite:** Day 13 / Day 13.1 已冻结；A-Matrix
    仅作为归一化的相对多波束方向响应使用
-   **Day 14 类型:** 平台工程 / 无线观测底座 / 多站场景能力
-   **不是:** 新算法研究、绝对无线校准、完整 Handover、1000
    小区性能冲刺、最终 KPI 验收
-   **默认 UI:** 中文优先
-   **核心原则:** 可追溯、可解释、可复现、科学边界明确，不制造"真实
    RSRP/SINR"结论

------------------------------------------------------------------------

## 0. Day 14 开工前的整体架构复核

### 0.1 项目最终目标没有改变

平台仍然定位为：

> **5G 网络学习优化仿真验证平台**

平台的职责不是替代研究人员发明算法，也不是把某个优化算法包装成项目本体，而是为三类网络优化问题提供统一的：

1.  场景定义与组合；
2.  模型与真实/半真实数据接入；
3.  算法接入；
4.  实验执行；
5.  KPI 计算；
6.  多算法/多配置对比；
7.  可视化；
8.  Evidence / Verification；
9.  验收追溯。

三类核心优化问题保持：

-   **网络结构参数优化**
-   **用户接入参数优化**
-   **系统资源参数优化**

Day 14 不改变这个主轴。

------------------------------------------------------------------------

## 0.2 当前平台总体链路

当前应继续沿用：

``` text
Scenario Center
    ↓
Scenario Definition / Scenario Instance
    ↓
Model / Dataset / Radio / Traffic Context
    ↓
Experiment Workspace
    ↓
Algorithm / Optimizer
    ↓
Execution Manager
    ↓
Problem Evaluation Adapter
    ↓
KPI / Comparison
    ↓
Evidence / Verification
    ↓
Acceptance Center
```

Day 14 在其中增加的不是新的平行系统，而是补齐：

``` text
Scenario Instance
    ↓
UE Twin + Cell/AAU
    ↓
Radio Observation
    ↓
Serving / Neighbor Radio Context
    ↓
Problem Evaluation / Visualization / KPI
```

因此 Day 14 必须是现有架构的**纵向补全**，禁止另建一套孤立的"无线仿真
Demo"。

------------------------------------------------------------------------

## 0.3 与任务要求的方向一致性

当前路线没有偏离项目任务。

平台最终仍需支撑：

-   不同业务场景下的网络参数智能调优；
-   大规模基站/小区网络；
-   三类参数优化；
-   系统级仿真；
-   可视分析；
-   网络性能模型；
-   实测数据验证；
-   最终 KPI 与验收证据。

"百余种不同业务场景"应由 Scenario System
的**语义有效场景定义**支撑，而不是通过随机 seed 或算法参数膨胀数量。

Day 14 的多站无线观测能力是 Scenario → UE → Radio → Function → KPI
链路中的基础能力，后续用户接入、Handover、流量、网络结构参数优化都需要它。

------------------------------------------------------------------------

## 0.4 当前路线中必须继续保持的科学边界

### 已经允许

``` text
A-Matrix
→ normalized relative beam response
→ UE-AAU geometry
→ per-beam relative response
→ multi-cell radio observation
→ serving/neighbor context
```

### 当前禁止直接声称

``` text
A-Matrix normalized value
= calibrated absolute antenna gain
= measured RSRP
= measured SINR
```

Day 14 可以建立**仿真无线观测量**，但必须把来源和 calibration status
明确写入 provenance。

------------------------------------------------------------------------

# 1. Day 14 核心目标

Day 14 建立统一的 **Radio Observation Contract V0.1**。

实现：

``` text
Multi-site / Multi-cell Scenario
        ↓
Cell / AAU Radio Configuration
        ↓
UE Twin Geometry
        ↓
A-Matrix Relative Beam Response
        ↓
Propagation Backend
        ↓
Received-Power Components
        ↓
Interference Components
        ↓
Radio Observation
        ↓
Serving / Neighbor Context
        ↓
Frontend Radio View + Evidence
```

Day 14 完成后，平台应该能够回答：

> 对于一个确定的 Scenario Instance 和 UE，当前有哪些候选 Cell/AAU？\
> UE 与每个 Cell/AAU 的几何关系是什么？\
> 当前使用哪个 A-Matrix profile / beam？\
> 相对方向响应是多少？\
> propagation backend 给出了什么传播结果？\
> received-power / interference / SINR 是如何组成的？\
> 当前 serving / neighbor 是什么？\
> 哪些值是 calibrated，哪些只是 simulation-derived？

而不是只给一个最终 SINR 数字。

------------------------------------------------------------------------

# 2. Day 14 不做什么

以下内容明确不属于 Day 14：

-   不实现完整 Handover 状态机；
-   不实现 A3/A5 等正式移动性策略；
-   不实现负载均衡算法；
-   不实现新的用户接入优化算法；
-   不实现新的学习优化算法；
-   不做算法优劣排名；
-   不做波束空间流量预测模型；
-   不接入尚未拿到的真实流量模型；
-   不做 1000+ Cell 大规模性能验收；
-   不跑大量 Sionna RT 场景；
-   不宣称完成最终吞吐率 +10%；
-   不宣称完成边缘用户速率 +20%；
-   不宣称完成优化速度 +100%；
-   不宣称完成华为实测数据最终验收；
-   不把 normalized A-Matrix 标成 dBi；
-   不把 simulation-derived received power 标成 measured RSRP；
-   不修改 Day 8 / Day 13 历史 Evidence。

------------------------------------------------------------------------

# 3. Radio Observation Contract V0.1

建议新增领域对象：

``` text
RadioObservation
RadioObservationSet
CellRadioObservation
RadioMetricValue
RadioProvenance
CalibrationStatus
PropagationObservation
InterferenceObservation
```

------------------------------------------------------------------------

## 3.1 RadioMetricValue

建议字段：

``` text
metric_name
value
unit
semantic_type
source_type
calibration_status
model_version
artifact_id
artifact_hash
notes
```

`semantic_type` 至少区分：

``` text
GEOMETRY
RELATIVE_ANTENNA_RESPONSE
SIMULATION_DERIVED
CALIBRATED_SIMULATION
MEASURED
DERIVED_KPI
```

Day 14 主要允许前三类。

------------------------------------------------------------------------

## 3.2 CalibrationStatus

至少支持：

``` text
RELATIVE_ONLY
UNCALIBRATED_SIMULATION
CALIBRATED_SIMULATION
MEASURED
UNKNOWN
```

Day 14 禁止为了 UI 好看把：

``` text
UNCALIBRATED_SIMULATION
```

显示成：

``` text
MEASURED
```

------------------------------------------------------------------------

# 4. 多站 / 多小区 Radio Context

Day 14 必须正式支持：

``` text
1 UE
→ 1 serving cell
→ 0..N neighbor cells
```

并允许：

``` text
1 Scenario
→ N sites
→ N cells
→ N AAUs
→ N antenna profiles
→ N beam profiles
→ M UEs
```

这里的 N/M 不应该写死成 Day 8 的 3 Cell / 12 UE。

Day 8 可以作为 regression fixture，但不能成为领域模型限制。

------------------------------------------------------------------------

# 5. Cell / AAU Radio Configuration

建议定义：

``` text
CellRadioConfig
```

至少包含：

``` text
cell_id
site_id
aau_id
position
coordinate_system
tx_power
tx_power_unit
carrier_frequency
bandwidth
antenna_profile_id
a_matrix_artifact_id
beam_configuration
propagation_backend
radio_config_version
provenance
```

其中：

-   `tx_power`
-   `carrier_frequency`
-   `bandwidth`

如果未知，必须允许 `UNKNOWN / NOT_PROVIDED`。

禁止偷偷使用无法追溯的默认值然后输出"真实 RSRP"。

------------------------------------------------------------------------

# 6. UE Twin 扩展

Day 13 已有 UE Twin V0.1。

Day 14 在保持兼容的前提下扩展：

``` text
UETwin
├── identity
├── position
├── orientation
├── traffic_profile
├── mobility_state
├── serving_cell_id
├── neighbor_cell_ids
├── radio_geometry
├── beam_observations
└── radio_observations
```

新增：

``` text
radio_observations: RadioObservationSet
```

不要复制一份新的 UE model。

------------------------------------------------------------------------

# 7. Radio Geometry

继续复用 Day 13 已冻结的 geometry contract：

``` text
AAU position + UE position
→ distance_3d
→ azimuth_deg
→ elevation_deg
```

Day 14 不允许重新实现另一套角度系统。

必须继续使用 Day 13 的：

-   coordinate convention；
-   azimuth normalization；
-   elevation convention；
-   periodic nearest-grid；
-   half-step tie policy；
-   angular-grid version。

------------------------------------------------------------------------

# 8. A-Matrix Integration

Day 14 继续使用：

``` text
raw NPY
→ validated 91×72 grid
→ peak normalized response
→ nearest-grid lookup
→ per-beam relative response
```

A-Matrix 的 Day 14 角色是：

> **Relative antenna directional response**

不是：

> Absolute calibrated antenna gain.

------------------------------------------------------------------------

## 8.1 Day 14 必须继承的 A-Matrix provenance

当 A-Matrix 参与 Radio Observation 时必须记录：

``` text
a_matrix_artifact_id
source_file_hash
antenna_profile_id
beam_family
beam_id
entry_key
normalization_policy
angular_grid_version
lookup_method
coordinate_convention
```

------------------------------------------------------------------------

# 9. Propagation Backend Contract

新增或正式化：

``` text
PropagationBackend
```

接口概念：

``` text
evaluate_link(
    scenario,
    cell,
    ue,
    antenna_response,
    radio_config
) -> PropagationObservation
```

至少允许：

``` text
FastPropagationBackend
SionnaRTPropagationBackend
FutureMeasuredPropagationAdapter
```

Day 14 不要求三个全部实现完整。

------------------------------------------------------------------------

## 9.1 Fast backend

Day 14 建议优先建立可测试的 Fast backend。

用途：

-   多 Cell 快速计算；
-   Scenario Center；
-   Radio View；
-   单元测试；
-   后续 100+ Scenario batch；
-   后续大规模 backend。

它可以使用明确、版本化、可解释的 propagation abstraction。

但必须记录：

``` text
backend_name
backend_version
model_name
model_version
input_parameters
```

禁止出现：

``` text
path_loss = magic_number
```

而没有 provenance。

------------------------------------------------------------------------

## 9.2 Sionna backend

Day 14 只需要保证架构能够：

``` text
RadioObservationService
→ PropagationBackend
→ SionnaRTPropagationBackend
```

不要求大规模 Sionna RT rerun。

如果已有代表性 Sionna artifact，可读取并显示。

不得为了 Day 14 演示重新制造 Day 8 historical artifact。

------------------------------------------------------------------------

# 10. Received-Power Decomposition

Day 14 不应该直接从一个公式吐出"RSRP"。

建议建立：

``` text
ReceivedPowerComponents
```

例如：

``` text
tx_power_component
antenna_relative_response
propagation_loss
additional_loss
result
```

其中每个 component 都必须有：

``` text
value
unit
source
status
```

如果 absolute calibration 不完整：

``` text
result.calibration_status = UNCALIBRATED_SIMULATION
```

------------------------------------------------------------------------

# 11. Radio Metric 命名规范

Day 14 必须避免科学含义混乱。

### 推荐 UI

如果当前链路未校准：

``` text
仿真接收功率
Simulation-derived Received Power

仿真 SINR
Simulation-derived SINR

相对波束响应
Relative Beam Response
```

不要直接写：

``` text
真实 RSRP
实测 SINR
```

------------------------------------------------------------------------

## 11.1 RSRP 字段规则

只有当模型明确实现了符合当前项目定义的 RSRP
计算，并且输入单位/功率语义完整时，才允许：

``` text
metric_name = RSRP
```

否则使用：

``` text
SIM_RECEIVED_POWER
```

或同等明确名称。

------------------------------------------------------------------------

# 12. Interference Observation

Day 14 必须让干扰可解释。

建议：

``` text
InterferenceObservation
```

包含：

``` text
serving_cell_id
interfering_cell_ids
per_interferer_component
aggregate_interference
noise_component
sinr
calibration_status
backend
provenance
```

前端应允许展开：

``` text
SINR
 ↓
Serving Signal
Interference Cell A
Interference Cell B
...
Noise
```

而不是只有一个不可解释数字。

------------------------------------------------------------------------

# 13. Serving / Neighbor Context

Day 14 建立的是：

``` text
ServingNeighborContext
```

不是 Handover decision engine。

至少包含：

``` text
serving_cell_id
neighbor_cell_ids
ranking_metric
ranking_source
observation_timestamp_or_step
selection_policy
selection_status
```

------------------------------------------------------------------------

## 13.1 Serving Cell 来源必须明确

可能来源：

``` text
SCENARIO_DEFINED
EXPERIMENT_DEFINED
STRONGEST_SIMULATED_SIGNAL
EXTERNAL_DATA
ALGORITHM_OUTPUT
```

不能默认为 strongest signal 后又说它是"真实网络主区"。

------------------------------------------------------------------------

# 14. Neighbor Ranking

Day 14 可以提供：

``` text
neighbor ranking
```

但必须明确 ranking metric，例如：

``` text
distance
relative_beam_response
simulation_received_power
simulation_sinr
```

禁止使用模糊的：

``` text
best_cell
```

除非定义了 best 的指标。

------------------------------------------------------------------------

# 15. Scenario System Integration

Day 14 必须直接消费：

``` text
ScenarioDefinition
ScenarioInstance
```

而不是自己建立：

``` text
RadioDemoScenario
```

------------------------------------------------------------------------

## 15.1 ScenarioInstance Radio Binding

建议增加：

``` text
radio_context
```

包含：

``` text
site_ids
cell_ids
aau_ids
antenna_profile_ids
propagation_backend
radio_config_version
calibration_status
```

------------------------------------------------------------------------

# 16. Scenario Scientific Identity

如果 Radio Observation 参与实验结果，Experiment scientific identity
必须增加/确认：

``` text
radio_model_id
radio_model_version
propagation_backend
propagation_backend_version
radio_config_hash
a_matrix_artifact_id
a_matrix_hash
antenna_profile_id
normalization_policy
angular_grid_version
lookup_method
calibration_status
```

------------------------------------------------------------------------

# 17. Comparison Identity

Comparison 必须判断：

``` text
same radio context
different radio context
insufficient radio identity
```

以下任意关键项不同，不能静默认为 same：

``` text
propagation backend
radio model version
A-Matrix artifact
antenna profile
normalization
radio config
calibration status
```

继续保持：

> **missing != equal**

------------------------------------------------------------------------

# 18. Radio Observation Service

建议：

``` text
src/radio/
    models.py
    service.py
    propagation.py
    interference.py
    identity.py
    api.py
    verifier.py
```

如果现有项目已有合适目录，应按现有风格扩展，不为了满足本 MD 强行搬目录。

------------------------------------------------------------------------

## 18.1 Service 输入

``` text
scenario_instance_id
ue_id
optional cell subset
optional backend override
```

------------------------------------------------------------------------

## 18.2 Service 输出

``` text
RadioObservationSet
```

至少包含：

``` text
ue
serving cell
neighbors
per-cell geometry
per-cell beam response
propagation observation
received-power observation
interference contribution
SINR status/value
calibration status
scientific identity
provenance
```

------------------------------------------------------------------------

# 19. API

建议 API：

``` text
GET /api/radio/scenarios/{scenario_id}/ues/{ue_id}/observations
GET /api/radio/scenarios/{scenario_id}/ues/{ue_id}/cells
GET /api/radio/scenarios/{scenario_id}/ues/{ue_id}/serving-neighbor
GET /api/radio/scenarios/{scenario_id}/ues/{ue_id}/interference
GET /api/radio/scenarios/{scenario_id}/radio-context
```

如已有 REST 命名规范，以项目现有规范为准。

------------------------------------------------------------------------

# 20. 前端：Radio View

Day 14 必须做真实可用的前端，不接受只有 API。

建议入口：

``` text
场景中心
→ 场景详情
→ UE Twin
→ 无线观测
```

也可以：

``` text
UE Twin Viewer
→ Radio View
```

------------------------------------------------------------------------

# 21. Radio View 页面布局

建议至少包含四块。

### A. UE 当前状态

显示：

``` text
UE ID
位置
Serving Cell
Neighbor Count
Traffic Profile
Mobility State
Radio Backend
Calibration Status
```

------------------------------------------------------------------------

### B. Multi-cell Radio Table

列：

``` text
Cell
Role
Distance
Azimuth
Elevation
Beam
Relative Beam Response
Simulation Received Power
Interference Role
SINR Contribution
Status
```

单位必须显示。

未知值显示：

``` text
未知
未提供
未校准
不适用
```

禁止填 0 冒充数据。

------------------------------------------------------------------------

### C. Serving / Neighbor Visualization

最少支持 2D：

``` text
Site / Cell
UE
Serving link
Neighbor links
```

Day 14 不要求复杂 3D。

------------------------------------------------------------------------

### D. Radio Explanation Panel

点击 Cell 后显示：

``` text
Geometry
A-Matrix
Propagation
Received Power Components
Interference
Calibration
Provenance
```

目标是让老师点击一个 UE 后能看懂：

> 为什么这个 Cell 是主区/邻区，以及这个无线指标是怎么来的。

------------------------------------------------------------------------

# 22. A-Matrix Beam Explorer 联动

Day 13 的 Beam Explorer 不重做。

Day 14 从 Radio View 点击：

``` text
Beam ID
```

应能进入/展开：

``` text
A-Matrix Beam Explorer
```

并显示当前 UE 方向：

``` text
azimuth
elevation
nearest-grid location
relative response
```

------------------------------------------------------------------------

# 23. SINR / RSRP 展示原则

这是 Day 14 的重点验收规则。

页面顶部必须有 calibration badge，例如：

``` text
相对方向图
仿真无线量
已校准仿真
实测数据
```

当前 Day 14 默认应是：

``` text
相对方向图 + 仿真无线量
```

除非确实接入了 calibrated artifact。

------------------------------------------------------------------------

# 24. Acceptance Center 映射

Day 14 不直接宣布完成任务书 KPI。

但应增加 Traceability：

``` text
任务要求
→ Platform Capability
→ Scenario
→ Radio Observation
→ Experiment
→ KPI
→ Evidence
```

Day 14 可以贡献的 capability：

``` text
多站/多小区无线环境建模
UE 主区/邻区无线观测
A-Matrix 多波束方向响应
干扰组成可视化
SINR/received-power 仿真观测
系统级仿真输入底座
```

------------------------------------------------------------------------

# 25. 与三类优化问题的关系

Day 14 必须保持三类问题兼容。

### 网络结构参数优化

Radio Observation 可提供：

``` text
coverage
interference
beam / antenna directional context
```

### 用户接入参数优化

Radio Observation 可提供：

``` text
serving/neighbor candidate context
radio quality context
```

### 系统资源参数优化

Radio Observation 后续可与：

``` text
resource allocation
scheduler
traffic
```

组合。

Day 14 不把三类问题缩成"用户关联"。

------------------------------------------------------------------------

# 26. Traffic 边界

UE Twin 可以继续绑定：

``` text
traffic_profile
```

但 Day 14 不实现：

``` text
beam-space full-user traffic prediction
```

如果 UI 需要业务字段，只展示 Scenario 已有 traffic profile。

不要制造预测结果。

------------------------------------------------------------------------

# 27. Data Source / Evidence Level

Radio Observation 必须明确 source level。

建议：

``` text
SYNTHETIC
SEMI_SYNTHETIC
MEASURED_INPUT
MIXED
```

并继续允许项目已有 Evidence Level 体系映射。

一个 Observation 可能是：

``` text
真实 A-Matrix
+ synthetic UE position
+ Fast propagation model
```

此时不能整体标记为：

``` text
MEASURED
```

应是：

``` text
MIXED / SEMI_SYNTHETIC
```

并展示组成。

------------------------------------------------------------------------

# 28. Multi-fidelity 原则

继续坚持：

``` text
Fast Backend
→ 大规模 / 多场景 / 优化循环

Sionna
→ 代表性高保真验证

Measured Adapter
→ 实测数据验证
```

禁止要求所有 100+ Scenario 都跑完整 Sionna RT。

------------------------------------------------------------------------

# 29. Day 8 Historical Evidence

Day 8 的 frozen channel / historical evidence：

-   不修改；
-   不重新生成；
-   不覆盖；
-   不把 Day 14 新 Radio Observation 反写成 Day 8 原始结果。

如果使用 Day 8 topology：

必须标记：

``` text
Day14 integration fixture based on historical topology
```

而不是：

``` text
Day8 historical experiment regenerated
```

------------------------------------------------------------------------

# 30. Acceptance Scenario Set

Day 14 仍不选择最终 Acceptance Scenario Set。

保持：

``` text
status = DRAFT / NOT_SELECTED
```

Day 14 只确保未来场景集合能够使用 Radio Observation capability。

------------------------------------------------------------------------

# 31. TD-012 Count Semantics

继续保持明确区分：

``` text
scenario_definition_count
definition_verified_count
executed_count
experiment_verified_count
acceptance_evidence_count
```

禁止重新出现：

``` text
120 scenarios = 120 verified experiments
```

------------------------------------------------------------------------

# 32. Error / Status Contract

建议明确错误：

``` text
RADIO_CONTEXT_NOT_FOUND
CELL_RADIO_CONFIG_MISSING
UE_POSITION_MISSING
COORDINATE_SYSTEM_MISMATCH
PROPAGATION_BACKEND_NOT_AVAILABLE
A_MATRIX_PROFILE_NOT_FOUND
RADIO_IDENTITY_INCOMPLETE
ABSOLUTE_RADIO_KPI_NOT_CALIBRATED
INTERFERENCE_CONTEXT_INCOMPLETE
INVALID_RADIO_OBSERVATION
```

不得 silent fallback 到 demo scenario。

------------------------------------------------------------------------

# 33. No Silent Defaults

Day 14 禁止以下行为：

``` text
missing frequency → silently 3.5 GHz
missing tx power → silently 46 dBm
missing antenna → silently isotropic
missing serving cell → silently strongest cell
missing backend → silently demo backend
```

如果产品确实需要 default：

必须在 Scenario / Backend contract 中显式定义：

``` text
default_source
default_version
default_reason
```

并进入 provenance。

------------------------------------------------------------------------

# 34. Unit Contract

至少明确：

``` text
distance: m
azimuth: degree
elevation: degree
frequency: Hz / GHz with explicit unit
power: explicit dBm / W
relative response: dimensionless [0,1]
loss: dB when applicable
SINR: dB when actually computed
```

禁止把：

``` text
relative response [0,1]
```

标成：

``` text
dB / dBi
```

------------------------------------------------------------------------

# 35. Tests --- Geometry Regression

必须继续覆盖 Day 13：

-   east / west / north / south；
-   above / below；
-   same-position guard；
-   azimuth 0/360；
-   half-step tie；
-   355↔0 periodic nearest；
-   elevation boundary；
-   coordinate provenance。

------------------------------------------------------------------------

# 36. Tests --- Multi-cell

至少覆盖：

``` text
1 UE + 1 Cell
1 UE + 3 Cells
multiple UEs + multiple Cells
serving + neighbors
missing serving
missing neighbor
unknown cell
cell subset
```

------------------------------------------------------------------------

# 37. Tests --- Radio Observation

必须验证：

-   每个 Cell observation 独立；
-   serving signal 与 interferer 不混；
-   aggregate interference 可追溯到 per-interferer；
-   noise 独立；
-   SINR 组成可解释；
-   calibration status 正确传播；
-   unknown input 不变成 0；
-   unit 正确；
-   provenance 完整。

------------------------------------------------------------------------

# 38. Tests --- A-Matrix

必须回归：

-   shape 91×72；
-   normalized max = 1；
-   raw unchanged；
-   NPY hash unchanged；
-   phase_power / spread generic pipeline；
-   nearest-grid；
-   periodic azimuth；
-   strongest relative beam wording；
-   no dBi labeling；
-   no absolute gain fabrication。

------------------------------------------------------------------------

# 39. Tests --- Scenario Identity

必须验证：

``` text
same radio identity → same
different backend → different
different backend version → different
different A-Matrix → different
different antenna profile → different
different normalization → different
different radio config → different
missing required identity → insufficient
```

禁止：

``` text
missing == default == same
```

------------------------------------------------------------------------

# 40. Tests --- Comparison

如果两个 Experiment 的 Radio Context 不同：

Comparison 必须显示：

``` text
varying dimension: radio_context
```

或项目已有等价结构。

不得自动把不同无线条件的算法结果包装成公平算法对比。

------------------------------------------------------------------------

# 41. Tests --- Historical Integrity

必须验证：

-   Day 8 historical artifacts hash unchanged；
-   Day 13 A-Matrix source hash unchanged；
-   Day 13 evidence unchanged，除非仅追加明确的新 reference；
-   raw NPY 未进入 Git；
-   historical Experiment Record 不被 rewrite。

------------------------------------------------------------------------

# 42. Independent Verifier

Day 14 必须提供独立 verifier。

Verifier 不应简单调用：

``` text
RadioObservationService.evaluate()
```

然后拿 production 输出证明 production 正确。

至少独立验证：

-   scenario/cell/UE identity；
-   geometry；
-   A-Matrix manifest/hash；
-   normalization metadata；
-   radio config identity；
-   serving/neighbor consistency；
-   per-interferer aggregation；
-   unit；
-   calibration status；
-   evidence manifest；
-   source files unchanged。

------------------------------------------------------------------------

# 43. Evidence

建议：

``` text
reference/day14/SCN-DAY14-MULTISITE-RADIO/
```

至少输出：

``` text
README.md
radio-context.json
ue-radio-observation.json
serving-neighbor.json
interference-breakdown.json
radio-identity.json
calibration-status.json
verification.json
source-integrity.json
frontend-e2e.json
```

如果有截图：

``` text
screenshots/
```

截图不是 verifier 的替代品。

------------------------------------------------------------------------

# 44. Browser E2E

必须真实浏览器走通：

``` text
Scenario Center
→ 选择 Multi-site Scenario
→ 打开 UE Twin
→ 选择 UE
→ Radio View
→ 查看 Serving Cell
→ 查看 Neighbor Cells
→ 查看 Geometry
→ 查看 Beam Response
→ 查看 Received-Power Components
→ 查看 Interference Breakdown
→ 查看 Calibration Status
→ 查看 Provenance
→ 切换另一个 UE
```

要求：

``` text
console errors = 0
```

------------------------------------------------------------------------

# 45. Frontend 中文要求

主要用户界面使用中文：

``` text
无线观测
主小区
邻区
相对波束响应
仿真接收功率
干扰贡献
仿真 SINR
校准状态
数据来源
传播后端
证据
```

技术字段可以同时显示英文。

------------------------------------------------------------------------

# 46. Performance Observation

Day 14 不是性能竞赛。

但 Final Report 记录：

``` text
1 UE / 3 Cells
12 UE / 3 Cells
representative multi-cell scenario
```

的：

``` text
cold latency
warm latency
cache status
backend
```

只作为工程观测。

禁止写成：

``` text
优化速度提升 XX%
```

------------------------------------------------------------------------

# 47. Scale Architecture Check

虽然 Day 14 不跑 1000 Cells，但代码必须避免明显的：

``` text
global mutable state
per-request reload every NPY
hard-coded 3 cells
hard-coded 12 UEs
frontend hard-coded demo IDs
```

要保证未来能够扩展。

------------------------------------------------------------------------

# 48. Caching

允许缓存：

``` text
A-Matrix loaded artifacts
normalized pattern
static cell radio config
```

缓存必须按：

``` text
artifact hash / version
```

失效。

不能按文件名永久缓存而忽略内容变化。

------------------------------------------------------------------------

# 49. Logging

建议结构化记录：

``` text
scenario_id
scenario_instance_id
ue_id
cell_id
radio_backend
radio_model_version
a_matrix_artifact_id
calibration_status
observation_id
```

不要把巨大 91×72 数组全部打进日志。

------------------------------------------------------------------------

# 50. Provenance

每个 RadioObservationSet 至少可追溯：

``` text
repository HEAD
scenario definition hash
scenario instance id/hash
UE identity
cell identities
radio config hash
propagation backend/version
A-Matrix artifact/hash
antenna profile
normalization
angular grid
lookup method
calibration status
```

------------------------------------------------------------------------

# 51. Scientific Claim Boundary

Day 14 完成后允许说：

> 平台已建立多站/多小区 UE 无线观测能力，可基于 Scenario、UE-AAU
> 几何、A-Matrix 相对多波束方向响应和版本化传播后端生成可追溯的
> serving/neighbor、接收功率组成、干扰组成和仿真无线观测，并支持前端解释与证据导出。

允许说：

> 当前 A-Matrix 以归一化相对方向响应参与仿真。

允许说：

> 当前无线指标属于 simulation-derived / uncalibrated
> simulation（如果确实如此）。

------------------------------------------------------------------------

## 51.1 Day 14 禁止说

禁止：

> 已获得真实 RSRP。

禁止：

> 已获得实测 SINR。

禁止：

> A-Matrix 已完成绝对天线增益校准。

禁止：

> Day14 已完成华为实测数据验收。

禁止：

> 已实现完整 Handover。

禁止：

> 已完成百余场景验证。

禁止：

> 已完成千站千小区验收。

------------------------------------------------------------------------

# 52. Stop Conditions

出现以下任一情况，Day 14 不得冻结：

1.  修改 raw A-Matrix NPY；
2.  raw NPY 被 commit；
3.  normalized response 标为 dBi；
4.  未校准 received power 标为 measured RSRP；
5.  未校准 SINR 标为 measured SINR；
6.  silent fallback 到 demo scenario；
7.  hard-code 3 Cell / 12 UE；
8.  serving cell 来源不明；
9.  neighbor ranking metric 不明；
10. missing radio identity 被视为 same；
11. Comparison 忽略 radio context；
12. aggregate interference 无法追溯到 interferer；
13. Day 8 historical evidence 被改写；
14. Day 13 evidence 被重写；
15. A-Matrix hash 变化；
16. geometry convention 与 Day 13 不一致；
17. nearest-grid 行为回退；
18. calibration status 丢失；
19. UI 把未知值显示为 0；
20. 新建孤立 Radio Demo 而不接 Scenario/UE Twin；
21. independent verifier 只是调用 production service 自证；
22. 浏览器 console 有未解释错误；
23. Final Report 宣称任务书 KPI 已达标但没有对应证据。

------------------------------------------------------------------------

# 53. Definition of Done

Day 14 只有全部满足才可冻结：

-   [ ] Radio Observation Contract V0.1；
-   [ ] Multi-site / Multi-cell；
-   [ ] ScenarioInstance integration；
-   [ ] UE Twin integration；
-   [ ] Day13 geometry reuse；
-   [ ] A-Matrix relative response reuse；
-   [ ] PropagationBackend contract；
-   [ ] Fast/reference backend 可运行；
-   [ ] Received-power decomposition；
-   [ ] Interference decomposition；
-   [ ] Serving/Neighbor context；
-   [ ] CalibrationStatus；
-   [ ] Scientific identity；
-   [ ] Comparison radio-context awareness；
-   [ ] Chinese-first Radio View；
-   [ ] Beam Explorer linkage；
-   [ ] Independent verifier；
-   [ ] Evidence package；
-   [ ] Browser E2E；
-   [ ] console errors = 0；
-   [ ] NPY source unchanged；
-   [ ] historical evidence unchanged；
-   [ ] Day 11.1 / Day 12 / Day 13 regressions；
-   [ ] backend full tests；
-   [ ] frontend tests；
-   [ ] typecheck；
-   [ ] production build；
-   [ ] HEAD == origin/main；
-   [ ] clean worktree。

------------------------------------------------------------------------

# 54. Final Report 必填

建议：

``` text
design/DAY14_FINAL_REPORT.md
```

至少回答以下内容：

1.  Base HEAD；
2.  implementation commit；
3.  evidence commit；
4.  final HEAD；
5.  origin/main；
6.  worktree clean；
7.  RadioObservation contract version；
8.  supported scenario type；
9.  number of sites in reference fixture；
10. number of cells；
11. number of UEs；
12. hard-coded scale yes/no；
13. UE Twin version；
14. geometry version；
15. coordinate convention；
16. A-Matrix artifact ID；
17. A-Matrix hash；
18. source NPY modified yes/no；
19. raw NPY committed yes/no；
20. normalization policy；
21. angular-grid version；
22. lookup method；
23. antenna profile；
24. propagation backend；
25. backend version；
26. radio model version；
27. tx-power source；
28. carrier-frequency source；
29. bandwidth source；
30. missing-default policy；
31. received-power metric name；
32. received-power calibration status；
33. RSRP produced yes/no；
34. if yes, exact semantics；
35. SINR produced yes/no；
36. SINR calibration status；
37. measured RSRP produced yes/no；
38. measured SINR produced yes/no；
39. serving-cell source；
40. neighbor ranking metric；
41. interferer count；
42. aggregate interference method；
43. noise source；
44. Radio Identity fields；
45. Comparison identity behavior；
46. missing identity behavior；
47. Scenario integration；
48. Acceptance Center mapping；
49. UI pages；
50. Chinese labels；
51. browser E2E；
52. browser console errors；
53. backend targeted tests；
54. backend full tests；
55. frontend test files；
56. frontend tests；
57. typecheck；
58. build；
59. independent verifier；
60. verifier independence description；
61. evidence path；
62. Day8 integrity；
63. Day13 integrity；
64. performance observations；
65. limitations；
66. technical debt；
67. absolute calibration status；
68. Huawei measured-data status；
69. 100+ scenario verification status；
70. 1000-cell verification status；
71. task-book KPI status；
72. freeze conclusion；
73. Day15 readiness。

------------------------------------------------------------------------

# 55. 推荐实现顺序

建议 Agent 严格按以下顺序推进：

``` text
1. Freeze current baseline
2. Radio domain model
3. Calibration / metric semantics
4. Scenario radio-context binding
5. PropagationBackend contract
6. Fast/reference propagation implementation
7. UE Twin multi-cell observations
8. Serving/Neighbor context
9. Interference decomposition
10. Scientific identity
11. Comparison integration
12. API
13. Radio View frontend
14. Beam Explorer linkage
15. Independent verifier
16. Evidence
17. Browser E2E
18. Full regressions
19. Final Report
20. Commit / push / clean
```

不要先做漂亮 UI，再补科学语义。

------------------------------------------------------------------------

# 56. Day 14 验收演示脚本

建议最终现场演示固定为：

``` text
1. 打开场景中心
2. 选择一个 Multi-site / Multi-cell Scenario
3. 查看场景中的 Cell / AAU / UE
4. 选择一个 UE
5. 打开 UE Twin
6. 进入“无线观测”
7. 查看 Serving Cell
8. 查看 Neighbor Cells
9. 查看 UE 与各 Cell 的距离/方位角/俯仰角
10. 查看当前 Beam 和 A-Matrix 相对响应
11. 展开仿真接收功率组成
12. 展开干扰来源
13. 查看仿真 SINR
14. 查看 Calibration Status
15. 查看 Data Source / Backend / Version
16. 查看 Evidence / Provenance
17. 切换另一个 UE
18. 证明结果不是前端写死
```

演示重点不是"数值多漂亮"，而是：

> **无线观测链条完整、来源明确、主区邻区可解释、指标语义诚实、能够进入后续优化和验收体系。**

------------------------------------------------------------------------

# 57. Day 14 与后续路线

Day 14 完成后再决定 Day 15。

候选方向：

``` text
A. Traffic / Beam-space Traffic Adapter
B. Mobility & Handover
C. Calibrated RSRP/SINR
D. Acceptance Scenario Set
E. Scenario Batch Validation
```

当前不在 Day 14 预先锁定 Day 15。

选择依据必须是 Day 14 Final
Report、老师/数据方提供的新材料，以及验收缺口，而不是固定开发日历。

------------------------------------------------------------------------

# 58. 最终架构检查结论

截至 Day 14 开始前，平台主路线应保持：

``` text
真实/半真实数据资产
        ↓
Scenario System
        ↓
UE Twin / Network Twin Context
        ↓
Radio + Traffic + Network Models
        ↓
Three Optimization Problems
        ↓
Algorithm Integration
        ↓
Execution Manager
        ↓
KPI / Comparison
        ↓
Evidence / Verification
        ↓
Acceptance Center
```

其中：

``` text
Day 11 → 执行与比较完整性
Day 12 → Scenario System
Day 13 → A-Matrix + UE Radio Geometry
Day 14 → Multi-site Radio Observability
```

这条演进路径与"5G 网络学习优化仿真验证平台"的目标一致。

Day 14 的判断标准不是"做了多少无线公式"，而是：

> **是否把多站、多小区、UE、A-Matrix、传播、干扰、主区/邻区和无线指标，以可追溯、可解释、可扩展的方式接入统一仿真验证平台。**
