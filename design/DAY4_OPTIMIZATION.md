# Day 4 — Optimization Loop V0.2 / 优化闭环 V0.2

> 项目：5G 网络学习优化仿真验证平台
> Project: 5G Learning Optimization Simulation & Validation Platform
>
> 当前基线 Commit：`1a46e65`
>
> 阶段：Day 4 — Optimization Loop
>
> **这是开发执行任务书。Cursor Auto 应直接修改代码、运行测试、执行真实 Sionna 优化实验、验证前端并提交 Git。不要只输出设计方案。**

---

# 0. Day 4 核心目标

前三天已经完成：

```text
Scenario
场景
   ↓
Experiment
实验
   ↓
Sionna RT
仿真
   ↓
Result
结果
   ↓
Web Visualization
可视化
```

Day 4 增加：

```text
Optimizer
优化器
```

最终形成：

```text
Scenario
   ↓
Baseline Configuration
基线配置
   ↓
Sionna Simulation
   ↓
Baseline Objective
基线目标值

        VS

Optimizer
   ↓
Candidate Configuration
候选配置
   ↓
Sionna Simulation
   ↓
Candidate Objective
候选目标值
   ↓
Search / Iteration
搜索 / 迭代
   ↓
Best Configuration
最优配置
   ↓
Optimized Result
优化结果
   ↓
Before / After Comparison
优化前后对比
```

Day 4 成功的真正含义：

> 平台第一次能够真实执行一个参数优化算法，并通过 Sionna RT 对每个候选参数进行评价，最终形成可追溯的优化前后对比。

---

# 1. Day 4 的科学边界

Day 4 不是：

```text
最终科研算法验证
```

也不是：

```text
华为实测数据验证
```

更不是：

```text
最终验收 KPI 验证
```

Day 4 是：

> **Optimization Infrastructure Validation**
> **优化基础设施验证**

目的：

验证平台已经具备：

```text
Algorithm
→ Parameter
→ Simulation
→ Objective
→ Search
→ Best Result
→ Comparison
→ Evidence
```

完整闭环。

---

# 2. 算法身份必须明确

Day 4 第一个优化器命名：

```text
Grid Search
网格搜索
```

算法分类：

```text
Engineering Baseline Optimizer
工程基线优化器
```

必须明确：

```text
Learning Algorithm: NO
学习算法：否
```

禁止 UI、README、metadata 把它称为：

```text
AI Optimizer
Learning Optimizer
Intelligent Optimization
学习优化算法
智能优化算法
```

它只是工程基线。

---

# 3. Day 4 优化变量

优先选择：

```text
TX Power
发射功率
```

作为第一条 Optimization Variable。

原因：

```text
1. Sionna RT 已经能够直接控制；

2. 参数语义简单；

3. 不需要修改场景几何；

4. 不需要 Blender；

5. 不需要重新设计天线模型；

6. 容易构造可重复搜索空间；

7. 可以真实影响 RSS / SINR / Radio Map。
```

如果当前 Sionna API 的 TX power 控制方式与现有 Backend 实现冲突：

允许 Cursor 根据 Sionna RT 2.1 实际 API 做最小调整。

但优先保持：

```text
TX Power
```

不要擅自换成复杂变量。

---

# 4. 第一版搜索空间

建议：

```text
TX Power Candidates

38 dBm
40 dBm
42 dBm
44 dBm
46 dBm
```

但：

**这些值属于工程演示搜索空间，不是 5G 标准规定值，也不是华为现网配置。**

必须在 metadata 中标记：

```text
source = assumption
```

或：

```text
[A] Assumption
```

如果当前配置的 baseline 不是 44 dBm：

以当前 Scenario Config 为准。

不要为了本文档强制修改 baseline。

---

# 5. Baseline 定义

Baseline：

> 当前 Scenario 原始配置。

例如：

```text
Scenario TX Power
=
44 dBm
```

则：

```text
Baseline TX Power
=
44 dBm
```

Baseline 不是 Grid Search 的第一个候选。

Baseline 必须独立执行并保存。

---

# 6. Objective / 目标函数

这是 Day 4 最重要的科学设计之一。

不要直接：

```text
maximize RSS
```

因为：

> 单纯提高 TX Power 几乎必然提高 RSS。

那会导致优化器毫无意义地永远选择最大功率。

所以 Day 4 第一版必须使用一个带成本项的工程目标函数。

建议：

```text
Propagation Utility
传播效用目标
```

概念：

```text
Objective
=
Coverage Quality
-
Power Cost
```

---

# 7. Objective V0.1

定义：

```text
J =
coverage_ratio
-
λ × normalized_power_cost
```

其中：

```text
coverage_ratio
```

必须来自真实 Sionna Radio Map。

```text
normalized_power_cost
```

来自真实 TX power。

例如：

```text
normalized_power_cost
=
(P - P_min)
/
(P_max - P_min)
```

λ：

```text
lambda_power
```

属于实验配置。

建议默认：

```text
0.10
```

但必须标记：

```text
[A] Assumption
Engineering Demonstration Parameter
```

不是标准值。

---

# 8. Coverage Ratio 的定义必须被冻结

当前平台已经存在：

```text
Radio Map Coverage
无线电地图覆盖比例
```

Day 4 必须找到后端真实计算公式。

然后在：

```text
docs/objectives/
```

增加：

```text
propagation-utility-v0.1.md
```

明确：

```text
Metric Name

Formula

Threshold

Units

Input

Assumptions

Version
```

禁止前端自己重新计算一个不同版本。

---

# 9. Objective 版本化

Objective ID：

```text
PROPAGATION_UTILITY_V0_1
```

metadata：

```json
{
  "objective": {
    "id": "PROPAGATION_UTILITY_V0_1",
    "version": "0.1",
    "direction": "maximize"
  }
}
```

未来不能悄悄改变公式但继续使用相同 ID。

---

# 10. Objective 必须由后端计算

禁止：

```text
Frontend
→ Calculate Objective
```

必须：

```text
Simulation Result
      ↓
Objective Evaluator
      ↓
Objective Value
```

前端只展示。

---

# 11. Objective Evaluator

新增：

```text
src/optimization/objectives/
```

建议：

```text
src/optimization/
├── __init__.py
├── models.py
├── base.py
├── registry.py
├── service.py
├── optimizers/
│   ├── __init__.py
│   └── grid_search.py
└── objectives/
    ├── __init__.py
    └── propagation_utility.py
```

---

# 12. Optimizer Interface

必须建立统一接口。

例如：

```python
class Optimizer(ABC):

    @property
    @abstractmethod
    def id(self) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def optimize(
        self,
        problem: OptimizationProblem,
        evaluator: CandidateEvaluator,
    ) -> OptimizationResult:
        ...
```

具体签名允许根据现有项目风格调整。

核心要求：

> Optimizer 不允许直接 import Sionna。

---

# 13. 最重要的解耦

必须：

```text
GridSearchOptimizer
        ↓
CandidateEvaluator Interface
        ↓
Optimization Service
        ↓
SimulationBackend
        ↓
SionnaBackend
```

禁止：

```text
GridSearchOptimizer
        ↓
SionnaBackend
```

更禁止：

```text
GridSearchOptimizer
        ↓
sionna.rt
```

未来科研算法必须能够替换 Grid Search，而无需理解 Sionna。

---

# 14. Optimization Problem

定义：

```text
OptimizationProblem
```

至少包含：

```text
scenario_id

parameter_space

objective

direction

baseline_configuration

metadata
```

例如：

```json
{
  "scenario_id": "SIONNA-DEMO-001",
  "parameter_space": {
    "tx_power_dbm": [
      38,
      40,
      42,
      44,
      46
    ]
  },
  "objective": {
    "id": "PROPAGATION_UTILITY_V0_1",
    "direction": "maximize",
    "lambda_power": 0.1
  }
}
```

实际字段以 Pydantic model 为准。

---

# 15. Candidate / 候选解

定义：

```text
OptimizationCandidate
```

至少：

```text
candidate_id

parameters

iteration

status

objective_value

simulation_result

runtime
```

---

# 16. Candidate ID

例如：

```text
CAND-001
CAND-002
CAND-003
```

或者 UUID。

要求：

> 同一个 Optimization Run 内唯一。

---

# 17. Optimization Run

不要把优化直接塞进普通 Experiment。

建立：

```text
OptimizationRun
```

因为语义不同。

Experiment：

```text
一次仿真
```

OptimizationRun：

```text
一次优化过程
```

一个 OptimizationRun 包含：

```text
Baseline Experiment

Candidate Experiment 1

Candidate Experiment 2

...

Best Experiment
```

---

# 18. Optimization Run ID

格式：

```text
OPT-XXXXXXXX
```

例如：

```text
OPT-A81F7D21
```

---

# 19. Optimization Status

定义：

```text
CREATED

RUNNING

SUCCEEDED

FAILED
```

Day 4 不需要：

```text
PAUSED
CANCELLED
```

---

# 20. OptimizationResult

至少：

```text
optimization_id

status

scenario

optimizer

objective

baseline

candidates

best_candidate

comparison

runtime

provenance

error
```

---

# 21. Baseline Experiment 必须保留

Optimization Run 中：

```text
baseline
```

必须指向一个真实 Simulation Experiment。

不要只保存：

```text
baseline_objective = 0.52
```

应该能够追溯：

```text
Optimization
   ↓
Baseline Experiment ID
   ↓
SimulationResult
   ↓
Artifacts
```

---

# 22. Candidate 也必须可追溯

每个 candidate：

必须能够追溯：

```text
Candidate
   ↓
Parameters
   ↓
Experiment ID
   ↓
Simulation Result
   ↓
Objective
```

禁止只保存最后最佳结果。

---

# 23. 重复 Baseline 参数

搜索空间可能包含：

```text
44 dBm
```

而 Baseline 也是：

```text
44 dBm
```

不要重复运行。

允许：

```text
Candidate 44 dBm
→ reuse baseline result
```

metadata：

```text
reused_baseline = true
```

这样节省一次 Sionna 调用。

---

# 24. Grid Search

行为：

```text
Baseline
   ↓
Evaluate

Candidate 38
   ↓
Evaluate

Candidate 40
   ↓
Evaluate

Candidate 42
   ↓
Evaluate

Candidate 44
   ↓
Reuse Baseline

Candidate 46
   ↓
Evaluate

Select Best
```

---

# 25. Candidate 顺序必须确定

使用搜索空间定义顺序。

不要随机 shuffle。

这样：

```text
同配置
+
同 seed
=
可重复结果
```

---

# 26. Seed

Optimization Run 必须记录：

```text
seed
```

并传给每个 candidate。

对于公平比较：

> 所有 Candidate 必须使用相同场景随机条件。

否则：

```text
Candidate A
```

和：

```text
Candidate B
```

可能是在不同随机世界里比较。

这是硬性要求。

---

# 27. Common Random Numbers / 公共随机条件

Day 4 必须在 README 或 objective 文档中明确：

> Baseline 和所有候选配置使用相同 Scenario Seed，以降低随机采样差异对参数比较的影响。

不需要使用复杂统计术语实现额外算法。

只需要保持相同 seed。

---

# 28. 参数注入

不要直接修改原始：

```text
configs/sionna_demo.yaml
```

应该：

```text
Base Scenario
     +
Candidate Parameters
     ↓
Derived Scenario Config
```

每次 Candidate 使用独立 config。

原始 Scenario 不变。

---

# 29. Immutability / 不可变原则

禁止：

```text
optimizer 修改全局 Scenario object
```

优先：

```text
copy / model_copy
```

生成：

```text
Candidate Scenario
```

避免 Candidate A 污染 Candidate B。

---

# 30. Candidate Artifact

每个 Candidate 不需要复制全部巨大产物到 Optimization 目录。

推荐：

```text
OptimizationRun
│
├── optimization.json
│
└── references
    ├── baseline_experiment_id
    ├── candidate_experiment_ids
    └── best_experiment_id
```

实际 Radio Map 等仍归：

```text
Experiment Store
```

管理。

---

# 31. Optimization Store

Day 4 继续 filesystem。

新增：

```text
data/
└── optimizations/
    └── OPT-XXXXXXXX/
        └── optimization.json
```

定义：

```text
OptimizationStore
```

以及：

```text
FileOptimizationStore
```

不要上数据库。

---

# 32. Atomic Write

和 Experiment Store 一样：

```text
optimization.json.tmp
   ↓
atomic rename
   ↓
optimization.json
```

---

# 33. Optimization Service

新增：

```text
OptimizationService
```

职责：

```text
Create Optimization Run

Load Scenario

Resolve Optimizer

Resolve Objective

Run Baseline

Generate Candidate

Run Candidate Simulation

Evaluate Objective

Persist Candidate Result

Select Best

Build Comparison

Finalize Optimization
```

---

# 34. Optimization Service 不做数学算法

Service 负责 orchestration。

Grid Search 负责：

```text
parameter enumeration
```

Objective Evaluator 负责：

```text
objective calculation
```

Simulation Backend 负责：

```text
simulation
```

不要混在一个 500 行函数里。

---

# 35. Optimizer Registry

类似 BackendRegistry。

增加：

```text
OptimizerRegistry
```

注册：

```text
grid_search
```

API 可以查询：

```text
GET /api/v1/optimizers
```

---

# 36. GET /api/v1/optimizers

返回：

```json
{
  "items": [
    {
      "id": "grid_search",
      "name_zh": "网格搜索",
      "name_en": "Grid Search",
      "category": "engineering_baseline",
      "learning_algorithm": false,
      "available": true
    }
  ]
}
```

不要出现假的：

```text
AI
Learning
Deep Learning
```

---

# 37. GET /api/v1/objectives

建议实现：

```text
GET /api/v1/objectives
```

返回：

```text
PROPAGATION_UTILITY_V0_1
```

及其：

```text
name

version

direction

description

required_metrics

assumptions
```

---

# 38. POST /api/v1/optimizations

请求示意：

```json
{
  "name": "TX Power Grid Search",
  "scenario_id": "SIONNA-DEMO-001",
  "optimizer_id": "grid_search",
  "objective_id": "PROPAGATION_UTILITY_V0_1",
  "parameter_space": {
    "tx_power_dbm": [
      38,
      40,
      42,
      44,
      46
    ]
  }
}
```

真实 schema 由实现决定。

---

# 39. Day 4 允许同步运行

和 Experiment 一样：

Day 4 可以同步：

```text
POST Optimization
       ↓
Baseline
       ↓
Candidates
       ↓
Best
       ↓
Response
```

因为搜索空间只有少量 Candidate。

但是必须保留：

```text
status
```

为以后异步化准备。

---

# 40. 运行次数控制

Day 4 默认 Candidate：

```text
<= 5
```

Hard Limit 建议：

```text
<= 10
```

防止用户误输入：

```text
10000 candidates
```

导致同步 API 卡死。

超过限制：

返回：

```text
422
```

---

# 41. Objective Evaluation

每个 Candidate 完成 Sionna 后：

```text
SimulationResult
      ↓
PropagationUtilityEvaluator
      ↓
ObjectiveEvaluation
```

保存：

```text
coverage_ratio

normalized_power_cost

lambda_power

objective_value
```

---

# 42. Objective Breakdown

必须保存 breakdown。

例如：

```json
{
  "objective_value": 0.53,
  "components": {
    "coverage_ratio": 0.61,
    "normalized_power_cost": 0.8,
    "lambda_power": 0.1
  }
}
```

以上数字仅为 schema 示例。

运行时不得使用示例数字。

---

# 43. Best Candidate

如果多个 Candidate：

```text
objective_value
```

完全相同：

选择：

```text
lower TX power
```

作为 deterministic tie-breaker。

必须写测试。

---

# 44. Improvement

定义：

```text
absolute_improvement
=
optimized_objective
-
baseline_objective
```

相对改善：

```text
relative_improvement_percent
=
(optimized - baseline)
/
abs(baseline)
× 100%
```

但如果：

```text
baseline ≈ 0
```

relative improvement：

```text
null
```

不要除零。

---

# 45. 非正改善必须允许

Grid Search 有可能：

```text
best objective <= baseline objective
```

平台必须允许显示：

```text
No Improvement
未获得改善
```

禁止为了 Demo 强行保证：

```text
+XX%
```

---

# 46. Comparison Model

建立：

```text
OptimizationComparison
```

至少：

```text
baseline_experiment_id

optimized_experiment_id

baseline_parameters

optimized_parameters

baseline_objective

optimized_objective

absolute_improvement

relative_improvement_percent
```

---

# 47. Comparison 不等于 Acceptance KPI

UI 中标题：

```text
优化目标改善
Objective Improvement
```

禁止：

```text
验收指标提升
Acceptance KPI Improvement
```

---

# 48. Provenance

Optimization Run 必须记录：

```text
optimizer = grid_search

optimizer_category = engineering_baseline

learning_algorithm = false

simulation_backend = sionna_rt

source_type = simulation

measured = false

objective_id

objective_version

scenario_id

seed
```

---

# 49. Evidence Label

Day 4 Optimization：

```text
Evidence Level:
Synthetic / Simulation Validation
```

如果沿用现有体系：

```text
L1 / L2
```

必须根据项目已有定义使用。

不要擅自称：

```text
Measured Validation
```

---

# 50. Optimization API

至少：

```text
GET /api/v1/optimizers

GET /api/v1/objectives

POST /api/v1/optimizations

GET /api/v1/optimizations

GET /api/v1/optimizations/{optimization_id}
```

---

# 51. Optimization List

支持：

```text
limit
offset
```

最新优先。

---

# 52. Frontend 导航变化

原：

```text
算法中心
Algorithm Center

Coming Soon
```

Day 4 改为真正页面：

```text
优化中心
Optimization Center
```

或者保留：

```text
算法中心
Algorithm Center
```

内部提供：

```text
Optimizers

Optimization Runs
```

推荐导航：

```text
平台概览

场景中心

优化中心

实验中心

验收中心
```

---

# 53. Optimization Center

路由：

```text
/optimizations
```

顶部：

```text
优化中心
Optimization Center
```

说明：

```text
配置并运行网络参数优化实验，
比较基线配置与候选配置的仿真结果。
```

---

# 54. Optimizer Card

显示：

```text
网格搜索
Grid Search

类型：
工程基线优化器

Learning Algorithm:
No
```

加 Info：

```text
用于验证平台优化闭环，
不代表项目最终学习优化算法。
```

---

# 55. 创建优化实验

按钮：

```text
新建优化实验
New Optimization Run
```

Modal / Drawer：

```text
Scenario

Optimizer

Objective

Parameter

Candidate Values
```

Day 4：

Parameter 固定：

```text
TX Power
```

不要做通用复杂 Parameter Builder。

---

# 56. Candidate 输入

默认：

```text
38, 40, 42, 44, 46
```

但这些值必须从：

```text
frontend default
```

明确标记为：

```text
Demo Search Space
演示搜索空间
```

更推荐由后端 optimizer/objective descriptor 返回 recommended demo values。

如果实现成本不高：

使用后端返回。

---

# 57. 运行优化

点击：

```text
运行优化
Run Optimization
```

显示：

```text
正在执行参数搜索
Running parameter search...
```

不要伪造：

```text
Candidate 3/5
```

除非 API 真正提供实时进度。

同步 API 情况下使用 Spinner。

---

# 58. Optimization Detail

路由：

```text
/optimizations/:optimizationId
```

这是 Day 4 的视觉核心。

---

# 59. 页面顶部

显示：

```text
优化实验
Optimization Run

OPT-XXXXXXXX

Status

Scenario

Optimizer

Objective

Simulation Backend
```

---

# 60. Before / After

页面核心：

```text
优化前
Baseline

VS

优化后
Optimized
```

左右并排。

---

# 61. Radio Map Comparison

桌面：

```text
┌─────────────────────┐   ┌─────────────────────┐
│                     │   │                     │
│ BASELINE RADIO MAP  │   │ OPTIMIZED RADIO MAP │
│                     │   │                     │
└─────────────────────┘   └─────────────────────┘
```

必须分别来自：

```text
baseline_experiment_id
```

和：

```text
optimized_experiment_id
```

的真实 artifact API。

---

# 62. 参数对比

例如：

```text
TX Power

Baseline
44 dBm

Optimized
42 dBm
```

真实结果决定。

不要假定 Optimized 一定降低功率。

---

# 63. Objective Comparison

显示：

```text
Propagation Utility
传播效用

Baseline
X

Optimized
Y

Improvement
+Z
```

所有数字来自 API。

---

# 64. Improvement 颜色

如果：

```text
improvement > 0
```

使用 success。

如果：

```text
= 0
```

neutral。

如果：

```text
< 0
```

warning/error。

不要永远绿色。

---

# 65. Optimization History

用 ECharts。

X：

```text
Candidate
```

Y：

```text
Objective Value
```

画真实：

```text
Candidate → Objective
```

---

# 66. 禁止平滑伪造

ECharts：

不要使用会制造“学习曲线”错觉的：

```text
smooth = true
```

建议：

```text
scatter
```

或：

```text
line + symbol
```

但：

```text
smooth = false
```

---

# 67. 图表 Tooltip

显示：

```text
Candidate ID

TX Power

Objective

Coverage Ratio

Power Cost
```

---

# 68. Best Candidate 标记

图中真实最佳 Candidate：

```text
BEST
```

视觉突出。

---

# 69. Objective Breakdown

显示：

```text
Objective Breakdown
目标函数分解
```

包括：

```text
Radio Map Coverage

Power Cost

λ

Final Objective
```

并提供公式说明。

---

# 70. Scientific Note

页面必须显示：

```text
当前优化目标为传播层工程目标函数，
用于验证参数优化闭环。

该指标不是项目最终吞吐率、
边缘用户速率或优化速度验收指标。
```

---

# 71. Optimization Timeline

显示：

```text
Optimization Created

Baseline Evaluated

Candidate Evaluated

...

Best Candidate Selected

Optimization Completed
```

如果后端目前不保存这么细：

至少：

```text
Created
Running
Succeeded
```

不要前端伪造时间点。

---

# 72. Candidate Table

显示：

| Candidate | TX Power | Coverage | Power Cost | Objective | Experiment |
| --------- | -------: | -------: | ---------: | --------: | ---------- |

Experiment ID：

可点击进入原 Experiment Detail。

这样：

```text
Optimization
    ↓
Candidate
    ↓
Experiment
```

证据链在 UI 上可导航。

---

# 73. Baseline Row

Candidate Table 中：

Baseline 单独标记：

```text
BASELINE
基线
```

如果 44 dBm Candidate 复用了 Baseline：

显示：

```text
Reused Baseline
复用基线结果
```

---

# 74. Experiment Center 不需要大改

现有 Experiment Center 保留。

Optimization 产生的 Candidate Experiments：

可以正常出现在 Experiment Center。

未来可增加：

```text
Purpose
baseline / optimization_candidate
```

如果容易实现。

Day 4 非强制。

---

# 75. Overview 更新

Overview 增加：

```text
Optimization Runs
优化实验
```

但不要让首页过度拥挤。

可以把原四卡调整为：

```text
Backend

Scenarios

Experiments

Optimization Runs
```

Latest Experiment 移到下面。

---

# 76. FakeBackend Optimization

Unit Test 必须能够：

```text
FakeBackend
   ↓
Grid Search
   ↓
Optimization Result
```

不依赖 GPU。

FakeBackend 可以根据 TX power：

返回确定性的测试结果。

但必须：

```text
source_type = test_fixture
```

---

# 77. Fake Objective 数据

测试可以构造：

```text
candidate A → 0.4
candidate B → 0.6
candidate C → 0.5
```

用于验证 Grid Search。

这属于：

```text
Test Fixture
```

不是生产数据。

---

# 78. Unit Tests

至少：

```text
test_grid_search_selects_best

test_grid_search_deterministic

test_baseline_reuse

test_objective_formula

test_objective_breakdown

test_tie_breaker_lower_power

test_negative_improvement_allowed

test_relative_improvement_zero_baseline

test_candidate_limit

test_candidate_scenario_immutable

test_optimization_store_atomic_write

test_optimization_failure_persisted

test_optimizer_does_not_require_sionna
```

---

# 79. API Tests

至少：

```text
test_list_optimizers

test_list_objectives

test_create_optimization

test_get_optimization

test_list_optimizations

test_optimization_not_found

test_invalid_optimizer

test_invalid_objective

test_too_many_candidates

test_failed_optimization
```

使用 FakeBackend。

---

# 80. Real Sionna Integration Test

至少一个：

```text
integration + sionna
```

真实运行：

```text
Baseline
+
至少 2 个不同 TX Power Candidate
```

验证：

```text
真实 Experiment ID 不同

真实 Radio Map 存在

Objective 可计算

Best Candidate 来自实际结果
```

CI 没 Sionna 可以 skip。

---

# 81. 不要让完整测试变得太慢

Unit：

```text
FakeBackend
```

Integration：

```text
small candidate set
```

Browser Manual：

可以：

```text
5 candidates
```

---

# 82. Browser Smoke Test

真实浏览器：

```text
打开 Optimization Center

创建 Optimization Run

选择 Sionna Scenario

Grid Search

运行

等待完成

进入 Optimization Detail

查看 Before/After

查看 Objective

查看 Candidate History

点击 Candidate Experiment

打开 Experiment Detail
```

---

# 83. 真实 Sionna Optimization Evidence

完成后保存轻量 reference：

```text
reference/
└── optimization/
    └── OPT-XXXXXXXX/
        ├── optimization.json
        ├── comparison.png
        └── README.md
```

不要复制：

```text
radio_map.npz × 5
```

进入 Git。

---

# 84. Reference README

必须声明：

```text
Optimizer:
Grid Search

Category:
Engineering Baseline

Learning Algorithm:
No

Simulation:
Sionna RT

Measured Data:
No

Purpose:
Optimization Loop Validation

Acceptance Evidence:
No
```

---

# 85. Day 4 禁止事项

禁止：

```text
伪造 Throughput

伪造 Edge User Rate

伪造 RSRP

伪造 Optimization Speed +100%

伪造 Learning Algorithm

伪造 Huawei Data

伪造 convergence curve

伪造 Candidate results

前端计算 objective

Grid Search 直接 import Sionna

修改原始 Scenario

为了 Demo 强制 improvement > 0
```

---

# 86. 一个重要的物理问题

TX Power 优化的目的不是证明：

```text
降低 TX Power 一定更好
```

也不是：

```text
提高 TX Power 一定更好
```

而是证明：

> 在显式目标函数下，平台可以搜索配置空间并根据真实仿真结果选择目标值最优的配置。

因此结果可能：

```text
38 dBm
```

也可能：

```text
46 dBm
```

也可能：

```text
Baseline 44 dBm
```

最好。

全部接受。

---

# 87. Objective Assumption 必须展示

`lambda_power`：

属于：

```text
Engineering Assumption
工程假设
```

前端 Detail：

显示：

```text
Power Cost Weight λ
功率成本权重

0.10

[A] Assumption
```

不要隐藏。

---

# 88. Objective Version 必须展示

Detail：

```text
Objective

Propagation Utility

Version
0.1
```

以后算法比较才能保证：

> 比较的是同一个 Objective。

---

# 89. Runtime

Optimization Runtime：

至少：

```text
total_seconds
```

如果方便：

```text
baseline_seconds

candidate_evaluation_seconds

total_seconds
```

但不要过度设计。

---

# 90. Optimization Speed 暂时不计算

即使有 runtime：

不要显示：

```text
Optimization Speed Improvement
```

因为还没有：

```text
baseline optimization algorithm
VS
candidate optimization algorithm
```

的正式 benchmark protocol。

---

# 91. API Error

增加：

```text
OPTIMIZER_NOT_FOUND

OBJECTIVE_NOT_FOUND

OPTIMIZATION_NOT_FOUND

INVALID_PARAMETER_SPACE

OPTIMIZATION_FAILED
```

保持现有双语 Error Model 风格。

---

# 92. Failed Optimization

如果 Candidate 失败：

Day 4 推荐：

```text
整个 Optimization Run = FAILED
```

保存：

```text
completed candidates

failed candidate

error
```

不要悄悄跳过失败 Candidate。

未来再设计：

```text
partial success
```

---

# 93. Crash Recovery

仍然：

```text
Known Limitation
```

Day 4 不解决。

---

# 94. Concurrency

仍然：

```text
Known Limitation
```

Day 4 不解决。

不要引入任务队列。

---

# 95. Day 4 Definition of Done

全部满足才通过：

```text
[ ] optimization package 建立

[ ] Optimizer interface 建立

[ ] GridSearchOptimizer 实现

[ ] GridSearch 不依赖 Sionna

[ ] Objective interface 建立

[ ] PROPAGATION_UTILITY_V0_1 实现

[ ] Objective 文档冻结

[ ] lambda 标记为 Assumption

[ ] OptimizationProblem 实现

[ ] Candidate Model 实现

[ ] OptimizationResult 实现

[ ] OptimizationComparison 实现

[ ] OptimizationStore 实现

[ ] Atomic Write 实现

[ ] OptimizationService 实现

[ ] OptimizerRegistry 实现

[ ] GET /optimizers

[ ] GET /objectives

[ ] POST /optimizations

[ ] GET /optimizations

[ ] GET /optimizations/{id}

[ ] Baseline 独立保存

[ ] Candidate Experiment 可追溯

[ ] Baseline reuse 工作

[ ] Same Seed 保证

[ ] Scenario 不被 mutation

[ ] Candidate Limit 工作

[ ] Tie-breaker deterministic

[ ] Negative/Zero improvement 正确处理

[ ] Optimization provenance 完整

[ ] Optimization Center 完成

[ ] Create Optimization UI 完成

[ ] Optimization Detail 完成

[ ] Before/After Radio Map 完成

[ ] Candidate Table 完成

[ ] Objective History Chart 完成

[ ] Objective Breakdown 完成

[ ] Scientific Note 完成

[ ] Candidate → Experiment 可点击追溯

[ ] Test Fixture 正确标记

[ ] 不存在假 KPI

[ ] Unit Tests PASS

[ ] API Tests PASS

[ ] Sionna Integration PASS

[ ] Frontend Typecheck PASS

[ ] Frontend Tests PASS

[ ] Frontend Build PASS

[ ] Browser Smoke Test PASS

[ ] 真实 Sionna Optimization Run 成功

[ ] Reference Evidence 保存

[ ] README 更新

[ ] Git Commit 完成
```

---

# 96. Cursor 完成后人工验收报告

必须输出：

```text
1. Git Commit Hash

2. 新增/修改文件

3. Optimizer Interface

4. Grid Search 实现说明

5. Objective 完整数学公式

6. Coverage Ratio 完整定义

7. lambda_power 的来源与标记

8. Parameter Search Space

9. Optimization API 列表

10. Unit Test 结果

11. Integration Test 结果

12. Frontend Test / Build 结果

13. Browser Smoke Test 结果

14. 真实 Optimization Run ID

15. Baseline Experiment ID

16. Candidate Experiment IDs

17. Baseline 参数

18. Best 参数

19. Baseline Objective

20. Best Objective

21. Absolute Improvement

22. Relative Improvement

23. Before Radio Map 路径

24. After Radio Map 路径

25. Optimization Detail 截图

26. Candidate History 截图

27. Provenance

28. Console Error 数量

29. 已知问题

30. Day 5 是否 Ready
```

---

# 97. Cursor Auto 执行顺序

严格建议：

```text
A. git pull

B. 确认 baseline >= 1a46e65

C. 跑现有 backend/frontend tests

D. 阅读当前 Coverage Ratio 实现

E. 冻结 Objective V0.1 文档

F. 建立 optimization models

G. 建立 objective evaluator

H. 写 objective unit tests

I. 建立 Optimizer interface

J. 实现 Grid Search

K. 写 Grid Search tests

L. 建立 OptimizationStore

M. 建立 OptimizationService

N. Backend Registry / API

O. FakeBackend Optimization tests

P. Real Sionna Integration test

Q. Optimization Center

R. Create Optimization UI

S. Optimization Detail

T. Before/After Radio Map

U. Candidate Table

V. Objective History Chart

W. Provenance / Scientific Note

X. Backend full tests

Y. Frontend typecheck/test/build

Z. 启动真实 Backend + Frontend

AA. Browser Smoke Test

AB. 从浏览器运行真实 Sionna Optimization

AC. 检查每个 Candidate Experiment

AD. 检查 Objective calculation

AE. 检查 Before/After artifacts

AF. 截图

AG. 保存 reference evidence

AH. README

AI. git diff review

AJ. Commit
```

---

# 98. 如果真实结果“优化不明显”

不要调数据。

不要换 seed。

不要偷偷修改 Radio Map。

不要反复调 λ 直到得到漂亮数字。

如实保存结果。

如果：

```text
Improvement = 0
```

就是：

```text
No Improvement
```

如果：

```text
Improvement < 0
```

就是负值。

科学可信性优先于 Demo 数字。

---

# 99. 如果 Objective 设计出现退化

如果真实运行发现：

```text
所有 Candidate objective 单调随 TX power 增加
```

不要擅自重新定义公式。

记录：

```text
Objective Design Limitation
```

然后完成当前版本。

下一版本再：

```text
PROPAGATION_UTILITY_V0_2
```

修改。

绝不能悄悄改变：

```text
V0_1
```

公式。

---

# 100. Day 4 完成后的架构

最终应该成为：

```text
                   Web Platform
                       │
              Optimization Center
                       │
                Optimization API
                       │
              OptimizationService
                       │
          ┌────────────┴────────────┐
          │                         │
     Optimizer                 Objective
          │                         │
   Grid Search                 Evaluator
          │                         │
          └────────────┬────────────┘
                       │
              CandidateEvaluator
                       │
                ExperimentService
                       │
               SimulationBackend
                       │
                 SionnaBackend
                       │
                   Sionna RT
```

关键依赖：

```text
Optimizer
```

永远不知道：

```text
Sionna RT
```

的存在。

---

# 101. Day 5 Preview — 不要现在实现

Day 4 解决：

```text
参数优化闭环
```

Day 5 将开始解决：

```text
System-Level KPI
系统级 KPI
```

即逐渐建立：

```text
UE
↓
Traffic Demand
↓
Radio Condition
↓
Resource Model
↓
Spectral Efficiency
↓
Throughput
↓
Edge User Rate
```

届时再评估：

```text
Sionna SYS
```

是否直接进入主链。

只有系统级模型建立以后：

```text
Throughput

Edge User Rate
```

才允许从：

```text
—
Not Available
```

变成真实数字。

---

# 102. 最终执行指令

现在直接执行 Day 4。

不要继续美化 Day 3。

不要开发登录系统。

不要上数据库。

不要上 Redis/Celery。

不要开发最终学习算法。

不要生成假 KPI。

不要人为制造优化提升。

只完成一件事：

> **让 Grid Search 通过统一 Optimizer 接口调用真实 Sionna 仿真，对真实候选配置进行评价，得到真实最佳配置，并在 Web 中形成可追溯的 Before / After 优化证据链。**

完成后：

```text
测试
↓
真实 Sionna Optimization
↓
浏览器验证
↓
Reference Evidence
↓
Git Commit
↓
人工验收报告
```

然后停止。

# END OF DAY 4
