# Day 15 --- Platform Information Architecture & Scenario Configuration Foundation

**平台信息架构收敛 + 场景工作区 + 环境/网络/天线/UE 配置体系 +
天线方向图产品化**

-   **Base HEAD:** 开工前必须执行
    `git fetch origin && git rev-parse HEAD && git rev-parse origin/main`，以二者一致的最新
    SHA 写入 Final Report；不得硬编码旧 SHA
-   **Prerequisite:** Day 13/13.1 已冻结；Day 14 Agent 已完成。若 Day 14
    独立源码审计尚未关闭，Day 15 不得修改 Day 14 的 scientific
    semantics/evidence，只允许做兼容式产品整合
-   **Day 15 类型:** 平台架构 / 信息架构 / 配置模型 / 产品工作流
-   **不是:** 新算法研究、完整 Traffic、完整 Handover、绝对 RSRP/SINR
    校准、1000 Cell 性能验收、最终 Acceptance Scenario Set
-   **UI:** 中文优先
-   **核心原则:**
    从"按开发日拆菜单"收敛为"按用户工作流和领域对象组织平台"
-   **Migration Principle:** 不推翻 Day 11--14 已验证能力；通过 adapter
    / route migration / compatibility layer 收敛

------------------------------------------------------------------------

# 0. 为什么 Day 15 必须先做架构收敛

Day 12--14 的开发顺序是合理的：

``` text
Day 12 → Scenario System
Day 13 → A-Matrix + UE Twin Geometry
Day 14 → Multi-site Radio Observability
```

但"开发任务分解"不能直接成为最终产品一级导航。

如果继续把后续能力都做成一级菜单：

``` text
Scenario
A-Matrix
UE Twin
Radio Observation
Traffic
Handover
Map
...
```

平台会快速碎片化。

最终用户真正需要完成的是：

``` text
创建/选择场景
→ 配置环境
→ 配置站点/基站/小区
→ 配置天线
→ 配置 UE
→ 配置业务
→ 配置传播/无线模型
→ 配置网络功能
→ 选择优化问题
→ 保存场景
→ 生成实例
→ 运行实验
→ 分析
→ Comparison
→ Evidence
→ Acceptance
```

Day 15 的目标是把平台产品结构调整到这条链路上。

------------------------------------------------------------------------

# 1. 与项目任务的总方向

Day 15 不改变项目目标。

平台仍服务于：

``` text
5G 网络结构参数优化
用户接入参数优化
系统资源参数优化
```

并最终支撑：

``` text
百余种不同业务场景
系统级仿真验证
网络性能模型
算法库
可视分析
大规模基站/小区
实测数据验证
KPI / Evidence / Acceptance
```

因此 Day 15 不是 UI 美化日，而是为：

``` text
100+ Scenario
1000+ Cell
Measured Data
Traffic
Handover
Three Optimization Problems
Acceptance
```

建立稳定的配置与对象底座。

------------------------------------------------------------------------

# 2. Day 15 的最终一级导航

一级导航目标收敛到最多 6 个业务入口：

``` text
平台概览

场景
  ├─ 场景库
  ├─ 场景编辑器
  ├─ 环境资产
  └─ 配置/模型资产

实验
  ├─ 实验
  ├─ 批量实验（可暂为 disabled/placeholder）
  └─ Comparison

算法
  ├─ 算法库
  ├─ 算法接入
  └─ 执行状态

分析
  ├─ KPI
  ├─ 无线分析
  ├─ UE 分析
  └─ Traffic（未实现时明确标注）

验收
  ├─ 任务书追溯
  ├─ 场景覆盖
  ├─ Evidence
  └─ Verification

系统
  ├─ Backend
  ├─ Dataset / Assets
  └─ Runtime
```

如果当前前端框架不适合二级菜单，可采用 tabs / contextual
navigation，但领域关系必须保持。

------------------------------------------------------------------------

# 3. 一级菜单迁移要求

以下能力不得继续作为孤立一级产品：

``` text
A-Matrix
UE Twin
Multi-cell Radio Observation
```

它们必须保留全部能力，但迁移为：

``` text
A-Matrix
→ 场景 / 配置资产 / 天线

UE Twin
→ 场景 → UE
→ 实验 → UE Analysis

Radio Observation
→ 场景 → Radio View
→ 实验 → Radio Analysis
```

旧 URL 可以保留兼容 redirect。

禁止直接删除旧 route 导致 bookmark/API regression。

------------------------------------------------------------------------

# 4. 核心领域层级

Day 15 正式冻结以下概念层次：

``` text
Asset
Definition
Instance
Run
Observation
Evidence
```

------------------------------------------------------------------------

## 4.1 Asset

外部或可复用数据资产：

``` text
EnvironmentAsset
AntennaPatternAsset
DatasetAsset
MapAsset
ModelArtifact
```

示例：

``` text
hong-kong.gltf
city.osm
a_matrix.npy
measured_traffic.csv
```

Asset 不等于 Scenario。

------------------------------------------------------------------------

## 4.2 Definition

用户配置、可版本化、可复用：

``` text
EnvironmentDefinition
SiteDefinition
CellDefinition
AntennaDefinition
UEPopulationDefinition
TrafficDefinition
RadioModelDefinition
ScenarioDefinition
```

Definition 不包含随机 realization。

------------------------------------------------------------------------

## 4.3 Instance

Definition materialize 后形成具体仿真实例：

``` text
ScenarioInstance
UEInstance
CellInstance
TrafficRealization
ChannelArtifact
```

seed / realization 属于 Instance。

------------------------------------------------------------------------

## 4.4 Run

``` text
ExperimentRun
AlgorithmRun
ComparisonRun
```

算法参数变化不能创建新的"业务场景定义"。

------------------------------------------------------------------------

## 4.5 Observation

``` text
RadioObservation
TrafficObservation
KPIObservation
UEObservation
```

------------------------------------------------------------------------

## 4.6 Evidence

``` text
EvidencePackage
VerificationRecord
AcceptanceEvidence
```

------------------------------------------------------------------------

# 5. Scenario Workspace

Day 15 建立统一：

> **Scenario Workspace / 场景工作区**

它是平台最核心的网络数字实验配置入口。

结构：

``` text
Scenario Workspace
│
├── 基本信息
├── 环境 Environment
├── 网络 Network
├── 天线 Antenna
├── UE
├── 业务 Traffic
├── 无线/传播 Radio
├── 网络功能 Network Function
├── 优化问题 Optimization Problem
├── 预览 Preview
└── 校验 Validation
```

不要把所有内容塞进一个巨大表单。

------------------------------------------------------------------------

# 6. Scenario Workspace 状态

至少支持：

``` text
DRAFT
VALID
INVALID
READY
ARCHIVED
```

未来可扩展：

``` text
VERIFIED
ACCEPTANCE_ELIGIBLE
```

但 Day 15 不把这些状态与实验验证混淆。

------------------------------------------------------------------------

# 7. 场景库 vs 场景组合器

这是 Day 15 的 P0 产品调整。

## 7.1 场景库

主页面默认展示：

> **已经被配置和管理的 ScenarioDefinition**

不是理论笛卡尔积。

建议卡片/表格显示：

``` text
场景名称
场景类别
环境
网络规模
UE 类型
业务类型
天线
Radio Backend
优化问题
状态
最近实验
Evidence 状态
```

顶部统计：

``` text
已配置场景
可运行
已执行
实验验证
验收证据
```

------------------------------------------------------------------------

## 7.2 不允许主页面突出

不要把：

``` text
theoretical combinations = 453600
valid combinations = 408240
```

作为专家看到的首要成果。

可以放在：

``` text
场景组合器 → 高级统计
```

------------------------------------------------------------------------

# 8. 场景组合器

新增或重构：

> **创建场景 / 场景组合器**

提供按维度选择：

``` text
Environment
Topology
UE Population
Mobility
Traffic
Radio Condition
Network Function
Optimization Problem
Device/Antenna
```

流程：

``` text
选择维度
→ 生成候选组合
→ Compatibility Validation
→ 用户选择
→ 预览
→ 添加到场景库
```

------------------------------------------------------------------------

## 8.1 禁止自动把组合算成成果

禁止：

``` text
Cartesian Product
→ first 120
→ 120 typical scenarios
```

Day 15 后必须区分：

``` text
Candidate Combination
ScenarioDefinition
AcceptanceScenario
```

------------------------------------------------------------------------

# 9. Scenario Counting Protocol 延续

继续保持：

``` text
theoretical_combination_count
valid_candidate_count
configured_scenario_count
runnable_scenario_count
executed_scenario_count
experiment_verified_count
acceptance_evidence_count
```

其中专家首页优先显示：

``` text
configured
runnable
executed
verified
acceptance evidence
```

------------------------------------------------------------------------

# 10. 100+ 典型场景的正确路径

未来形成：

``` text
Scenario Taxonomy
        ↓
Combination Builder
        ↓
Compatibility Rules
        ↓
Candidate Scenario
        ↓
用户/专家选择或规则选取
        ↓
Scenario Catalog
        ↓
Experiment Validation
        ↓
Acceptance Scenario Set
```

Day 15 不要求凑齐 100+。

但数据模型和 UI 必须允许自然管理 100+ ScenarioDefinition。

------------------------------------------------------------------------

# 11. Environment Domain

Day 15 新增/正式化：

``` text
EnvironmentAsset
EnvironmentDefinition
```

Environment 是地图、建筑、地形、坐标空间的统一入口。

------------------------------------------------------------------------

# 12. EnvironmentAsset 类型

至少设计支持：

``` text
OSM
GLTF
GeoJSON
Raster Map
Terrain
Sionna Scene
Custom Mesh
```

Day 15 不要求全部实现完整 renderer。

但 schema 不得只支持 Sionna。

------------------------------------------------------------------------

# 13. 香港 GLTF

用户已有香港 GLTF 数据时，允许作为 Day 15 的真实 fixture。

建议流程：

``` text
环境资产
→ 导入
→ GLTF
→ Metadata inspection
→ Coordinate / scale confirmation
→ Preview
→ Save EnvironmentAsset
```

禁止：

-   自动假设 GLTF 是 WGS84；
-   自动假设单位为米而不记录；
-   为演示修改原始 GLTF；
-   把 GLTF 直接绑死为 Sionna scene。

------------------------------------------------------------------------

# 14. OSM

Day 15 设计 OSM workflow：

``` text
输入区域
→ 下载/导入 OSM
→ 保存 raw asset
→ preprocess
→ EnvironmentDefinition
→ 可选转换为 simulation backend representation
```

如果 Day 15 时间不足：

实现 contract + import existing `.osm` 即可。

**不要为了赶进度实现不可靠的在线下载器。**

------------------------------------------------------------------------

# 15. Map Layer

地图叠加属于：

``` text
Environment
```

不是 Radio Observation 独有功能。

统一定义：

``` text
MapLayer
```

可包含：

``` text
base map
OSM buildings
GLTF scene
site layer
cell layer
UE layer
radio overlay
traffic overlay
handover overlay
```

------------------------------------------------------------------------

# 16. Layer Visibility

前端统一提供：

``` text
图层
☑ 地图
☑ 建筑
☑ Site
☑ Cell
☑ UE
☐ Radio
☐ Traffic
☐ Handover
```

未来所有地图类分析共用，不允许各页面重复造地图组件。

------------------------------------------------------------------------

# 17. Network Domain

正式定义：

``` text
SiteDefinition
BaseStationDefinition
CellDefinition
AAUDefinition
```

逻辑层级：

``` text
Site
 └── BaseStation / Node
      └── Cell
           └── AAU / Antenna Binding
```

若现有数据模型不同，可用 adapter，不要求机械重命名。

------------------------------------------------------------------------

# 18. SiteDefinition

建议：

``` text
site_id
name
position
coordinate_system
altitude
metadata
source
version
```

------------------------------------------------------------------------

# 19. CellDefinition

核心字段建议：

``` text
cell_id
site_id
name

position / position_reference
carrier_frequency
bandwidth
tx_power

azimuth
mechanical_tilt
electrical_tilt
antenna_height

antenna_definition_id
aau_definition_id

network_parameters
resource_parameters

source
version
```

------------------------------------------------------------------------

# 20. Cell 参数扩展策略

禁止 Day 15 做一个 100+ 字段扁平 Cell JSON。

采用：

``` text
CellDefinition
├── CoreConfig
├── RadioConfig
├── AntennaBinding
├── NetworkParameterExtension
├── ResourceParameterExtension
└── BackendSpecificExtension
```

------------------------------------------------------------------------

# 21. 参数来源

每个重要参数应能追踪：

``` text
USER_DEFINED
IMPORTED
GENERATED
MEASURED
MODEL_DEFAULT
BACKEND_DEFAULT
UNKNOWN
```

如果使用 default：

必须记录 default source/version。

------------------------------------------------------------------------

# 22. 大规模网络配置能力

为了未来 1000+ Cell，Day 15 数据模型和 UI 必须预留：

``` text
Import
Template
Clone
Batch Edit
Generator
Filter
Multi-select
```

Day 15 不要求真正跑 1000 Cell。

------------------------------------------------------------------------

# 23. Network Import Contract

至少定义：

``` text
NetworkImporter
```

未来可支持：

``` text
CSV
GeoJSON
JSON
vendor export
measured config
```

Day 15 可以只实现一种最小可用格式。

但不得要求用户手工创建 1000 Cell。

------------------------------------------------------------------------

# 24. Antenna Domain

Day 15 把 A-Matrix 从"独立功能"提升为统一天线体系的一种实现。

正式定义：

``` text
AntennaDefinition
AntennaPatternProvider
AntennaPatternAsset
```

------------------------------------------------------------------------

# 25. AntennaPatternProvider

统一接口概念：

``` text
get_metadata()
get_pattern()
get_response(azimuth, elevation, beam?)
list_beams()
get_provenance()
```

------------------------------------------------------------------------

# 26. Antenna Provider 类型

至少设计：

``` text
SionnaBuiltinAntenna
GaussianAntenna
CustomPatternAntenna
AMatrixAntenna
ExternalAntennaAdapter
```

平台不得被 Sionna RT 锁死。

------------------------------------------------------------------------

# 27. Sionna Built-in Antenna

Day 15 如果已有 Sionna adapter，应暴露其 metadata。

如果没有：

只建立 provider contract + supported placeholder。

禁止假装已经完整接入所有 Sionna antenna types。

------------------------------------------------------------------------

# 28. Gaussian Antenna

支持定义 Gaussian pattern 时，应记录：

``` text
parameters
coordinate convention
normalization
backend compatibility
version
```

不要只保存一个 UI 名称。

------------------------------------------------------------------------

# 29. Custom Pattern

未来支持：

``` text
CSV
JSON
NPY
external provider
```

Day 15 不要求全部完成。

必须有 validation hook。

------------------------------------------------------------------------

# 30. A-Matrix Provider

Day 13 已冻结语义继续保持：

``` text
91 × 72
[elevation, azimuth]
relative gain/power-like response
peak normalized
nearest-grid
periodic azimuth
half-step tie policy
```

A-Matrix 是：

> **一种 AntennaPatternProvider**

不是：

> Scenario 本身

也不是：

> Association Matrix

------------------------------------------------------------------------

# 31. Antenna Binding

Cell/AAU 通过：

``` text
antenna_definition_id
```

绑定天线。

Scenario 不复制整个 91×72 数组。

------------------------------------------------------------------------

# 32. Antenna Workspace

在：

``` text
场景 → 配置/模型资产 → 天线
```

或：

``` text
场景编辑器 → 天线
```

提供统一管理。

至少显示：

``` text
名称
Provider Type
Source
Beam Count
Coordinate Convention
Normalization
Backend Compatibility
Calibration Status
Version
```

------------------------------------------------------------------------

# 33. 天线方向图默认 3D 球面

Day 15 将 A-Matrix/Pattern Viewer 默认视图改为：

> **3D Spherical Pattern**

方向：

``` text
azimuth
elevation
```

半径：

``` text
normalized relative response
```

------------------------------------------------------------------------

# 34. 球面显示科学语义

必须明确：

``` text
r = normalized relative response
```

禁止标：

``` text
dBi
absolute gain
measured power
```

除非未来完成校准。

------------------------------------------------------------------------

# 35. 保留二维 Heatmap

Viewer：

``` text
[球面方向图] [二维热力图]
```

默认：

``` text
球面方向图
```

Heatmap 继续用于：

``` text
91×72 grid inspection
debug
precise angular comparison
```

------------------------------------------------------------------------

# 36. 多波束叠加

新增：

``` text
单波束
多波束叠加
```

Overlay 模式允许选择多个 beam。

------------------------------------------------------------------------

## 36.1 重要语义

Overlay 仅表示：

> **visual overlay**

不是：

``` text
beam power combining
beamforming sum
physical composite pattern
```

除非未来有明确模型。

UI 使用：

``` text
多波束叠加显示
```

禁止叫：

``` text
合成方向图
```

------------------------------------------------------------------------

# 37. 波束切换交互

主要 Beam 切换不再使用 dropdown。

使用：

``` text
▲
Beam 03 / 08
▼
```

并支持：

``` text
ArrowUp
ArrowDown
```

快速切换。

------------------------------------------------------------------------

# 38. Beam Selector

可以保留高级 Beam selector 用于：

``` text
多选
快速跳转
overlay
```

但单 Beam 主操作使用上下切换。

------------------------------------------------------------------------

# 39. 3D Viewer 性能

91×72 = 6552 samples / beam。

Day 15 必须观察：

``` text
1 beam
4 beams overlay
8 beams overlay（如果真实数据支持）
```

的浏览器性能。

可以做 rendering decimation，但：

-   不改变 source data；
-   UI 标明 rendering resolution；
-   精确查询仍使用原始 grid。

------------------------------------------------------------------------

# 40. UE Domain

UE Twin 不再一级菜单。

统一：

``` text
Scenario
→ UE
→ UE Detail / UE Twin
```

以及：

``` text
Experiment
→ Analysis
→ UE
```

------------------------------------------------------------------------

# 41. UE Detail

建议 tabs：

``` text
基本信息
业务
移动性
主区/邻区
无线观测
Beam
KPI
Timeline
Provenance
```

未实现的 tabs：

``` text
Coming / Not Available
```

不能生成假数据。

------------------------------------------------------------------------

# 42. Radio Observation Integration

Day 14 Radio Observation 不删除。

迁移到：

``` text
Scenario Workspace
→ Radio View
```

和：

``` text
Experiment
→ Analysis
→ Radio
```

------------------------------------------------------------------------

# 43. Config-time vs Result-time

必须区分：

### 配置态

``` text
Scenario Radio Preview
```

表示当前场景配置下的预览/仿真输入。

### 结果态

``` text
Experiment Radio Analysis
```

绑定具体 Experiment / frozen scientific identity。

两者不能混。

------------------------------------------------------------------------

# 44. Traffic

Day 15 只建立位置：

``` text
Scenario Workspace
→ Traffic
```

继续允许：

``` text
Full Buffer
Static Demand
Time Series
Beam-space Prediction
Measured Traffic
```

但没有真实模型时：

``` text
NOT_IMPLEMENTED
```

不要做假的 beam-space prediction。

------------------------------------------------------------------------

# 45. Network Function

场景中正式留出：

``` text
Access
Handover
Load Balance
Scheduling
Resource Allocation
```

Day 15 不实现完整逻辑。

作用是避免以后再新增一级菜单。

------------------------------------------------------------------------

# 46. Optimization Problem

ScenarioDefinition 必须可以声明：

``` text
NETWORK_STRUCTURE
USER_ACCESS
SYSTEM_RESOURCE
```

支持一个场景与多个 compatible problem 关联。

------------------------------------------------------------------------

# 47. Platform Overview 重设计

Day 15 重做 `/overview`。

首页不再以开发阶段 widgets 为核心。

------------------------------------------------------------------------

# 48. Overview 第一屏

建议：

``` text
5G 网络学习优化仿真验证平台

已配置场景
可运行场景
已执行场景
实验验证
验收证据
```

数据必须来自真实 backend。

------------------------------------------------------------------------

# 49. 三类优化覆盖

显示：

``` text
网络结构参数优化
用户接入参数优化
系统资源参数优化
```

每类展示：

``` text
Scenario Count
Experiment Count
Evidence Count
```

没有 evidence 就显示 0。

------------------------------------------------------------------------

# 50. Capability / Acceptance Map

第二屏建议：

``` text
场景系统
多站多小区
天线模型
A-Matrix
UE Twin
无线观测
Traffic
Handover
Measured Data
Large-scale
Acceptance Evidence
```

状态只能来自：

``` text
capability registry / evidence
```

禁止前端 hard-code：

``` text
完成
```

------------------------------------------------------------------------

# 51. Recent Activity

Overview 后半部分才显示：

``` text
最近实验
最近 Comparison
最近 Evidence
Runtime Status
Backend Status
```

------------------------------------------------------------------------

# 52. Capability Registry

建议新增：

``` text
CapabilityRegistry
```

字段：

``` text
capability_id
name
status
implementation_version
evidence_refs
limitations
last_verified_at
```

状态例如：

``` text
NOT_IMPLEMENTED
FOUNDATION
IMPLEMENTED
VERIFIED
ACCEPTANCE_EVIDENCE
```

------------------------------------------------------------------------

# 53. Capability 状态语义

禁止：

``` text
implemented = acceptance passed
```

必须区分：

``` text
功能实现
实验验证
验收证据
```

------------------------------------------------------------------------

# 54. 场景编辑器布局

建议三栏：

``` text
左：配置树
中：地图/3D/主要编辑区
右：属性/校验
```

例如：

``` text
┌──────────────┬────────────────────────┬───────────────┐
│ Environment  │                        │ Properties    │
│ Network      │       Map / 3D         │ Validation    │
│ Antenna      │                        │ Provenance    │
│ UE           │                        │               │
│ Traffic      │                        │               │
│ Radio        │                        │               │
│ Function     │                        │               │
│ Optimization │                        │               │
└──────────────┴────────────────────────┴───────────────┘
```

------------------------------------------------------------------------

# 55. 地图/3D 编辑区

中心 Viewer 统一承载：

``` text
2D Map
3D Environment
Site/Cell
UE
Radio overlay
Traffic overlay
```

不要每个功能写一个 viewer。

------------------------------------------------------------------------

# 56. Selection Model

统一：

``` text
select Site
→ property panel

select Cell
→ property panel

select UE
→ UE detail

select Antenna
→ pattern viewer
```

------------------------------------------------------------------------

# 57. Validation Panel

实时显示：

``` text
ERROR
WARNING
INFO
```

例如：

``` text
Cell missing antenna
UE outside environment bounds
Coordinate system unknown
Radio backend incompatible
Traffic model unavailable
```

禁止 silent fallback。

------------------------------------------------------------------------

# 58. Coordinate System Contract

Environment / Site / Cell / UE / GLTF / OSM 都必须有：

``` text
coordinate_system
unit
origin/reference
source
status
```

Day 15 不要求解决所有 GIS 转换。

但未知必须是 UNKNOWN，不可假设。

------------------------------------------------------------------------

# 59. GLTF / OSM / Sionna Scene 的关系

不要把它们强行当同一种原始格式。

统一的是：

``` text
EnvironmentAsset interface
```

而不是文件格式。

每个 adapter 负责：

``` text
metadata
coordinate semantics
preview
backend compatibility
conversion status
```

------------------------------------------------------------------------

# 60. Backend Compatibility

Environment、Antenna、Radio Model 都应声明：

``` text
supported_backends
```

例如：

``` text
FAST
SIONNA_RT
EXTERNAL
```

禁止 Scenario READY 时才发现关键 asset 与 backend 不兼容。

------------------------------------------------------------------------

# 61. Scenario Validation

`ScenarioValidator` 至少验证：

``` text
environment
coordinate system
network
cells
antenna binding
UE
traffic availability
radio backend
optimization problem
compatibility rules
```

------------------------------------------------------------------------

# 62. Scenario Readiness

区分：

``` text
CONFIG_VALID
SIMULATION_READY
EXPERIMENT_READY
```

未来再增加：

``` text
ACCEPTANCE_READY
```

------------------------------------------------------------------------

# 63. Scientific Identity

Day 15 UI 重构不得削弱 Experiment scientific identity。

继续绑定：

``` text
dataset
scenario
scenario instance
environment
network config
traffic realization
channel artifact
A-Matrix
antenna
radio backend
objective
constraints
KPI
protocol
budget
algorithm
```

------------------------------------------------------------------------

# 64. UI 配置对象与冻结实验

重要：

ScenarioDefinition 可以继续编辑。

但已启动 Experiment 必须绑定：

``` text
frozen ScenarioInstance / identity hash
```

后续修改 Definition 不得 retroactively 改历史 Experiment。

------------------------------------------------------------------------

# 65. Versioning

Definition 修改后至少：

``` text
version++
hash changes
```

历史 Experiment 保持旧 version。

------------------------------------------------------------------------

# 66. Save / Clone

Scenario 支持：

``` text
保存
另存为
克隆
归档
```

Day 15 不建议实现 destructive delete。

------------------------------------------------------------------------

# 67. Bulk Configuration

至少设计：

``` text
multi-select Cells
→ batch edit
```

可批量改：

``` text
frequency
bandwidth
tx power
antenna binding
tilt
```

如果 Day 15 时间不足，可实现最小 2--3 个字段。

------------------------------------------------------------------------

# 68. Search / Filter

场景库至少支持：

``` text
类别
环境
拓扑
业务
优化问题
状态
数据源
```

天线资产支持：

``` text
provider
beam count
backend
calibration
```

------------------------------------------------------------------------

# 69. API Boundary

不要做一个巨大：

``` text
PUT /scenario/everything
```

建议按资源：

``` text
/api/scenarios
/api/scenarios/{id}
/api/scenarios/{id}/validate
/api/scenarios/{id}/materialize

/api/environments
/api/network/sites
/api/network/cells
/api/antennas
/api/ue-populations
/api/traffic-models
```

具体路径遵循现有项目风格。

------------------------------------------------------------------------

# 70. Backward Compatibility

Day 15 必须列出旧页面：

``` text
old route
new route
migration behavior
redirect yes/no
```

特别是：

``` text
A-Matrix
UE Twin
Radio Observation
Scenario Center
```

------------------------------------------------------------------------

# 71. 禁止重写科学服务

Day 15 的目标不是重写：

``` text
ExecutionManager
ComparisonService
RadioObservationService
A-Matrix normalization
UE geometry
Scenario counting
```

除非发现真实 bug。

如发现 bug：

单独记录：

``` text
BUG-ID
impact
fix
regression
```

不要借 UI refactor 改科学语义。

------------------------------------------------------------------------

# 72. Frontend Component Architecture

建议提取：

``` text
ScenarioWorkspace
EnvironmentViewer
LayerManager
NetworkTree
PropertyPanel
ValidationPanel
AntennaPatternViewer
UEDetailPanel
RadioAnalysisPanel
```

避免 copy/paste Day13/14 页面。

------------------------------------------------------------------------

# 73. AntennaPatternViewer

统一服务：

``` text
Sionna Built-in
Gaussian
Custom
A-Matrix
```

只要 provider 能输出标准 pattern。

------------------------------------------------------------------------

# 74. 3D Spherical Viewer Tests

必须覆盖：

``` text
single beam
beam next
beam previous
wrap first/last
keyboard up/down
multi-beam select
overlay
return single-beam
2D/3D switch
```

------------------------------------------------------------------------

# 75. Scientific Viewer Tests

验证：

``` text
normalized response remains [0,1]
no dBi label
no measured label
overlay does not numerically combine beams
exact query still uses source grid
```

------------------------------------------------------------------------

# 76. Scenario Library Tests

验证：

``` text
only configured scenarios shown by default
candidate combinations not mixed into catalog
filter
search
clone
archive
status
counts
```

------------------------------------------------------------------------

# 77. Combination Builder Tests

验证：

``` text
dimension select
compatibility rules
invalid combination
candidate preview
add selected candidate
definition created
canonical hash
duplicate detection
```

------------------------------------------------------------------------

# 78. Environment Tests

至少：

``` text
asset metadata
unknown coordinate
GLTF registration
OSM registration/import contract
layer visibility
no source mutation
```

如果香港 GLTF 可访问：

增加真实 fixture metadata test。

不要把大型 GLTF commit 进 Git，除非项目明确允许。

------------------------------------------------------------------------

# 79. Network Tests

至少：

``` text
site create/update
cell create/update
antenna binding
unknown antenna
batch edit
version/hash
coordinate validation
```

------------------------------------------------------------------------

# 80. 1000-Cell Readiness Test

Day 15 不跑物理仿真。

但做配置层 smoke：

``` text
generate/import 1000 lightweight CellDefinitions
validate
filter
serialize
materialize metadata
```

记录：

``` text
time
memory observation
UI behavior
```

目标只是发现明显 O(N²)/UI 卡死问题。

**这不是任务书 1000 Cell 仿真验收。**

------------------------------------------------------------------------

# 81. 100+ Scenario Management Test

创建测试 catalog：

``` text
>= 120 lightweight configured definitions
```

验证：

``` text
pagination
filter
search
status counts
no UI freeze
```

这些测试 definition 不得被宣传成：

``` text
120 acceptance scenarios
```

------------------------------------------------------------------------

# 82. Browser E2E --- 主工作流

必须真实浏览器完成：

``` text
1. 平台概览
2. 进入场景库
3. 创建场景
4. 选择/注册 Environment
5. 添加 Site
6. 添加 Cell
7. 配置 Cell 参数
8. 绑定 Antenna
9. 打开 Antenna Viewer
10. 默认显示球面方向图
11. 上下切换 Beam
12. 开启多波束叠加
13. 返回场景
14. 添加/选择 UE
15. 查看 UE Detail
16. 查看 Radio View
17. Validation
18. 保存 ScenarioDefinition
19. 场景库可看到新场景
20. Clone
21. Filter
```

------------------------------------------------------------------------

# 83. Browser E2E --- Contextual Analysis

验证：

``` text
Scenario → UE → Radio
```

以及如果已有 Experiment：

``` text
Experiment → Analysis → UE / Radio
```

不得要求用户通过一级菜单猜上下文。

------------------------------------------------------------------------

# 84. Browser Console

要求：

``` text
console errors = 0
```

任何 warning 需在 Final Report 说明。

------------------------------------------------------------------------

# 85. Accessibility / Interaction

至少：

-   keyboard focus；
-   Beam up/down keyboard；
-   buttons 有 label；
-   3D Viewer 有文本 metadata fallback；
-   不依赖颜色作为唯一状态表达。

------------------------------------------------------------------------

# 86. Independent Verifier

Day 15 verifier 重点不是验证 UI 像不像。

独立验证：

``` text
ScenarioDefinition identity
Asset binding
Cell → Antenna binding
Environment provenance
Scenario catalog semantics
candidate vs configured separation
version/hash
historical Experiment immutability
A-Matrix source integrity
Day13 lookup semantics
Day14 Radio identity
```

Verifier 不调用 production "save then read" 自证所有内容。

------------------------------------------------------------------------

# 87. Evidence

建议：

``` text
reference/day15/PLATFORM-IA-SCENARIO-CONFIG/
```

至少：

``` text
README.md
navigation-map.json
domain-model.json
route-migration.json
scenario-example.json
environment-example.json
network-example.json
antenna-example.json
scenario-validation.json
scenario-count-semantics.json
scale-config-smoke.json
source-integrity.json
verification.json
frontend-e2e.json
```

可增加：

``` text
screenshots/
```

但截图不是 verifier。

------------------------------------------------------------------------

# 88. Historical Integrity

必须确认：

``` text
Day8 historical evidence unchanged
Day11.1 execution semantics unchanged
Day12 Scenario identity semantics preserved
Day13 A-Matrix raw hashes unchanged
Day13 lookup semantics unchanged
Day14 Radio scientific semantics unchanged
```

------------------------------------------------------------------------

# 89. README / Architecture Docs

Day 15 必须更新 README。

README 不得继续停留在 Day7 产品结构。

至少更新：

``` text
Platform Architecture
Navigation
Scenario Workflow
Antenna Providers
Environment Assets
Experiment Flow
Scientific Boundary
Current Limitations
```

------------------------------------------------------------------------

# 90. Architecture Decision Records

建议新增：

``` text
design/adr/
```

至少记录：

``` text
ADR-001 Scenario Workspace
ADR-002 Asset-Definition-Instance-Run-Observation-Evidence
ADR-003 AntennaPatternProvider
ADR-004 EnvironmentAsset
ADR-005 Navigation Consolidation
```

如果项目已有 ADR 规范，沿用。

------------------------------------------------------------------------

# 91. Stop Conditions

出现任一情况，Day 15 不得冻结：

1.  A-Matrix/UE Twin/Radio 功能因菜单迁移丢失；
2.  删除旧 route 且无 migration；
3.  重写 Day13 normalization；
4.  nearest-grid 回退；
5.  raw NPY hash 变化；
6.  raw NPY 进入 Git；
7.  Day14 Radio identity 被削弱；
8.  ScenarioDefinition 修改会改变历史 Experiment；
9.  candidate combination 被计为 configured scenario；
10. random seed 被计为新业务场景；
11. 首页把 theoretical combinations 当"已配置场景"；
12. 120 test definitions 被宣称为 120 acceptance scenarios；
13. Environment 默认为 WGS84 而无来源；
14. GLTF 默认为米而无 provenance；
15. OSM/GLTF 被绑死为 Sionna-only domain object；
16. Antenna model 只能支持 A-Matrix；
17. Antenna model 只能支持 Sionna；
18. Cell 成为巨大无版本扁平 JSON；
19. unknown 参数 silent default；
20. 3D pattern 标为 dBi；
21. multi-beam overlay 做未定义的物理求和；
22. UE Twin 仍只能从孤立一级菜单访问；
23. Radio Observation 仍只能从孤立一级菜单访问；
24. 各页面重复实现独立地图系统；
25. 1000 Cell smoke 被宣称为 1000 Cell 仿真验收；
26. Capability 状态由前端硬编码；
27. Overview 显示虚假验收完成状态；
28. Independent verifier 仅调用 production service 自证；
29. Browser E2E 未覆盖主工作流；
30. console error 未解释；
31. Day14 尚未独立审计时，Day15 无理由修改其 scientific semantics。

------------------------------------------------------------------------

# 92. Definition of Done

-   [ ] 一级导航收敛；
-   [ ] Scenario Workspace；
-   [ ] Asset/Definition/Instance/Run/Observation/Evidence 模型；
-   [ ] 场景库；
-   [ ] 场景组合器；
-   [ ] candidate/configured 分离；
-   [ ] EnvironmentAsset；
-   [ ] GLTF/OSM contract；
-   [ ] MapLayer；
-   [ ] Site/Cell model；
-   [ ] Cell 参数 provenance；
-   [ ] AntennaPatternProvider；
-   [ ] Sionna/Gaussian/Custom/A-Matrix provider boundary；
-   [ ] Cell-Antenna binding；
-   [ ] 3D spherical antenna viewer；
-   [ ] 2D heatmap retained；
-   [ ] Beam up/down；
-   [ ] multi-beam visual overlay；
-   [ ] UE contextual integration；
-   [ ] Radio contextual integration；
-   [ ] Traffic/Network Function slots；
-   [ ] Overview redesign；
-   [ ] Capability Registry；
-   [ ] Scientific identity preserved；
-   [ ] historical Experiment immutability；
-   [ ] 120+ config management smoke；
-   [ ] 1000 Cell config smoke；
-   [ ] Independent verifier；
-   [ ] Evidence package；
-   [ ] README updated；
-   [ ] Browser E2E；
-   [ ] console errors = 0；
-   [ ] backend full tests；
-   [ ] frontend full tests；
-   [ ] typecheck；
-   [ ] production build；
-   [ ] source assets unchanged；
-   [ ] HEAD == origin/main；
-   [ ] clean worktree。

------------------------------------------------------------------------

# 93. Final Report

生成：

``` text
design/DAY15_FINAL_REPORT.md
```

至少回答：

1.  Base HEAD；
2.  implementation commits；
3.  evidence commit；
4.  final HEAD；
5.  origin/main；
6.  worktree clean；
7.  old top-level navigation；
8.  new top-level navigation；
9.  migrated routes；
10. redirects；
11. Scenario Workspace status；
12. Scenario Library status；
13. Combination Builder status；
14. candidate/configured semantics；
15. theoretical count；
16. configured count；
17. runnable count；
18. executed count；
19. experiment verified count；
20. acceptance evidence count；
21. Asset model；
22. Definition model；
23. Instance model；
24. Run model；
25. Observation model；
26. Evidence model；
27. EnvironmentAsset types；
28. GLTF support；
29. OSM support；
30. coordinate contract；
31. map layer contract；
32. Site model；
33. Cell model；
34. Cell core parameters；
35. extension strategy；
36. parameter provenance；
37. network import status；
38. batch edit status；
39. 1000 Cell config smoke result；
40. AntennaPatternProvider version；
41. supported providers；
42. Sionna provider status；
43. Gaussian provider status；
44. Custom provider status；
45. A-Matrix provider status；
46. A-Matrix source hashes；
47. raw NPY modified yes/no；
48. raw NPY committed yes/no；
49. 91×72 semantics preserved；
50. normalization preserved；
51. nearest-grid preserved；
52. spherical viewer；
53. heatmap；
54. Beam up/down；
55. keyboard Beam navigation；
56. multi-beam overlay；
57. physical combining performed yes/no；
58. UE Twin contextual route；
59. Radio contextual route；
60. Day14 semantics changed yes/no；
61. Traffic slot；
62. Network Function slot；
63. three optimization problems；
64. Overview redesign；
65. Capability Registry；
66. capability status source；
67. 120+ config management smoke；
68. 120 test definitions advertised as acceptance scenarios yes/no；
69. historical Experiment immutability；
70. scientific identity regression；
71. Comparison regression；
72. Day8 integrity；
73. Day11.1 integrity；
74. Day12 integrity；
75. Day13 integrity；
76. Day14 integrity；
77. independent verifier；
78. verifier independence；
79. backend targeted tests；
80. backend full tests；
81. frontend test files；
82. frontend tests；
83. typecheck；
84. build；
85. Browser E2E；
86. console errors；
87. performance observations；
88. 3D viewer performance；
89. evidence path；
90. README updated；
91. ADRs；
92. known limitations；
93. technical debt；
94. 100+ acceptance scenario status；
95. 1000 Cell simulation status；
96. measured-data status；
97. absolute radio calibration status；
98. freeze conclusion；
99. next-day readiness。

------------------------------------------------------------------------

# 94. 推荐实施顺序

严格建议：

``` text
1. Capture current HEAD / baseline
2. Inventory current routes/components
3. Freeze migration map
4. Domain model: Asset → Evidence
5. Scenario Library semantics
6. Scenario Workspace shell
7. EnvironmentAsset
8. Network Site/Cell config
9. AntennaPatternProvider
10. A-Matrix adapter migration
11. Spherical Viewer
12. Beam navigation / overlay
13. UE contextual migration
14. Radio contextual migration
15. Combination Builder
16. Overview
17. Capability Registry
18. 120+ management smoke
19. 1000 Cell config smoke
20. Independent verifier
21. Browser E2E
22. Full regression
23. README / ADR
24. Evidence
25. Final Report
26. Commit / push / clean
```

不要先移动菜单，再想领域模型。

------------------------------------------------------------------------

# 95. Day 15 最终演示脚本

最终演示建议：

``` text
1. 打开平台概览
2. 查看真实场景/实验/Evidence 状态
3. 进入场景库
4. 按类别筛选
5. 点击“创建场景”
6. 进入 Scenario Workspace
7. 添加/选择 Environment
8. 注册/选择 GLTF 或已有 EnvironmentAsset
9. 查看 Map/3D Layer
10. 添加 Site
11. 添加 Cell
12. 修改 Cell 功率/频率/方位角/倾角等配置
13. 选择 Antenna
14. 切换 Sionna/Gaussian/A-Matrix 等 provider（仅展示真实已实现项）
15. 打开 A-Matrix Pattern
16. 默认看到球面方向图
17. ▲/▼ 快速切换 Beam
18. 开启多波束叠加显示
19. 切回 Heatmap
20. 添加/选择 UE
21. 打开 UE Detail
22. 查看主区/邻区与 Radio
23. 查看 Scenario Validation
24. 保存 ScenarioDefinition
25. 返回场景库
26. 搜索/筛选刚才场景
27. Clone 场景
28. 打开场景组合器
29. 生成候选组合
30. 选择候选并加入场景库
31. 证明候选组合数量与已配置场景数量不同
32. 查看 Evidence / Provenance
```

------------------------------------------------------------------------

# 96. Day 15 冻结后的产品结构

期望最终用户看到的不是：

``` text
Day12 Scenario
Day13 A-Matrix
Day13 UE Twin
Day14 Radio
Day15 Map
```

而是：

``` text
平台概览
│
├── 场景
│    └── Environment / Network / Antenna / UE / Traffic / Radio / Function / Problem
│
├── 实验
│
├── 算法
│
├── 分析
│    └── KPI / Radio / UE / Traffic
│
├── 验收
│
└── 系统
```

底层仍保留 Day 11--14 已验证的服务和 Evidence。

------------------------------------------------------------------------

# 97. Day 15 后的路线

Day 15 完成后，不预先强制 Day 16。

根据 Final Report 和实际数据条件，在以下方向选择：

``` text
A. Traffic / Beam-space Traffic Integration
B. Mobility & Handover
C. Environment / OSM / GLTF Deep Integration
D. Calibrated RSRP/SINR
E. Acceptance Scenario Set
F. Scenario Batch Validation
G. Large-scale 1000 Cell Simulation Foundation
```

优先级由：

``` text
任务书验收缺口
真实数据可用性
平台当前技术债
老师/团队接口
```

共同决定。

------------------------------------------------------------------------

# 98. 最终原则

Day 15 不是为了让页面"看起来更统一"。

真正目标是冻结一套以后不容易推翻的关系：

``` text
Environment
    ↓
Network: Site / Cell
    ↓
Antenna
    ↓
UE / Population
    ↓
Traffic
    ↓
Radio / Propagation
    ↓
Network Function
    ↓
Optimization Problem
    ↓
ScenarioDefinition
    ↓
ScenarioInstance
    ↓
Experiment
    ↓
Observation / KPI / Comparison
    ↓
Evidence
    ↓
Acceptance
```

只要这条链稳定：

-   A-Matrix 有正确归属；
-   UE Twin 有正确上下文；
-   Radio Observation 不再孤立；
-   OSM/GLTF 有统一入口；
-   Cell 参数能够系统配置；
-   Sionna 和非 Sionna 天线可以共存；
-   100+ 场景不需要硬凑；
-   1000+ Cell 不依赖人工逐个配置；
-   Traffic/Handover 后续有明确插槽；
-   验收 Evidence 可以沿同一对象链回溯。

**Day 15
的成功标准不是新增多少功能，而是以后继续深入时平台不会越做越乱。**
