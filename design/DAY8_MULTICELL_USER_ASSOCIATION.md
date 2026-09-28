# Day 8 --- Multi-Cell User Association & Load Balancing

## 多小区用户接入与负载均衡：首个任务书对齐的 5G 网优案例

> 项目：5G 网络学习优化仿真验证平台
>
> Day 7 Frozen Baseline
>
> -   HEAD / origin/main: `7b7706874476c2b746d66f688eb68dfaba104d21`
> -   Day 7 Code: `52eb45b`
> -   Day 7 Evidence: `7b77068`
> -   Reference Optimization: `OPT-808014E9`
> -   Algorithm SDK: `0.1`
> -   Day 7 Status: `PASS WITH MINOR DEBT / FROZEN`
>
> Day 8 核心目标：
>
> **第一次实现与任务书"用户接入参数优化"直接对应的、多小区系统级 5G
> 网优案例。**
>
> Day 8
> 的重点不是增加一种高级优化算法，而是建立一个科学可信、可验证、可扩展的：
>
> `Multi-Cell → UE Association → Cell Load → Scheduling → UE Throughput → KPI → Optimization → Evidence`
>
> 闭环。
>
> 本任务书供新 Agent
> 直接执行。必须实际修改代码、测试、真实运行、浏览器验证、保存 Reference
> Evidence、提交并 push。
>
> 不要只输出设计方案。

------------------------------------------------------------------------

# 0. Day 8 与任务书的关系

任务书明确包含三类 5G 网络优化问题：

1.  网络结构参数优化；
2.  用户接入参数优化；
3.  系统资源参数优化。

Day 8 选择：

**用户接入参数优化（User Association）+ Load Balancing**

作为第一个直接任务书对齐的系统级案例。

Day 8 不是最终项目验收。

Day 8 产生：

`Simulation / System Optimization Evidence`

而不是：

`Measured / Huawei / Acceptance Evidence`

------------------------------------------------------------------------

# 1. Day 8 成功标准

Day 8 成功不等于：

"某个算法让吞吐率提升很多"。

真正成功标准是：

1.  至少存在多个真实参与系统计算的 Cell；
2.  UE 有多个候选 serving cells；
3.  Association 决策真实影响系统行为；
4.  Cell load 能由 association 改变；
5.  Scheduling / throughput 使用 association 后的真实系统状态；
6.  Baseline 和 optimized association 在同一公平 Evaluation Context
    下比较；
7.  Network KPI 与 UE-level KPI 可追溯；
8.  负面 trade-off 必须显示；
9.  独立 verifier 能从 artifacts 重算关键结果；
10. EvidenceDescriptor 能把该案例标记为"用户接入参数优化证据"；
11. 不把工程 baseline 冒充科研学习算法；
12. 不把 P5 冒充任务书最终"边缘用户速率"。

------------------------------------------------------------------------

# 2. Day 8 首要原则：先建立 Problem，再谈高级 Algorithm

Day 7 已经证明 Algorithm SDK 工作。

Day 8 不要优先实现：

-   ZO-PGD
-   Reinforcement Learning
-   Deep Learning
-   Bayesian Optimization
-   Project Research Algorithm

Day 8 优先建立：

`USER_ASSOCIATION_V0_1`

优化问题。

高级科研算法留到 Day 9+。

------------------------------------------------------------------------

# 3. 冻结 Day 1--7

禁止修改历史定义来配合 Day 8。

尤其不得修改：

-   Day 4 propagation objective semantics
-   Day 5 KPI definitions
-   Day 6 `SYSTEM_BENCHMARK_V0_1`
-   Day 7 Algorithm SDK 0.1 的历史 evidence
-   `OPT-E56D9514`
-   `EXP-FC79FFC2`
-   `OPT-9A16123C`
-   `OPT-808014E9`

如确实需要新语义：

创建新 version。

不要覆盖历史 version。

------------------------------------------------------------------------

# 4. Day 8 前置 Freeze Check

开始开发前执行：

``` bash
git status
git rev-parse HEAD
git rev-parse origin/main
git log --oneline --decorate -10
```

要求：

-   HEAD == origin/main
-   working tree clean
-   HEAD 包含 `7b77068`

运行合理范围的 Day 4--7 regression。

若基础回归失败：

先停止 Day 8。

------------------------------------------------------------------------

# 5. Day 8 场景：MULTICELL-DEMO-001

新增独立 scenario：

`MULTICELL-DEMO-001`

不要修改：

`SYSTEM-DEMO-001`

建议第一版规模：

-   3 BS
-   3 Cells
-   12--24 UE

推荐从：

-   3 Cells
-   18 UE

开始。

但 Agent 可以根据当前 Sionna backend 的真实能力选择 12/18/24 UE。

必须在最终报告解释选择原因。

------------------------------------------------------------------------

# 6. 为什么至少 3 Cells

2 Cells 可以证明 handover-like association。

但 3 Cells 更容易出现：

-   overlapping coverage
-   uneven load
-   multiple candidate cells
-   load-balancing decision

同时仍然适合 Day 8 的计算预算。

不要 Day 8 直接做 100 Cells。

------------------------------------------------------------------------

# 7. Multi-Cell 必须是真的

禁止仅在 UI 创建：

CELL-001 CELL-002 CELL-003

而实际 Sionna 仍只计算一个 Cell。

至少必须证明：

-   多个 transmitter/cell 对 UE 的 propagation/channel 有贡献；
-   serving-cell assignment 不同会改变对应 UE 的 serving link；
-   非 serving cell 的影响按当前系统模型正确处理；
-   cell-specific load/scheduling 真实存在或以明确的 simulator-neutral
    系统抽象实现。

如果当前 Sionna SYS API 不能原生支持所需的完整多小区 scheduler：

可以建立经过明确标注的：

`MultiCellSystemModel V0.1`

但必须真实使用 Sionna RT / channel-derived link information。

禁止伪造 throughput。

------------------------------------------------------------------------

# 8. 先做 Capability Spike

正式实现前，写：

`DAY8_MULTICELL_SPIKE.md`

回答：

1.  当前 Sionna 2.1.0 的 RT 能否同时提供多个 BS → UE link/channel？
2.  当前使用的 Sionna SYS pipeline 是否原生支持 multi-cell
    scheduling/inter-cell interference？
3.  如果不支持，最小可信 bridge architecture 是什么？
4.  哪些计算来自 Sionna？
5.  哪些计算来自平台自己的 system abstraction？
6.  是否仍然保持 simulator-neutral？
7.  association 改变后哪些量需要重新计算？
8.  哪些量可以复用 frozen propagation/channel？
9.  预计一次 evaluation runtime？
10. Day 8 GO / NO-GO。

Spike 必须先提交到 evidence/docs 或最终 commit 中。

------------------------------------------------------------------------

# 9. 不允许为了"多小区"退化成假公式

禁止：

`throughput = signal_strength * arbitrary_factor`

禁止：

`load = UE_count; throughput = bandwidth/load`

作为最终 Day 8 Reference Backend 的全部系统模型。

可以使用明确的资源共享抽象，但必须建立在：

-   Sionna-derived channel/link quality
-   defined scheduler/resource model
-   defined SINR/spectral-efficiency/throughput chain

之上。

------------------------------------------------------------------------

# 10. Multi-Cell Canonical Model

新增或扩展 canonical entities：

`BaseStation`

`Cell`

`UE`

`CandidateServingCell`

`Association`

`CellLoad`

不要让前端直接依赖 Sionna object。

------------------------------------------------------------------------

# 11. Cell

至少：

``` text
cell_id
bs_id
position
carrier_frequency
bandwidth
tx_power
antenna_config
status
```

如已有 canonical schema：

扩展，不要重复建立平行模型。

------------------------------------------------------------------------

# 12. UE Candidate Cells

对每个 UE 保存：

``` text
ue_id
candidate_cells[]
```

每个 candidate 至少：

``` text
cell_id
link_available
link_metric(s)
```

候选 cell 生成规则必须版本化。

例如：

`CANDIDATE_CELL_POLICY_V0_1`

------------------------------------------------------------------------

# 13. Candidate Cell Policy

Day 8 推荐：

从存在有效 propagation path 的 cells 中选候选。

如果需要 Top-K：

例如 Top-3 RSRP/link gain。

必须记录：

-   K
-   metric
-   tie rule
-   no-path behavior

不要把规则埋在代码里。

------------------------------------------------------------------------

# 14. Association

正式定义：

``` text
AssociationAssignment
ue_id -> serving_cell_id
```

Association 是：

**网络优化变量**

不是：

Algorithm Hyperparameter。

------------------------------------------------------------------------

# 15. Association Parameter Type

这是 Day 7 `categorical` / `vector` schema 第一次真正落地。

概念上：

``` text
association = [
  UE1 -> CELL2,
  UE2 -> CELL1,
  UE3 -> CELL3,
  ...
]
```

属于：

`categorical vector`

如果 SDK 0.1 无法自然表达：

以向后兼容方式扩展 SDK 到 `0.2`。

不要破坏 0.1。

------------------------------------------------------------------------

# 16. Feasibility Constraints

至少：

每个 active UE：

-   必须且只能关联一个 serving cell；
-   serving cell 必须属于其 candidate cells；
-   serving link 必须可用；
-   disabled cell 不得被选择。

违反约束：

candidate rejected

而不是 simulator crash。

------------------------------------------------------------------------

# 17. Optional Capacity Constraint

Day 8 不要人为规定：

"每 Cell 最多 N UE"

除非系统模型确实需要。

Load balancing 应主要由：

资源竞争 / scheduler / objective

产生，而不是硬编码漂亮均衡。

------------------------------------------------------------------------

# 18. Baseline Association

必须定义并版本化：

`ASSOCIATION_BASELINE_V0_1`

推荐 baseline：

**Best-RSRP / strongest-link association**

或当前 canonical link metric 下的：

**Best Serving Link**

Agent 必须确认现有数据支持哪个。

------------------------------------------------------------------------

# 19. Baseline 不能偷偷做 Load Balancing

Baseline 的目的：

提供工程参考。

不要为了让优化增益变漂亮，故意使用明显糟糕 baseline。

------------------------------------------------------------------------

# 20. Baseline Tie Rule

必须固定。

例如：

metric equal → lexicographically smallest cell_id

或 deterministic cell order。

禁止随机 tie。

------------------------------------------------------------------------

# 21. Cell Load

定义：

`CELL_LOAD_V0_1`

Day 8 至少记录两类 load：

1.  Associated UE Count
2.  Resource / scheduling load（如果 backend 能可靠给出）

不要把二者混为一个 KPI。

------------------------------------------------------------------------

# 22. Load Imbalance Metric

可以增加工程诊断指标：

`CELL_UE_COUNT_CV_V0_1`

例如：

Cell associated UE counts 的 coefficient of variation。

但：

它是 engineering diagnostic。

不是任务书验收 KPI。

------------------------------------------------------------------------

# 23. Day 8 KPI

继续复用 Day 5 已冻结：

-   Network Throughput
-   Average UE Throughput
-   P5 UE Throughput

如语义完全相同：

不要重新定义新版本。

------------------------------------------------------------------------

# 24. 新增 Multi-Cell Diagnostic KPI

建议：

-   Per-cell Throughput
-   Associated UE Count per Cell
-   Per-cell Average UE Throughput
-   Load Imbalance

这些属于：

diagnostic/system metrics。

------------------------------------------------------------------------

# 25. P5 的科学边界继续保持

P5 UE Throughput：

仍然是工程指标。

必须继续标：

`NOT official acceptance edge-user rate`

不要在 Day 8 改名成：

Edge User Rate。

------------------------------------------------------------------------

# 26. Inter-Cell Interference

这是 Day 8 最大科学风险之一。

必须明确当前模型属于哪一种：

A. Full inter-cell interference modeled

B. Approximate inter-cell interference modeled

C. Orthogonal/interference-isolated cells

D. Interference not modeled

Reference Evidence 必须写清楚。

------------------------------------------------------------------------

# 27. 禁止隐瞒干扰模型

如果 Day 8 bridge 还不能实现完整 inter-cell interference：

允许。

但 UI / README 必须明确：

`Inter-cell interference model: <actual state>`

不能让用户以为是完整现网 multi-cell PHY。

------------------------------------------------------------------------

# 28. Channel Reuse Policy

建立：

`PropagationDependencyPolicy`

至少区分：

`REUSE_CHANNEL`

和：

`RERUN_PROPAGATION`

Association 改变：

如果没有改变：

-   BS/UE position
-   antenna geometry/pattern
-   carrier frequency
-   environment/material

则应优先复用同一组 BS→UE propagation/channel realization。

------------------------------------------------------------------------

# 29. Day 8 不因为 Association 改变而重新 Ray Trace

如果 association 只是从已有 candidate links 中选择 serving cell：

应该复用 frozen multi-BS→UE propagation realization。

这样才能保证：

candidate differences 来自 association，

而不是 RT drift。

------------------------------------------------------------------------

# 30. Multi-Cell Channel Realization

新增：

`MultiCellChannelRealization`

至少：

``` text
channel_realization_id
sha256
bs/cell set
ue population
frequency
scene
seed
link set
```

------------------------------------------------------------------------

# 31. Fair Evaluation Context

新增/扩展：

`MultiCellEvaluationContext`

至少冻结：

``` text
scenario_id
scenario_version
ue_population_id
candidate_cell_policy
channel_realization_id
traffic_realization_id
simulation_horizon
backend
backend_version
scheduler
link_adaptation
interference_model
association_baseline
kpi_versions
objective_version
```

------------------------------------------------------------------------

# 32. Fairness Checks

至少：

Same Scenario

Same UE

Same Candidate Cells

Same Channel Realization

Same Traffic

Same Horizon

Same Backend

Same Scheduler

Same Link Adaptation

Same Interference Model

Only Association Changed

------------------------------------------------------------------------

# 33. Objective：不要再单纯追求 Network Throughput

Day 6 已经证明：

只最大化 Network Throughput

可能明显牺牲 P5。

Day 8 应第一次引入：

**constraint-aware optimization**

而不是随便发明多目标权重。

------------------------------------------------------------------------

# 34. Day 8 推荐 Objective

定义：

`NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1`

概念：

``` text
maximize Network Throughput

subject to:

P5 UE Throughput >= baseline P5 UE Throughput
```

------------------------------------------------------------------------

# 35. 为什么用 Baseline P5 Floor

因为任务书最终"边缘用户速率"正式口径仍未确认。

所以 Day 8 不设置：

"P5 ≥ 某个验收数字"。

只使用：

**不低于当前 baseline P5**

作为工程约束。

------------------------------------------------------------------------

# 36. Constraint 不是 Acceptance KPI

必须明确：

`P5 floor`

是：

Day 8 engineering optimization constraint。

不是：

项目最终边缘用户验收指标。

------------------------------------------------------------------------

# 37. Constraint Evaluation

每个 candidate：

``` text
feasible = all constraints satisfied
```

至少记录：

``` text
network_throughput
p5_throughput
p5_floor
p5_margin
feasible
```

------------------------------------------------------------------------

# 38. Candidate Selection

Best candidate：

只从：

`feasible candidates`

中选择。

不可行 candidate：

即使 Network Throughput 更高：

也不能成为 best。

------------------------------------------------------------------------

# 39. 如果没有 Candidate 改善 Baseline

完全允许：

Best = Baseline

这仍然是 Day 8 PASS。

禁止：

调 seed

改 UE

改 baseline

改 constraint

只为了产生漂亮提升。

------------------------------------------------------------------------

# 40. Day 8 Algorithm：工程 Baseline 即可

不要 Day 8 实现 ZO。

Association 是组合变量。

第一版推荐：

`Greedy Load-Aware Association Search`

或等价、可审计的工程 baseline。

------------------------------------------------------------------------

# 41. Greedy Load-Aware Search

要求：

-   `learning_algorithm=false`
-   category=`engineering_baseline`
-   deterministic
-   uses platform evaluation
-   obeys evaluation budget
-   uses Algorithm SDK

------------------------------------------------------------------------

# 42. 不要暴力穷举所有 Association

若：

18 UE × 3 candidates

理论组合空间可达：

`3^18`

禁止全部枚举。

Day 8 的目的之一就是证明：

组合优化空间存在。

------------------------------------------------------------------------

# 43. 推荐搜索策略

从 baseline 开始：

1.  识别 overloaded / low-performing region；
2.  选择一个有替代 serving cell 的 UE；
3.  提议单 UE reassociation；
4.  平台 evaluate；
5.  接受满足 constraint 且 objective 更优的 move；
6.  继续；
7.  budget / no-improvement 停止。

------------------------------------------------------------------------

# 44. 算法不得直接访问 Sionna

继续遵守 Day 7：

Algorithm → Evaluation Interface → Platform → Backend

------------------------------------------------------------------------

# 45. 算法不得自己算 KPI

继续：

Backend → KPI Engine → Constraint / Objective Engine → Algorithm
Observation

------------------------------------------------------------------------

# 46. Association Move Trace

每次 move 记录：

``` text
iteration
ue_id
from_cell
to_cell
reason
objective_before
objective_after
p5_before
p5_after
feasible
accepted
```

------------------------------------------------------------------------

# 47. "reason" 不要伪造 AI 解释

可以记录规则事实：

`candidate move generated from overloaded cell`

不要写：

"AI believes this UE should move"。

------------------------------------------------------------------------

# 48. Evaluation Budget

必须配置：

`max_evaluations`

建议根据 spike runtime 选择。

不要固定照抄 Day 7 的 8。

最终报告说明：

为什么是该 budget。

------------------------------------------------------------------------

# 49. Cache / Dedup

继续复用 Day 7。

相同：

Evaluation Context + Association Vector

应复用 evaluation。

------------------------------------------------------------------------

# 50. Association Hash

每个 association 保存：

`association_hash`

使用 canonical deterministic serialization。

------------------------------------------------------------------------

# 51. Optimization Problem

新增：

`problem_type = user_association`

不要继续把所有问题都塞进：

`system`

------------------------------------------------------------------------

# 52. Problem Metadata

至少：

``` text
problem_id
problem_type
task_category
scenario
parameter_space
constraints
objective
baseline_policy
evaluation_protocol
```

其中：

`task_category = user_access_parameter_optimization`

------------------------------------------------------------------------

# 53. Acceptance Traceability Tag

EvidenceDescriptor 增加或使用已有 metadata：

``` text
task_book_mapping:
  category: user_access_parameter_optimization
  evidence_level: simulation
```

注意：

这只是：

任务书能力映射。

不是：

验收通过。

------------------------------------------------------------------------

# 54. Evidence Level

Day 8：

`L1/L2 simulation evidence`

按当前平台已有命名保持一致。

必须：

Measured = NO

Huawei = NO

Acceptance Eligible = NO

------------------------------------------------------------------------

# 55. API

增加或自然扩展：

``` text
GET /api/v1/multicell/scenarios
GET /api/v1/multicell/scenarios/{id}
POST /api/v1/optimizations
GET /api/v1/optimizations/{id}
```

不要为了 Day 8 重建第二套 Optimization API。

------------------------------------------------------------------------

# 56. Scenario API

返回：

-   BS count
-   Cell count
-   UE count
-   candidate-cell summary
-   frequency
-   bandwidth
-   backend compatibility
-   interference model

------------------------------------------------------------------------

# 57. Association API Representation

必须稳定、明确。

例如：

``` json
{
  "UE-001": "CELL-002",
  "UE-002": "CELL-001"
}
```

或 typed list。

保持 deterministic ordering。

------------------------------------------------------------------------

# 58. Frontend --- Scenario Center

`MULTICELL-DEMO-001`

必须可查看：

-   BS / Cell
-   UE
-   candidate serving cells
-   baseline serving cell
-   network scale

------------------------------------------------------------------------

# 59. Map / Visualization

Day 8 应增加非常有价值的：

**Association Map**

显示：

-   BS / Cell
-   UE
-   serving relationship
-   baseline / optimized toggle

------------------------------------------------------------------------

# 60. 不要求 Day 8 做复杂 3D

优先：

2D / 2.5D 清晰关系图。

不要为炫酷 3D 延误核心系统逻辑。

------------------------------------------------------------------------

# 61. Association Map 颜色规则

使用前端现有 theme / accessible palette。

同一 Cell：

UE serving relationship 一致标识。

Baseline / Optimized：

不能让颜色含义变化导致误判。

------------------------------------------------------------------------

# 62. Optimization Center

新增问题类型：

`User Association / 用户接入`

与已有：

Propagation

System

并列。

------------------------------------------------------------------------

# 63. Create Optimization

选择：

Scenario

Problem Type

Baseline Policy

Algorithm

Objective

Constraint

Evaluation Budget

------------------------------------------------------------------------

# 64. Day 8 Objective UI

必须显示：

``` text
Objective:
Maximize Network Throughput

Constraint:
P5 UE Throughput >= Baseline P5
```

并显示：

`Engineering constraint — not acceptance edge-user KPI`

------------------------------------------------------------------------

# 65. Running Stages

真实阶段：

``` text
Freeze Context
Build Candidate Cells
Run Baseline
Generate Association Move
Evaluate Candidate
Check Constraint
Update Best
Verify
Persist Evidence
```

不要 fake progress percentage。

------------------------------------------------------------------------

# 66. Optimization Detail --- Overview

显示：

-   Optimization ID
-   Scenario
-   Problem Type
-   Algorithm
-   Objective
-   Constraint
-   Evaluation Budget
-   Stop Reason
-   Evidence Status

------------------------------------------------------------------------

# 67. Baseline vs Best

至少：

``` text
Network Throughput
Average UE Throughput
P5 UE Throughput
Feasibility
Cell UE Counts
Per-cell Throughput
```

------------------------------------------------------------------------

# 68. Trade-off

如果：

Network ↑ P5 ↓ but still \>= floor

必须显示：

P5 decreased but remained feasible.

如果：

candidate violates P5 floor

显示：

Rejected by constraint.

------------------------------------------------------------------------

# 69. Per-UE Table

至少：

``` text
UE
Baseline Cell
Optimized Cell
Before Throughput
After Throughput
Delta
```

------------------------------------------------------------------------

# 70. Per-Cell Table

至少：

``` text
Cell
Baseline UE Count
Optimized UE Count
Baseline Throughput
Optimized Throughput
```

------------------------------------------------------------------------

# 71. Association Changes

单独显示：

``` text
UE-xxx
CELL-A → CELL-B
```

不要让用户从两个大表自己找差异。

------------------------------------------------------------------------

# 72. Candidate History

显示：

-   iteration
-   move
-   objective
-   P5
-   feasible
-   accepted
-   best-so-far

------------------------------------------------------------------------

# 73. Evidence Panel

继续显示：

Same UE

Same Channel

Same Traffic

Same Horizon

Only Association Changed

Independent Verification

Measured

Huawei

Acceptance Eligible

------------------------------------------------------------------------

# 74. Acceptance Center --- Day 8 第一次加入 Task Capability Mapping

不要全面建设 Acceptance Center。

但可以把 Day 8 EvidenceDescriptor 映射到：

``` text
Task Category:
用户接入参数优化

Capability:
Multi-Cell User Association Optimization

Evidence:
Available — Simulation

Measured Validation:
Not Available

Acceptance Eligible:
NO
```

------------------------------------------------------------------------

# 75. 不显示 Acceptance PASS/FAIL

仍然禁止：

``` text
用户接入优化：PASS
```

应该：

``` text
Simulation Evidence: Available
Acceptance Evidence: Not Available
```

------------------------------------------------------------------------

# 76. Independent Verification

新增：

`verify_user_association.py`

或自然扩展现有 verifier。

必须独立检查：

1.  Scenario identity
2.  BS/Cell/UE counts
3.  Candidate cell sets
4.  Baseline association
5.  Candidate association vectors
6.  Association hashes
7.  Feasibility
8.  Same channel hash
9.  Same traffic
10. Same horizon
11. KPI recomputation
12. P5 floor
13. Candidate feasible flags
14. Best selection
15. Move trace
16. Per-cell counts
17. Per-UE results
18. EvidenceDescriptor

------------------------------------------------------------------------

# 77. Verifier 独立性

不得导入：

-   production association optimizer
-   production objective evaluator
-   production constraint evaluator

KPI 独立性沿用 Day 5--7 的严格规则。

------------------------------------------------------------------------

# 78. Tamper Tests

至少证明 verifier 能发现：

-   tampered association
-   invalid serving cell
-   tampered channel hash
-   tampered network throughput
-   tampered P5
-   hidden constraint violation
-   wrong best candidate
-   tampered per-cell count

------------------------------------------------------------------------

# 79. Backend Unit Tests --- Multi-Cell Model

至少：

``` text
test_multicell_scenario
test_cell_identity
test_ue_candidate_cells
test_candidate_policy_deterministic
test_no_path_excluded
test_baseline_association
test_baseline_tie_rule
```

------------------------------------------------------------------------

# 80. Association Validation Tests

至少：

``` text
test_exactly_one_serving_cell
test_serving_cell_in_candidates
test_disabled_cell_rejected
test_invalid_cell_rejected
test_association_hash_deterministic
```

------------------------------------------------------------------------

# 81. Objective / Constraint Tests

至少：

``` text
test_p5_floor_from_baseline
test_candidate_above_floor_feasible
test_candidate_below_floor_infeasible
test_infeasible_candidate_cannot_win
test_baseline_remains_valid_fallback
```

------------------------------------------------------------------------

# 82. Algorithm Tests

至少：

``` text
test_load_aware_algorithm_metadata
test_learning_algorithm_false
test_first_move
test_move_uses_observation
test_budget_enforced
test_duplicate_move_dedup
test_no_improvement_stop
test_determinism
```

------------------------------------------------------------------------

# 83. Evaluation Context Tests

至少：

``` text
test_same_channel_reused
test_same_ue_population
test_same_candidate_sets
test_same_traffic
test_same_horizon
test_only_association_changes
```

------------------------------------------------------------------------

# 84. Sionna Integration Tests

必须至少有一个真实：

3 Cell + Multi-UE

integration test。

验证：

-   multi-BS/UE link data
-   association changes system input
-   channel reuse
-   actual KPI output

不要只使用 FakeBackend。

------------------------------------------------------------------------

# 85. Performance Test

记录：

-   propagation/channel build time
-   baseline evaluation time
-   candidate evaluation time
-   total optimization time
-   cache effect

这将帮助后续规模化。

------------------------------------------------------------------------

# 86. Frontend Tests

至少覆盖：

-   User Association problem type
-   Multi-cell scenario
-   association map data
-   create form
-   constraint display
-   baseline/best
-   candidate history
-   per-UE
-   per-cell
-   Evidence Panel
-   Acceptance mapping

------------------------------------------------------------------------

# 87. Browser Smoke

真实浏览器：

``` text
Home
→ Scenario Center
→ MULTICELL-DEMO-001
→ inspect cells/UE
→ Optimization Center
→ User Association
→ Create
→ Run
→ Running Stages
→ Result
→ Association Map
→ Baseline/Optimized
→ Candidate History
→ Candidate Experiment
→ Back
→ Evidence
→ Acceptance Center
```

Console Errors = 0。

------------------------------------------------------------------------

# 88. Reference Optimization

创建真实：

`OPT-XXXXXXXX`

不要 fixture。

保存：

`reference/user_association/OPT-XXXXXXXX/`

------------------------------------------------------------------------

# 89. Reference Evidence Files

至少：

``` text
README.md
scenario.json
candidate-cells.json
evaluation-context.json
baseline-association.json
optimization.json
candidate-history.json
association-trace.json
kpi.json
per-ue.json
per-cell.json
verification.json
evidence-descriptor.json
```

根据当前 artifact architecture 合理合并。

不要为了凑文件数重复数据。

------------------------------------------------------------------------

# 90. Reference Plots

至少：

1.  Association Before / After
2.  Cell Load Before / After
3.  KPI Before / After
4.  Candidate History

图必须由真实 artifact 数据生成。

------------------------------------------------------------------------

# 91. Screenshots

至少覆盖：

-   scenario
-   association visualization
-   create
-   running
-   result overview
-   KPI
-   per-UE
-   per-cell
-   candidate history
-   evidence
-   acceptance mapping

------------------------------------------------------------------------

# 92. Reference README 必须明确

``` text
Purpose:
Multi-Cell User Association Simulation Validation

Task-book Mapping:
User Access Parameter Optimization

Measured:
NO

Huawei Data:
NO

Acceptance Evidence:
NO

Acceptance Eligible:
NO

Learning Algorithm:
NO

Official Edge User Rate:
NO
```

------------------------------------------------------------------------

# 93. Allowed Claim

如果得到提升，只允许：

> 在当前冻结的多小区仿真场景、信道
> realization、业务模型和评价协议下，优化后的用户接入配置使网络吞吐率从
> X 提高到 Y，同时 P5 UE 吞吐率满足不低于 baseline 的工程约束。

------------------------------------------------------------------------

# 94. Forbidden Claims

禁止：

-   "5G 网络吞吐率提高 X%"
-   "现网提升 X%"
-   "项目吞吐指标提升 X%"
-   "边缘用户速率达标"
-   "完成用户接入验收"
-   "AI 自动优化网络"
-   "学习优化算法提升 X%"

------------------------------------------------------------------------

# 95. 如果 P5 下降但仍满足 floor

如果 constraint 定义是：

`P5 >= baseline P5`

那么实际上不能下降。

注意浮点容差必须严格定义。

例如：

``` text
p5 + tolerance >= baseline_p5
```

tolerance 只处理数值误差。

禁止用 5% tolerance 偷偷允许真实性能下降。

------------------------------------------------------------------------

# 96. 如果希望允许微小 P5 trade-off

不要 Day 8 临时改规则。

建立新 objective/constraint version。

V0.1 保持：

`P5 >= baseline P5`

------------------------------------------------------------------------

# 97. Edge Cases

必须处理：

-   UE 只有一个 candidate cell
-   UE 没有 candidate cell
-   all UEs prefer same cell
-   candidate produces empty cell
-   candidate moves UE to worse link
-   duplicate association
-   baseline already optimal
-   no feasible improvement

------------------------------------------------------------------------

# 98. UE 无 Candidate Cell

不得静默删除。

明确：

-   inactive/unserved
-   scenario invalid

选择一种政策并版本化。

Reference Scenario 应尽量保证 active UE 有至少一个 candidate。

------------------------------------------------------------------------

# 99. Empty Cell

允许一个 cell 最终 0 associated UE。

不要强制每 cell 都有人。

除非算法/模型有明确要求。

------------------------------------------------------------------------

# 100. Scientific Limitation

Day 8 README 至少讨论：

-   small multi-cell scenario
-   simulation only
-   traffic model
-   interference model
-   scheduler abstraction
-   finite simulation horizon
-   one/few channel realization
-   P5 not official edge KPI
-   engineering baseline algorithm
-   no measured-data calibration

------------------------------------------------------------------------

# 101. Day 7 Provenance Debt

不要修改历史 `OPT-808014E9`。

但 Day 8 新 run 必须改善 provenance：

至少记录：

``` text
git_commit
working_tree_dirty
```

推荐：

``` text
diff_hash
```

如果实现成本合理。

------------------------------------------------------------------------

# 102. Acceptance Mode Dirty Rule

如果已有 `/acceptance` mode：

Day 8 可以增加规则：

`working_tree_dirty=true`

→ `acceptance_eligible=false`

但当前 Day 8 本来就是 false。

不要阻止 normal/demo 开发运行。

------------------------------------------------------------------------

# 103. Day 8 Algorithm SDK

如果不需要扩展：

保持 0.1。

如果 categorical vector / constraints 需要真实接口变化：

升级：

`0.2`

并提供：

0.1 backward compatibility tests。

最终报告必须说明。

------------------------------------------------------------------------

# 104. 不要为了 Day 8 过度抽象

禁止 Day 8 顺手实现：

-   arbitrary graph optimization framework
-   distributed optimizer
-   generic RL environment
-   arbitrary plugin loader
-   Kubernetes
-   microservices
-   universal constraint DSL
-   1000-cell runtime

只做支持当前案例和未来自然扩展所需的最小抽象。

------------------------------------------------------------------------

# 105. Day 8 Definition of Done

全部满足才完成：

-   [ ] Day 7 freeze baseline confirmed
-   [ ] Day 4--7 regressions PASS
-   [ ] Multi-cell capability spike completed
-   [ ] `MULTICELL-DEMO-001`
-   [ ] \>= 3 real participating cells
-   [ ] Multi-UE
-   [ ] candidate serving cells
-   [ ] deterministic candidate-cell policy
-   [ ] baseline association policy
-   [ ] categorical/vector association representation
-   [ ] feasibility validation
-   [ ] frozen multi-cell channel realization
-   [ ] channel hash
-   [ ] channel reused across candidates
-   [ ] inter-cell interference model explicitly documented
-   [ ] cell load model
-   [ ] per-cell metrics
-   [ ] existing network/avg/P5 KPI reused correctly
-   [ ] P5 remains engineering metric
-   [ ] `NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1`
-   [ ] P5 baseline floor constraint
-   [ ] infeasible candidates cannot win
-   [ ] engineering association optimizer
-   [ ] learning_algorithm=false
-   [ ] Algorithm SDK used
-   [ ] evaluation budget
-   [ ] cache/dedup
-   [ ] association trace
-   [ ] `problem_type=user_association`
-   [ ] task-book mapping metadata
-   [ ] EvidenceDescriptor
-   [ ] acceptance_eligible=false
-   [ ] Scenario UI
-   [ ] Association Map
-   [ ] Optimization Create
-   [ ] Constraint UI
-   [ ] Baseline vs Best
-   [ ] per-UE table
-   [ ] per-cell table
-   [ ] association changes
-   [ ] candidate history
-   [ ] Evidence Panel
-   [ ] Acceptance Center simulation mapping
-   [ ] independent verifier
-   [ ] tamper tests
-   [ ] real Sionna integration
-   [ ] backend tests PASS
-   [ ] frontend tests PASS
-   [ ] typecheck PASS
-   [ ] build PASS
-   [ ] browser smoke PASS
-   [ ] console errors = 0
-   [ ] reference evidence
-   [ ] screenshots
-   [ ] provenance cleanly recorded
-   [ ] Git commit
-   [ ] Evidence commit
-   [ ] Push

------------------------------------------------------------------------

# 106. Cursor / Agent 最终报告必须按此顺序

1.  Code Commit
2.  Evidence Commit
3.  HEAD / origin/main
4.  Working Tree
5.  Changed Files
6.  Sionna Version
7.  Algorithm SDK Version
8.  Day 8 Spike Verdict
9.  Multi-cell Architecture
10. Which computations come from Sionna
11. Which computations come from platform abstraction
12. Inter-cell Interference Model
13. Scenario ID
14. BS Count
15. Cell Count
16. UE Count
17. Candidate Cell Policy
18. Candidate Cell Statistics
19. Channel Realization ID
20. Channel Hash
21. Traffic Model
22. Simulation Horizon
23. Baseline Association Policy
24. Baseline Association
25. Problem Type
26. Task-book Mapping
27. Algorithm ID
28. Algorithm Version
29. Algorithm Category
30. learning_algorithm
31. Parameter Space
32. Constraints
33. Objective ID
34. Evaluation Budget
35. Evaluations Used
36. Cache Hits
37. Stop Reason
38. Baseline Experiment ID
39. Candidate Experiment IDs
40. Association Moves
41. Best Candidate
42. Baseline Network Throughput
43. Best Network Throughput
44. Relative Change
45. Baseline Average UE Throughput
46. Best Average UE Throughput
47. Baseline P5
48. Best P5
49. P5 Floor
50. P5 Margin
51. Feasible
52. Per-UE Before/After
53. Per-cell Before/After
54. Baseline Cell Loads
55. Best Cell Loads
56. Same Scenario
57. Same UE
58. Same Candidate Cells
59. Same Channel
60. Same Traffic
61. Same Horizon
62. Same Backend
63. Same Scheduler
64. Same Interference Model
65. Only Association Changed
66. Independent Verification
67. Tamper Tests
68. Backend Unit Tests
69. Association Tests
70. Objective/Constraint Tests
71. Algorithm Tests
72. API Tests
73. Real Sionna Integration
74. Full Backend Regression
75. Frontend Tests
76. Typecheck
77. Build
78. Browser Smoke
79. Console Errors
80. Reference Evidence Path
81. Screenshots
82. EvidenceDescriptor
83. verified
84. measured
85. Huawei Data
86. acceptance_eligible
87. Acceptance Center Mapping
88. Provenance Commit
89. working_tree_dirty at run time
90. Assumptions
91. Known Limitations
92. Day 4 Regression
93. Day 5 Regression
94. Day 6 Regression
95. Day 7 Regression
96. Technical Debt
97. Day 9 Ready YES/NO

------------------------------------------------------------------------

# 107. 推荐执行顺序

A. Pull / environment check

B. Confirm Day 7 frozen HEAD

C. Regression smoke

D. Read current Sionna backend

E. Read Sionna 2.1.0 multi-cell relevant APIs/code already installed

F. Write capability spike

G. Decide GO / bridge architecture

H. Canonical multi-cell model

I. Scenario `MULTICELL-DEMO-001`

J. Candidate Cell Policy

K. Frozen Multi-Cell Channel Realization

L. Baseline Association

M. Multi-cell system evaluation

N. Validate KPI chain

O. Per-cell metrics

P. P5 floor constraint

Q. Objective

R. Association representation / ParameterSpace

S. Association optimizer

T. Algorithm SDK integration

U. Evaluation budget

V. Cache / dedup

W. Optimization service

X. API

Y. Backend tests

Z. Real Sionna integration tests

AA. Independent verifier

AB. Tamper tests

AC. Scenario UI

AD. Association Map

AE. Optimization Create

AF. Running stages

AG. Result Overview

AH. Per-UE / Per-cell

AI. Candidate History

AJ. Evidence Panel

AK. Acceptance Center mapping

AL. Frontend tests

AM. Typecheck

AN. Build

AO. Real reference optimization

AP. Independent verification

AQ. Browser smoke

AR. Console check

AS. Export reference evidence

AT. Screenshots

AU. Full regression

AV. Scientific wording review

AW. Git diff review

AX. Code commit

AY. Evidence commit

AZ. Push

BA. Final report

------------------------------------------------------------------------

# 108. Stop Conditions

立即停止并报告，不要硬做，如果：

1.  当前 Sionna backend 无法产生可信的 multi-BS→UE link information；
2.  只能通过随机造 throughput 才能完成多小区；
3.  association candidate 之间无法共享同一 channel realization；
4.  无法证明 association 真正进入 system evaluation；
5.  Day 4--7 regression 被破坏且不能定位；
6.  Reference result 只能通过调 seed 才产生 improvement。

这些情况下：

Day 8 = NO-GO

给出最小修复建议。

不要伪造完成。

------------------------------------------------------------------------

# 109. Day 8 科学完整性

Day 8 Reference 的价值优先级：

1.  Association 真实进入计算
2.  公平比较
3.  Constraint 正确
4.  Evidence 可追溯
5.  Independent Verification
6.  Task-book capability mapping
7.  KPI improvement magnitude

最后一项最低。

------------------------------------------------------------------------

# 110. Day 8 完成后的平台能力

完成后平台应该第一次具备：

``` text
Multi-Cell Scenario
        ↓
Multiple Candidate Serving Cells
        ↓
Baseline Association
        ↓
Association Optimization
        ↓
Frozen Propagation Context
        ↓
Cell Load / Scheduling
        ↓
UE Throughput
        ↓
Network + UE KPI
        ↓
Constraint-aware Selection
        ↓
Independent Verification
        ↓
EvidenceDescriptor
        ↓
Task-book Capability Mapping
```

------------------------------------------------------------------------

# 111. Day 9 Preview --- 不要实现

Day 9 才研究：

**First Research Optimization Algorithm**

优先调研/候选：

-   Zeroth-Order Optimization
-   ZO-PGD
-   Block-coordinate ZO

但必须根据 Day 8 最终形成的真实 parameter space 判断。

如果 User Association 是纯离散组合变量：

不要强行把 continuous ZO-PGD 套进去。

Day 9 应选择与问题结构匹配的研究算法，或者另建适合 ZO
的连续网络参数案例。

------------------------------------------------------------------------

# 112. Final Instruction

现在执行 Day 8。

核心不是：

"做一个多小区页面"。

核心是：

``` text
真实 Multi-Cell
        ↓
真实 Candidate Links
        ↓
真实 Association Variable
        ↓
真实 System Evaluation
        ↓
真实 KPI
        ↓
Constraint-aware Optimization
        ↓
Independent Evidence
```

如果当前 Sionna 能力不支持某一层：

明确建立并标注 bridge abstraction。

不要伪造完整 PHY 能力。

完成后：

Tests → Real Reference Run → Independent Verification → Browser E2E →
Evidence → Git Commit → Push → Final Report

然后停止。

# END OF DAY 8
