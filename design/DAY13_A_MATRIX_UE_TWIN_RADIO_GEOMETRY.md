# Day 13 --- A-Matrix Integration & UE Twin Radio Geometry Foundation

## 真实多波束方向图接入 + UE 孪生无线几何 + 相对波束响应可视化

> **Base HEAD:** `477a047220cadd0a9d132e53c1e8be9fd18b34b7`
>
> **Day 12:** FROZEN --- `PASS WITH DOCUMENTED LIMITATIONS`
>
> **定位：** 平台能力集成日。不是算法研究日，不是绝对 RSRP/SINR
> 校准日，不是 Handover 实现日，不是 KPI 冲刺日。
>
> **核心目标：** 将真实 A-Matrix
> 作为归一化的多波束天线相对方向响应正式接入 5glosvp，并建立 UE Twin
> 无线几何基础，形成：
>
> `AAU/Cell + UE 空间位置 → azimuth/elevation → 多波束相对响应 → serving/neighbor context → 可视化与证据`
>
> **科学边界：** 当前 A-Matrix 按项目工程理解作为信号强度/线性 gain-like
> 方向图使用，仿真消费时做峰值归一化，类似 Sionna RT
> 天线方向图的相对方向响应。不得把归一化值单独解释成物理校准后的绝对增益、RSRP
> 或 SINR。

------------------------------------------------------------------------

# 1. 已确认输入事实

真实数据目录（只读）：

`/home/ubuntu/h2/sionnatest/webapp/data/a_matrix`

当前 sionnatest 工程约定：

``` text
shape = [91, 72]
axis 0 = elevation
axis 1 = azimuth

elevation = -90° + row * 2°
azimuth   = column * 5°

Elevation: -90° ... +90°, 2° step, 91 samples
Azimuth:    0° ... 355°, 5° step, 72 samples
```

Sionna 球坐标转换：

``` text
elevation = 90° - theta
azimuth   = phi
```

文档必须称为 **sionnatest implementation convention /
当前工程代码使用约定**，不能升级为"原始测量方权威坐标定义已确认"。

当前数值工程语义：

``` text
raw A-Matrix value
→ non-negative linear signal-strength / gain-like response
→ peak normalization: g_norm = g / max(g)
→ relative beam power response
→ field amplitude = sqrt(max(g_norm, 0))
```

`phase_power` 和 `spread` 当前只作为 A-Matrix library/dataset family
identifier；两者走同一套 load → validate → normalize → lookup
流程，不自行赋予不同物理公式。

sionnatest 已实际将 A-Matrix 用于 Sionna antenna pattern、relative
directional response、ray-direction importance sampling、Radio Map
相关路径以及 beam_id → entry_key 选择。Day 13
应复用/抽象这些工程语义，不重新发明数学。

------------------------------------------------------------------------

# 2. Day 13 闭环

必须形成：

``` text
A-Matrix .npy
→ AMatrix Library Adapter
→ AAU / Antenna / Beam Profile
→ 91×72 Angular Grid
→ Peak-normalized Relative Beam Pattern
→ UE Twin Position
→ AAU ↔ UE Geometry
→ Elevation / Azimuth
→ Angular Lookup
→ Per-Beam Relative Response
→ Serving / Neighbor Context
→ Frontend Visualization + Evidence
```

平台完成后应能回答：

-   某 UE 相对于某 AAU/Cell 位于什么方向？
-   在该方向上，此天线 profile 的各 beam 相对响应是多少？
-   当前方向相对响应最大的 beam 是哪个？

不得声称由此单独得到绝对 RSRP/SINR。

------------------------------------------------------------------------

# 3. 收口 Day 12 技术债

## TD-012-01

将歧义的 `verified_count` 拆成：

``` text
definition_verified_count
experiment_verified_count
acceptance_evidence_count
```

语义：

-   `definition_verified_count`：Scenario Definition 通过
    taxonomy/compatibility/hash/semantic uniqueness 独立结构校验。
-   `experiment_verified_count`：该 Scenario 至少存在一个真实 Experiment
    且 evidence verified。
-   `acceptance_evidence_count`：满足未来正式验收 evidence policy。

UI 不得继续用"已验证场景 120"表示 definition verification。建议显示：

``` text
场景定义
定义校验通过
已执行
实验验证
验收证据
```

## TD-012-02

只建立 `AcceptanceScenarioSet` schema/boundary：

``` text
set_id
name
version
selection_policy
scenario_ids
coverage_summary
status
evidence_status
```

当前状态保持 `DRAFT / NOT_SELECTED`。Day 13 不自行挑 120
个并称最终验收集合。

------------------------------------------------------------------------

# 4. A-Matrix Domain Model

建立正式对象（名称可按现有风格调整）：

``` text
AMatrixLibrary
AMatrixEntry
AntennaProfile
BeamProfile
AngularGrid
NormalizedBeamPattern
```

`AMatrixLibrary` 至少记录
library_id、family、source、source_artifact、entries、metadata。

`AMatrixEntry` 至少记录
entry_key、raw_shape、dtype、beam_id、beam_family、能够被 profiles
证明的 device/AAU mapping、source_hash。

`AngularGrid` 固定记录当前工程约定：

``` text
elevation_min_deg = -90
elevation_max_deg = 90
elevation_step_deg = 2
elevation_count = 91

azimuth_min_deg = 0
azimuth_max_sample_deg = 355
azimuth_period_deg = 360
azimuth_step_deg = 5
azimuth_count = 72

axis_order = [elevation, azimuth]
convention_source = SIONNATEST_IMPLEMENTATION
```

------------------------------------------------------------------------

# 5. Raw 与 Normalized 必须分离

不得修改 raw array。

明确区分：

``` text
raw_response
normalized_response
field_amplitude
```

定义：

``` text
normalized_response = raw_response / max(raw_response)
field_amplitude = sqrt(max(normalized_response, 0))
```

若 `max(raw_response) <= 0`，不得静默除零，返回明确错误如
`INVALID_A_MATRIX_RESPONSE` 并记录 evidence。

调用方必须知道 normalization policy，避免 provenance 混乱。

------------------------------------------------------------------------

# 6. 数据质量检查

每个 entry 至少检查：

``` text
shape == (91, 72)
numeric dtype
finite values
NaN / Inf
negative values
max value
all-zero
```

如果出现负值，不得自动 `abs()`；记录 `DATA_SEMANTICS_WARNING`
或明确失败策略。

原始 `.npy`：

-   不修改；
-   不移动；
-   不覆盖；
-   不 normalize 后写回；
-   不 commit 到 5glosvp。

------------------------------------------------------------------------

# 7. Beam Profile Mapping

从现有 `profiles.json`、loader、mapping 中读取能够直接证明的：

``` text
AAU/profile
beam family
beam_id
entry_key
library
```

禁止凭文件顺序猜映射。映射不完整则 `mapping_status = PARTIAL`。

------------------------------------------------------------------------

# 8. UE Twin V0.1

把 Day 12 schema 升级为实际可用对象：

``` text
ue_id
position
orientation_optional
mobility_state
serving_cell_id
neighbor_cell_ids
traffic_profile
radio_geometry
beam_observations
provenance
```

Day 13 主要实现 position、serving/neighbor context、radio geometry、beam
observations；不实现完整动态 mobility。

Position 必须记录：

``` text
x, y, z
coordinate_system
source
```

若使用 Sionna scene Cartesian
coordinates，应明确标记，不能默认为经纬度。

------------------------------------------------------------------------

# 9. AAU ↔ UE Geometry

建立独立纯函数/服务：

``` text
compute_radio_geometry(aau_position, ue_position, convention)
```

输出：

``` text
distance_3d
azimuth_deg
elevation_deg
coordinate_convention
```

需要数学单测。

Azimuth lookup 前：

``` text
azimuth = azimuth % 360
```

必须覆盖：

``` text
-5°  → 355°
360° → 0°
365° → 5°
```

Elevation 有效范围 `[-90°, +90°]`；人工查询越界必须 validation
error，不静默 wrap。

------------------------------------------------------------------------

# 10. Angular Lookup

Day 13 至少实现可解释的：

``` text
nearest-grid lookup
```

可选 bilinear interpolation。

如果实现 interpolation，必须正确处理 azimuth `355° ↔ 0°` 周期边界。

Evidence/UI 必须暴露 `lookup_method`。

------------------------------------------------------------------------

# 11. Per-Beam Relative Response

给定 AntennaProfile + AAU + UE，输出：

``` text
BeamResponse[]
```

每项至少：

``` text
beam_id
entry_key
azimuth_deg
elevation_deg
normalized_response
rank
```

可选记录 raw_response / field_amplitude，但默认 UI 不需要暴露全部 raw
值。

允许计算 `strongest_beam_id`，其唯一含义是：

> 在当前 A-Matrix
> profile、当前方向和当前归一化响应定义下，相对响应最大的 beam。

禁止称为"吞吐最优波束""最高 RSRP 波束"。

------------------------------------------------------------------------

# 12. Serving / Neighbor Context

UE Twin 可绑定：

``` text
serving_cell_id
neighbor_cell_ids
```

对 serving/neighbor 分别查询相对 beam response。

Day 13 不执行：

``` text
handover decision
cell reselection
load balancing decision
```

这里只是 radio observation/context。

------------------------------------------------------------------------

# 13. Day 8 集成边界

优先复用 Day 8 的 3 Cell / 12 UE 场景作为多小区展示基础。

不得重新生成：

`CH-MULTICELL-FBD449D7`

不得 retroactively 声称历史 Day 8 frozen channel 使用过 A-Matrix。

若历史 Day 8 未使用该数据，则 Day 13 明确标为：

`Day13 visualization/integration overlay`

历史 scientific evidence 不修改。

------------------------------------------------------------------------

# 14. Scenario / Scientific Identity

Day 12 `device_antenna` 维度从 placeholder 升级，可绑定：

``` text
antenna_profile_id
a_matrix_library_id
beam_family
beam_configuration
```

如果 A-Matrix 影响新 Experiment 科学结果，identity 必须绑定：

``` text
a_matrix_artifact_id
a_matrix_hash / manifest hash
antenna_profile_id
normalization_policy
angular_grid_version
lookup_method
```

Comparison 必须区分 same / different / unknown A-Matrix；missing
不得等于 equal。

------------------------------------------------------------------------

# 15. A-Matrix Artifact Manifest

不要复制 raw `.npy` 到 evidence。

建立 manifest：

``` text
artifact_id
source_family
source_file_name
source_hash
entry_count
shape
dtype
angular_grid_version
normalization_policy
profile_mapping_version
semantic_status
```

若 hash 属敏感信息，可只保留本地 reference 并在报告说明。

------------------------------------------------------------------------

# 16. 与 sionnatest 的关系

优先做 adapter / compatible loader，不复制整个 sionnatest
backend，不形成第二套漂移实现。

Day 13 不要求把两个 repository 重构成共享 package，但 Final Report
要说明复用/兼容策略。

继续保留 Fast backend / Sionna backend 边界。A-Matrix normalized pattern
应能作为未来 Sionna antenna-pattern consumer 输入。

不要求大规模重跑 Sionna RT；允许小型 smoke/compatibility test。

------------------------------------------------------------------------

# 17. 前端：A-Matrix / Beam Explorer

新增入口：

``` text
A 矩阵 / 波束方向图
```

至少展示：

``` text
Library
AAU/Profile
Beam Family
Beam ID
91×72 Grid
Normalization
Data Source
Semantic Status
```

至少提供 2D angular heatmap：

``` text
X = Azimuth (deg)
Y = Elevation (deg)
Value = Normalized Relative Response [0,1]
```

支持 Beam selector。

Day 13 不强制 3D 球面渲染；不要为了 3D 拖慢主线。

------------------------------------------------------------------------

# 18. UE Twin Viewer

选择 Scenario / UE / Serving or Neighbor Cell / Antenna Profile 后展示：

``` text
UE position
AAU position
distance
azimuth
elevation
serving cell
neighbor cells
per-beam relative responses
strongest relative beam
```

新 UI 中文优先。

科学标签使用：

``` text
相对波束响应
归一化响应
当前方向最强波束
```

禁止把 normalized response 标成 dBm/dBi/绝对 RSRP/绝对 SINR。

------------------------------------------------------------------------

# 19. Absolute Radio KPI Calibration Gate

建立显式状态：

`ABSOLUTE_RADIO_KPI_NOT_CALIBRATED`

进入绝对 RSRP/SINR 前至少还需确认：

``` text
raw value precise physical meaning
absolute/maximum antenna gain or calibration reference
Tx power semantics
frequency
polarization
system/cable loss if applicable
mechanical/electrical tilt semantics
whether tilt already embedded
coordinate convention owner confirmation
normalization suitability for absolute link budget
```

这些未确认不阻塞：

``` text
normalized pattern
beam visualization
relative angular lookup
UE geometry
relative beam ranking
ray-sampling compatibility
```

但阻塞：

``` text
absolute RSRP
absolute SINR
calibrated link budget
```

------------------------------------------------------------------------

# 20. API / Backend

按项目现有风格实现能力：

``` text
list A-Matrix libraries
list antenna profiles
get beam pattern metadata
get normalized beam pattern
query angular response
get UE twin
query UE beam responses
```

前端不得直接读取服务器 `.npy`。

建议模块：

``` text
src/antenna/
  models.py
  amatrix_adapter.py
  normalization.py
  angular_grid.py
  beam_profiles.py
  geometry.py
  service.py

src/ue_twin/
  ...
```

按现有项目风格调整即可。NumPy/geometry/normalization 逻辑不得塞进
router。

------------------------------------------------------------------------

# 21. Read-only Guarantee

对 A-Matrix 原始文件在 Day 13 前后验证可行的：

``` text
size
mtime
hash
```

Final Report 必须回答：

``` text
A-Matrix original files modified: YES/NO
A-Matrix original files committed: YES/NO
```

------------------------------------------------------------------------

# 22. Tests

A-Matrix 至少：

``` text
91×72 validation
normalization max == 1
all-zero guard
NaN/Inf guard
negative-value policy
raw unchanged
phase_power load
spread load
beam/profile mapping
azimuth wrap
elevation bounds
nearest lookup
interpolation if implemented
355↔0 boundary if interpolation
strongest-beam semantics
```

Geometry/UE Twin 至少：

``` text
UE east/west/north/south
UE above/below
same-position guard
azimuth normalization
elevation range
distance
serving/neighbor context
multiple beams
multiple cells
provenance
```

Scenario/Comparison 至少：

``` text
A-Matrix binding enters identity
different A-Matrix != same scientific condition
missing A-Matrix != equal when required
definition_verified != experiment_verified
acceptance_evidence separate
Day8 frozen artifact unchanged
```

------------------------------------------------------------------------

# 23. Frontend Tests + Browser E2E

前端至少测试：

``` text
A-Matrix Explorer
beam selector
heatmap
normalization label
UE Twin Viewer
geometry values
per-beam response list
strongest relative beam label
calibration warning
Chinese labels
Day12 count semantics
```

真实浏览器：

``` text
Scenario Center
→ 打开带 Device/Antenna binding 的场景
→ A-Matrix / Beam Explorer
→ 选择 library/profile/beam
→ 查看 91×72 normalized heatmap
→ 切换 beam
→ 打开 UE Twin
→ 选择 UE
→ 查看 AAU↔UE geometry
→ 查看 per-beam relative response
→ 查看 strongest relative beam
→ 查看 serving/neighbor context
→ 查看“绝对 RSRP/SINR 未校准”提示
```

要求 `console errors = 0`。

------------------------------------------------------------------------

# 24. Evidence + Independent Verification

建立 `reference/day13/`（或遵循现有 reference 命名）。

至少：

``` text
amatrix-manifest.json
angular-grid.json
beam-profile-mapping.json
ue-twin-example.json
beam-response-example.json
scenario-identity-example.json
verification.json
README.md
```

不 commit raw `.npy`。

独立 verifier 至少重算/验证：

``` text
source files unchanged
manifest metadata consistency
91×72 convention
normalization
angular lookup
geometry
scenario identity
TD-012-01 count semantics
```

Verifier 不应只调用 production service 后比较自身输出。

------------------------------------------------------------------------

# 25. Performance

不得每个请求重新加载整个 A-Matrix library。

至少考虑：

``` text
lazy load
cache
profile-level access
```

记录 cold load / warm query 基础观察即可，不做算法性能竞赛。

------------------------------------------------------------------------

# 26. Day 13 明确不做

``` text
完整 Handover
动态 mobility simulation
beam-space traffic prediction model
measured traffic model
1000-cell scale
大规模 Sionna RT rerun
绝对 RSRP calibration
绝对 SINR calibration
算法优劣比较
算法性能优化
最终 Acceptance Scenario Set 选择
```

------------------------------------------------------------------------

# 27. Stop Conditions

出现任一项停止并报告：

1.  修改原始 `.npy`；
2.  raw `.npy` 加入 Git；
3.  A-Matrix 被解释成 UE-Cell association matrix；
4.  normalized response 标成 dBm/dBi；
5.  用 normalized A-Matrix 单独生成"真实 RSRP"；
6.  用 normalized A-Matrix 单独生成"真实 SINR"；
7.  phase_power/spread 无依据使用不同物理公式；
8.  自动 abs() 修复负值；
9.  all-zero 静默除零；
10. 轴顺序与 `[elevation, azimuth]` 不一致；
11. azimuth wrap 错误；
12. Day8 frozen channel 被重生成；
13. Day8 历史 evidence 被 retroactively 修改；
14. Scenario identity 未绑定 A-Matrix 条件；
15. Comparison identity 被弱化；
16. `verified_count=120` 歧义继续进入验收 UI；
17. 当前 120 definitions 被宣称最终验收场景集；
18. UI 生成伪造 RSRP/SINR；
19. 新增研究算法；
20. browser console error 未解释。

------------------------------------------------------------------------

# 28. Definition of Done

-   [ ] TD-012-01 count semantics fixed
-   [ ] AcceptanceScenarioSet schema/boundary only
-   [ ] AMatrixLibrary / AMatrixEntry
-   [ ] AngularGrid V0.1
-   [ ] phase_power / spread support
-   [ ] raw/normalized separation
-   [ ] peak normalization
-   [ ] data validation
-   [ ] beam/profile mapping
-   [ ] source manifest
-   [ ] source read-only verification
-   [ ] UE Twin V0.1
-   [ ] AAU↔UE geometry
-   [ ] azimuth/elevation conversion
-   [ ] angular lookup
-   [ ] per-beam relative response
-   [ ] strongest relative beam
-   [ ] serving/neighbor context
-   [ ] Scenario Device/Antenna binding
-   [ ] scientific identity update
-   [ ] Comparison regression
-   [ ] A-Matrix Explorer
-   [ ] normalized heatmap
-   [ ] UE Twin Viewer
-   [ ] calibration warning
-   [ ] backend/frontend tests
-   [ ] typecheck/build
-   [ ] browser E2E
-   [ ] console errors 0
-   [ ] independent verifier
-   [ ] Day4--12 regression
-   [ ] evidence + final report
-   [ ] commit + push
-   [ ] clean worktree

------------------------------------------------------------------------

# 29. Final Report 必须逐项回答

1.  Base commit
2.  implementation commit
3.  evidence/docs commit
4.  HEAD / origin/main / worktree
5.  A-Matrix source path
6.  source file count
7.  source files modified YES/NO
8.  source files committed YES/NO
9.  libraries detected
10. phase_power status
11. spread status
12. entry counts
13. raw shape/dtype
14. angular grid version
15. elevation/azimuth convention
16. convention source
17. raw value engineering interpretation
18. normalization policy
19. max normalized response
20. field-amplitude policy
21. negative/zero/NaN/Inf policy
22. profile mapping source/status
23. AAU profiles / beam families / beam IDs
24. AMatrixLibrary/Entry implemented
25. manifest path
26. UE Twin implemented
27. UE/AAU coordinate systems
28. geometry convention
29. distance/azimuth/elevation calculations
30. angular lookup method
31. azimuth wrap/elevation boundary tests
32. interpolation YES/NO
33. per-beam response
34. strongest relative beam
35. serving/neighbor context
36. Day8 integration mode
37. Day8 frozen channel unchanged YES/NO
38. Scenario A-Matrix binding
39. Scenario identity fields
40. Comparison identity behavior
41. TD-012-01 fixed YES/NO
42. definition_verified_count
43. experiment_verified_count
44. acceptance_evidence_count
45. AcceptanceScenarioSet schema
46. final acceptance set selected YES/NO
47. A-Matrix Explorer/heatmap/beam selector
48. UE Twin Viewer
49. relative-response label
50. absolute calibration warning
51. absolute RSRP produced YES/NO
52. absolute SINR produced YES/NO
53. calibration gate status
54. backend tests
55. frontend tests
56. Node/npm
57. typecheck/build
58. browser E2E
59. console errors
60. cold-load/warm-query observation
61. independent verifier/result
62. Day4--12 regressions
63. evidence path
64. known limitations
65. technical debt
66. Day13 Final
67. Day13 Frozen
68. Day14 Ready

------------------------------------------------------------------------

# 30. 允许的最终声明

若证据支持，可以说：

> 平台已接入项目真实 A-Matrix 多波束数据，并按照当前 sionnatest
> 工程约定将其作为归一化相对方向响应使用。

可以说：

> 平台能够基于 UE 与 AAU
> 的空间几何关系查询不同波束在该方向上的相对响应，并进行可视化。

可以说：

> A-Matrix 已进入 Scenario / UE Twin / Beam Profile 的平台数据链。

不能说：

> A-Matrix 已完成绝对天线增益校准。

不能说：

> 平台已基于 A-Matrix 得到物理校准的真实 RSRP/SINR。

不能说：

> strongest relative beam 就是吞吐率最优波束。

------------------------------------------------------------------------

# 31. Day 14 不预设

Day 13 完成后先审：

``` text
A-Matrix integration
UE Twin geometry
beam visualization
identity/evidence
真实前端效果
```

再决定 Day 14：

``` text
Multi-site Radio Observability
RSRP/SINR calibrated integration
Traffic / Beam-space Traffic
Mobility & Handover
Acceptance Scenario Set
Scenario Batch Validation
```

Agent 不得在 Day 13 自动选择 Day 14 路线。

# END OF DAY 13
