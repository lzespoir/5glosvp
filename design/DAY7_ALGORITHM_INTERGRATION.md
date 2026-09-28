# Day 7 — Algorithm Integration Framework & First Research Algorithm Slot
# 算法接入框架与首个科研算法插槽

> 项目：5G 网络学习优化仿真验证平台
>
> Day 6 Frozen Baseline:
>
> Code: 6417ffd
> Fix: c565c91
> Evidence: 94829c3
>
> Reference Optimization:
> OPT-9A16123C
>
> Benchmark Protocol:
> SYSTEM_BENCHMARK_V0_1
>
> Day 7 核心目标：
>
> 将当前“平台内置 Grid Search”
> 演进为
> “统一算法接入、统一参数空间、统一实验协议、统一证据输出”
> 的算法验证平台。
>
> Grid Search 继续保留为 Engineering Baseline。
>
> Day 7 不要求真正实现项目最终科研学习算法，
> 但必须建立一个真实可运行的 Research Algorithm Slot，
> 证明未来研究团队算法能够在不修改平台核心代码的情况下接入。
>
> 本任务书供 Cursor Auto 直接执行。
>
> 必须实际修改代码、测试、真实运行、浏览器验证、
> 保存 Reference Evidence、提交 Git。
>
> 不要只输出设计方案。

---

# 0. Day 7 为什么现在做

Day 4 已完成：

Optimizer
→ Propagation Simulation
→ Objective

Day 5 已完成：

System Simulation
→ Throughput
→ KPI

Day 6 已完成：

Optimizer
→ Fair Evaluation Context
→ System Simulation
→ System KPI
→ Objective
→ Best Candidate
→ Evidence

但目前主要优化器仍然是：

Grid Search

Grid Search 是：

Engineering Baseline

不是：

Learning Optimization Algorithm

Day 7 必须解决：

“科研团队以后交给平台一个算法，
平台怎样接？”

而不是继续增加新的 Grid Search 功能。

---

# 1. Day 7 最重要的架构原则

Platform owns:

Scenario

Parameter Space

Evaluation Protocol

Simulation

KPI

Objective

Experiment

Evidence

Algorithm owns:

Candidate Generation / Search Logic

即：

Platform
    ↓
Optimization Problem
    ↓
Algorithm Adapter
    ↓
Algorithm
    ↓
Candidate Configuration
    ↓
Platform Evaluation
    ↓
Objective / KPI Feedback
    ↓
Algorithm
    ↓
Next Candidate
    ↓
...
    ↓
Final Result

算法不能拥有：

Sionna

Experiment Store

Frontend

KPI implementation

Acceptance logic

---

# 2. Algorithm 不得直接调用 Sionna

禁止：

ResearchAlgorithm
    ↓
SionnaSystemBackend

正确：

ResearchAlgorithm
    ↓
Evaluation Interface
    ↓
Platform
    ↓
Simulation Backend

算法只知道：

Parameter

Objective Feedback

Constraint Feedback

必要的 Metadata

---

# 3. Algorithm 不得直接计算平台 KPI

禁止：

ResearchAlgorithm
→ 自己重新计算 Network Throughput

平台统一：

Simulation
→ KPI Engine
→ Objective Engine

然后把结果返回算法。

---

# 4. Algorithm Adapter

建立正式：

AlgorithmAdapter

或与当前 Optimizer Interface 自然兼容的抽象。

建议能力：

metadata()

validate_problem()

initialize()

suggest()

observe()

finalize()

不要为了形式强制完全采用该命名。

重点是：

算法与平台之间存在清晰生命周期。

---

# 5. 推荐生命周期

概念：

algorithm.initialize(problem)

while not algorithm.should_stop():

    suggestions = algorithm.suggest()

    evaluations = platform.evaluate(suggestions)

    algorithm.observe(evaluations)

result = algorithm.finalize()

这样未来：

Grid Search

Random Search

Bayesian Optimization

Zero-order Optimization

Learning Algorithm

External Algorithm

都可以进入同一条链。

---

# 6. 不要假设算法一次给出全部 Candidate

Day 4 / Day 6 Grid Search：

可以一次产生：

[0.1, 0.3, 0.6, ...]

但未来算法可能：

Candidate 1
↓
Evaluation
↓
Candidate 2
↓
Evaluation
↓
Candidate 3

因此平台必须支持：

Iterative Ask / Tell

或语义等价机制。

---

# 7. Algorithm Capability

新增：

AlgorithmCapabilities

至少能够描述：

supports_discrete

supports_continuous

supports_integer

supports_categorical

supports_vector

supports_constraints

supports_multi_objective

supports_batch_suggestions

supports_iterative_feedback

supports_auto_configuration

---

# 8. Day 7 不要求所有 capability 都实现

Capability 是声明。

例如 Grid Search：

supports_discrete = true

supports_continuous = false

Research Demo Algorithm：

根据实际实现填写。

禁止：

为了看起来高级全部 true。

---

# 9. Algorithm Metadata

每个算法至少：

algorithm_id

name

version

category

description

provider

learning_algorithm

capabilities

supported_parameter_types

hyperparameter_schema

source

status

---

# 10. Algorithm Category

至少区分：

engineering_baseline

research

external

未来可以增加：

production

但 Day 7 不需要。

---

# 11. Grid Search Metadata

当前 Grid Search 正式登记：

id:
grid_search

category:
engineering_baseline

learning_algorithm:
false

不要删除。

它以后是所有科研算法的重要对照组。

---

# 12. Research Algorithm Slot

Day 7 建立：

research_demo_optimizer

注意：

它不是项目最终科研成果。

必须明确：

Purpose:
Algorithm Integration Validation

Acceptance:
NO

Research Deliverable:
NO

Measured:
NO

---

# 13. Research Demo Algorithm 选择

推荐实现：

Adaptive Local Search

或者：

Simple Coordinate / Local Search

要求：

1. 与 Grid Search 搜索逻辑明显不同；
2. 使用 iterative feedback；
3. 能根据上一次 objective 决定下一次参数；
4. 能证明 ask → evaluate → tell；
5. 实现简单、可审计；
6. 不冒充学习优化科研成果。

不要实现复杂 AI。

---

# 14. 推荐 Demo：Adaptive Local Search

针对一个 continuous parameter：

scheduler_beta

bounds:

(0, 1)

算法概念：

start from baseline

evaluate neighbors

move toward better direction

reduce step size

repeat

直到：

max_iterations

或：

step_size < tolerance

---

# 15. 重要：这不是 Learning Algorithm

即使它：

adaptive

iterative

也必须：

learning_algorithm = false

category = research_demo

或：

algorithm_integration_demo

不要把：

“会根据结果调整”

等同于：

“学习优化算法”。

---

# 16. 为什么仍然叫 Research Algorithm Slot

Slot 是：

未来科研算法使用的接入位置。

不是说：

Demo Algorithm 本身就是科研成果。

UI 必须区别。

---

# 17. ParameterDefinition 正式化

Day 6 已开始：

ParameterDefinition

Day 7 正式完善。

至少支持：

continuous

integer

discrete

categorical

vector

---

# 18. Continuous Parameter

例如：

scheduler_beta

type:
continuous

bounds:
lower > 0
upper < 1

unit:
dimensionless

default:
0.9

---

# 19. Discrete Parameter

例如：

candidate scheduler beta list

type:
discrete

choices:
[...]

---

# 20. Integer Parameter

未来：

PRB allocation

type:
integer

bounds:
[min, max]

Day 7 只需要 schema + validation test。

---

# 21. Categorical Parameter

未来：

serving_cell

type:
categorical

choices:
CELL-A
CELL-B
...

Day 7 只做 schema。

---

# 22. Vector Parameter

未来非常重要。

例如：

TX Power per Cell

[
  P1,
  P2,
  P3,
  ...
]

或者：

PRB allocation vector

建立：

shape

element_type

bounds

constraints

Day 7 不要求真正优化 vector。

---

# 23. Parameter Space

新增：

ParameterSpace

包含：

parameters[]

constraints[]

metadata

未来一个优化问题可能：

1 parameter

也可能：

1000 parameters

平台数据结构不能假设：

single parameter only

---

# 24. Day 7 不把 SystemOptimizationService 重写掉

现有 Day 6 已经工作。

优先：

evolve

不要：

rewrite

必须保证：

OPT-9A16123C

继续可打开。

---

# 25. Algorithm Hyperparameters

建立正式：

AlgorithmHyperparameterSchema

与：

Optimization Variable

完全分离。

例如 Research Demo：

initial_step

min_step

max_iterations

tolerance

---

# 26. Hyperparameter 类型

至少允许：

float

integer

boolean

categorical

---

# 27. Auto Configuration

Algorithm Metadata 允许：

auto_configuration:
true / false

如果 true：

算法可以使用默认推荐配置。

如果 false：

用户必须填写必要参数。

Day 7 Demo 可以：

auto_configuration = true

但 UI 仍允许：

Advanced Settings

修改。

---

# 28. Default 不等于隐藏

UI：

Recommended / Default

Advanced Settings

用户可以展开。

不要把所有算法参数永久写死在 backend。

---

# 29. Algorithm Validation

运行前必须验证：

Algorithm supports Parameter Type

例如：

Grid Search
+
continuous parameter without discretization

应该：

reject

而不是偷偷 discretize。

---

# 30. Problem Compatibility

建立：

AlgorithmProblemCompatibility

检查：

parameter types

constraints

objective count

backend requirements

evaluation protocol

---

# 31. Unsupported 必须明确

例如：

Algorithm:
Grid Search

Parameter:
1000-dimensional continuous vector

如果不支持：

HTTP 4xx

明确：

ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED

不要运行到一半才炸。

---

# 32. Evaluation Interface

Research Algorithm 获得的 evaluation result 至少：

candidate_id

parameters

objective

objective_direction

secondary_metrics

constraint_results

status

runtime

---

# 33. Algorithm 不需要知道 Experiment 内部结构

不要把：

Sionna artifact path

NPZ path

ExperimentStore object

传给算法。

算法只接收规范化：

EvaluationResult

---

# 34. Algorithm Run State

保存：

AlgorithmRunState

至少：

iteration

suggestions

observations

best_so_far

stop_reason

algorithm_state_metadata

---

# 35. 不保存不可审计黑盒 Pickle

Day 7 Reference Evidence：

优先 JSON。

如果未来算法内部模型必须 binary：

另外处理。

Day 7 不需要。

---

# 36. Iteration History

每次：

suggest
evaluate
observe

必须留下：

iteration

candidate

parameter

objective

secondary KPI

timestamp / sequence

---

# 37. Algorithm Trace

增加：

algorithm_trace.json

用于回答：

“算法为什么最后给出这个参数？”

Grid Search：

可以简单记录 candidate order。

Adaptive Demo：

记录：

initial point

step

direction

observation

next suggestion

stop reason

---

# 38. 不要求算法可解释内部数学

未来科研算法可能很复杂。

平台要求的是：

Input / Output / Evaluation Trace

而不是：

强制解释神经网络内部。

---

# 39. Stop Reason

标准化：

completed

max_iterations

converged

no_improvement

budget_exhausted

failed

cancelled

---

# 40. Evaluation Budget

正式引入：

max_evaluations

因为真实 Sionna evaluation 成本高。

算法不能无限调用 simulator。

---

# 41. Budget Enforcement

Budget 由：

Platform

执行。

不是：

Algorithm 自觉遵守。

如果：

max_evaluations = 10

算法第 11 次 suggest：

拒绝继续评价。

---

# 42. Candidate Deduplication

如果算法重复建议：

same parameter

平台应：

reuse existing evaluation

如果：

same Evaluation Context

same parameter

same backend/config

完全一致。

---

# 43. Evaluation Cache Key

建立稳定：

evaluation_cache_key

至少由：

evaluation_context

parameter configuration

backend version

simulation configuration

组成。

---

# 44. Cache 不跨错误上下文复用

禁止：

不同 channel

不同 UE

不同 protocol

复用。

---

# 45. Algorithm Registry

建立正式：

AlgorithmRegistry

业务层通过 registry 获取算法。

不要：

if algorithm_id == "grid_search"

if algorithm_id == "research_demo"

---

# 46. Future External Algorithms

Registry 未来允许：

PythonAdapter

MatlabAdapter

ExecutableAdapter

RESTAdapter

DockerAdapter

但：

Day 7 不实现。

---

# 47. 不做 Dynamic Plugin Loader

Day 7 禁止：

pip install arbitrary algorithm

upload Python code

dynamic import arbitrary path

plugin marketplace

remote execution

这些有：

安全

版本

环境

依赖

审计

问题。

以后单独设计。

---

# 48. Algorithm Package Contract 文档

新增：

docs/algorithms/algorithm-integration-contract-v0.1.md

内容：

Lifecycle

Metadata

Parameter Space

Evaluation Interface

Budget

Errors

Evidence

Versioning

---

# 49. Research Team 接入说明

新增：

docs/algorithms/how-to-integrate-an-algorithm.md

目标读者：

项目科研团队。

必须做到：

一个不了解平台内部实现的人，

能够知道：

我要实现什么接口？

输入是什么？

输出是什么？

怎么声明参数？

怎么声明超参数？

怎么本地测试？

怎么注册？

怎么运行？

怎么生成证据？

---

# 50. Example Algorithm

新增：

examples/algorithms/research_demo_optimizer/

或项目现有合适目录。

这是以后科研团队的：

template

---

# 51. Example 必须小

不要 1000 行。

目标：

清晰展示：

metadata

initialize

suggest

observe

finalize

---

# 52. Algorithm SDK

如果当前项目已经有：

algorithms/sdk

优先扩展。

不要建立第二套平行 SDK。

---

# 53. Algorithm SDK 版本

开始记录：

ALGORITHM_SDK_VERSION

例如：

0.1

Algorithm Metadata 保存：

sdk_version

未来接口变化：

可以判断兼容性。

---

# 54. API — Algorithm Catalog

GET /api/v1/algorithms

返回：

id

name

version

category

learning_algorithm

capabilities

supported_parameter_types

status

---

# 55. API — Algorithm Detail

GET /api/v1/algorithms/{id}

返回：

metadata

hyperparameter schema

compatibility

description

---

# 56. API — Compatibility

可以：

POST /api/v1/algorithms/{id}/validate

输入：

optimization problem

返回：

compatible

errors

warnings

---

# 57. Optimization API

现有 Optimization Create：

增加：

algorithm_id

algorithm_hyperparameters

parameter_space

evaluation_budget

---

# 58. Backward Compatibility

旧 Day 4 / Day 6 请求：

必须继续支持。

如果旧字段：

optimizer_id

存在：

兼容转换。

不要破坏历史 evidence。

---

# 59. Frontend — Algorithm Center

现在把之前：

Coming Soon

的：

Algorithm Center

正式启用。

这是 Day 7 的主要 UI 成果之一。

---

# 60. Algorithm Center 首页

显示算法卡片/表格：

Grid Search

Research Demo Optimizer

至少显示：

Name

Version

Category

Learning Algorithm

Parameter Types

Status

---

# 61. Grid Search 标签

明确：

Engineering Baseline
工程基线

Not Learning Algorithm

---

# 62. Research Demo 标签

明确：

Integration Demo
接入验证算法

Not Project Research Deliverable

---

# 63. 不使用误导性标签

禁止：

AI Optimizer

Intelligent Algorithm

Learning Optimizer

Advanced AI

用于 Research Demo。

---

# 64. Algorithm Detail

显示：

Description

Version

Provider

Category

Capabilities

Supported Parameter Types

Hyperparameters

SDK Version

Evidence Status

---

# 65. Integration Guide

Algorithm Center：

增加：

“算法接入说明”

链接到：

How to Integrate

可以前端展示文档摘要。

---

# 66. Optimization Create

算法选择从：

硬编码 Grid Search

变成：

Algorithm Registry

返回列表。

---

# 67. Parameter Editor

Day 7 做：

Schema-driven minimal editor

只支持当前实际需要：

continuous

discrete

不要为了未来一次做完整 universal form builder。

---

# 68. Continuous UI

显示：

Parameter

Lower Bound

Upper Bound

Default

Unit

---

# 69. Discrete UI

显示：

Candidate Values

---

# 70. Algorithm Settings

独立区域：

Algorithm Settings
算法设置

例如：

Initial Step

Minimum Step

Max Iterations

Evaluation Budget

---

# 71. Auto Configure

如果：

auto_configuration = true

默认：

Recommended Settings

用户可以：

Use Recommended

或者展开：

Advanced Settings

---

# 72. Compatibility Feedback

选择：

Algorithm + Parameter

后立即检查。

例如：

✓ Compatible

或者：

Grid Search requires discrete candidate values.

不要等 Run 后才报错。

---

# 73. Optimization Detail

增加：

Algorithm

Algorithm Version

Category

Learning Algorithm

Hyperparameters

Evaluation Budget

Evaluations Used

Stop Reason

---

# 74. Algorithm Trace UI

增加：

Algorithm Trace
算法轨迹

显示：

Iteration

Suggested Parameter

Objective

Observation

Best So Far

---

# 75. 不伪造 Convergence Curve

只有算法真正：

iteration → feedback → next iteration

才可以显示：

Convergence

Grid Search：

仍然叫：

Candidate History

---

# 76. Research Demo 可以显示 Search Trace

例如：

β

0.9
↓
0.7
↓
0.5
↓
0.3
↓
...

但必须来自真实 trace。

---

# 77. Day 7 Reference Run

运行：

Research Demo Optimizer

Scenario：

SYSTEM-DEMO-001

Backend：

sionna_system

Benchmark：

SYSTEM_BENCHMARK_V0_1

Objective：

NETWORK_THROUGHPUT_MAX_V0_1

Parameter：

scheduler_beta

---

# 78. 不要求 Research Demo 打败 Grid Search

非常重要。

Day 7 成功标准：

Research Algorithm Slot works.

不是：

Demo Algorithm > Grid Search

如果它更差：

照样通过。

---

# 79. Fair Evaluation 继续沿用 Day 6

Research Demo 必须：

Same UE

Same Channel

Same Traffic

Same Horizon

不得重新建立一套评价方式。

---

# 80. Day 6 Frozen Protocol 不修改

SYSTEM_BENCHMARK_V0_1

保持。

如果发现必须修改：

建立 V0.2。

不要覆盖 V0.1。

---

# 81. Independent Verification

扩展：

verify_system_optimization.py

或新增：

verify_algorithm_run.py

独立检查：

Algorithm ID

Algorithm Version

SDK Version

Parameter Space

Hyperparameters

Budget

Trace

Candidate → Experiment

Objective

Best

Stop Reason

Fair Context

---

# 82. Verifier 不导入生产算法

否则无法独立证明：

trace / result

正确。

---

# 83. Algorithm Unit Tests

至少：

test_algorithm_metadata

test_algorithm_registry

test_unknown_algorithm

test_algorithm_capabilities

test_algorithm_sdk_version

test_algorithm_lifecycle

---

# 84. Parameter Tests

至少：

test_continuous_parameter

test_discrete_parameter

test_integer_schema

test_categorical_schema

test_vector_schema

test_bounds_validation

test_choices_validation

test_parameter_serialization

---

# 85. Compatibility Tests

至少：

test_grid_search_discrete_supported

test_grid_search_continuous_rejected_without_choices

test_demo_continuous_supported

test_unsupported_parameter_type

test_invalid_hyperparameter

---

# 86. Demo Algorithm Tests

至少：

test_initialize

test_first_suggestion

test_observe

test_next_suggestion_depends_on_observation

test_budget

test_convergence

test_stop_reason

test_determinism

---

# 87. Cache Tests

至少：

test_duplicate_candidate_reuses_evaluation

test_cache_same_context

test_cache_different_context_miss

test_cache_different_parameter_miss

---

# 88. API Tests

至少：

test_list_algorithms

test_algorithm_detail

test_validate_algorithm

test_create_optimization_with_algorithm

test_invalid_algorithm

test_invalid_hyperparameters

test_budget_enforced

---

# 89. Regression

必须：

Day 4

Day 5

Day 6

全部 PASS。

特别：

OPT-E56D9514

EXP-FC79FFC2

OPT-9A16123C

保持可读取。

---

# 90. Browser Smoke

真实浏览器：

Home
↓
Algorithm Center
↓
Grid Search Detail
↓
Research Demo Detail
↓
Integration Guide
↓
Optimization Center
↓
New System Optimization
↓
Select Research Demo
↓
Continuous Parameter
↓
Algorithm Settings
↓
Run
↓
Algorithm Trace
↓
Candidate Experiments
↓
Best Result
↓
Fair Evaluation
↓
Evidence

Console Error = 0

---

# 91. Reference Evidence

保存：

reference/algorithm_integration/

例如：

reference/algorithm_integration/OPT-XXXXXXXX/

至少：

README.md

algorithm-metadata.json

parameter-space.json

algorithm-config.json

algorithm-trace.json

optimization.json

evaluation-context.json

verification.json

---

# 92. Reference README

必须：

Optimization ID

Algorithm ID

Algorithm Version

SDK Version

Category

Learning Algorithm

Purpose

Scenario

Backend

Benchmark Protocol

Objective

Parameter Space

Hyperparameters

Evaluation Budget

Evaluations Used

Stop Reason

Baseline

Best Candidate

Network Throughput

P5 Throughput

Fairness Checks

Measured:
NO

Huawei:
NO

Acceptance:
NO

Project Research Deliverable:
NO

---

# 93. Algorithm Provenance

每个 Optimization 保存：

algorithm_id

algorithm_version

algorithm_provider

algorithm_category

sdk_version

learning_algorithm

algorithm_config_hash

parameter_space_hash

source_revision

---

# 94. Source Revision

对于内置算法：

记录：

git commit

未来外部算法：

可以记录：

package version

container digest

repository commit

Day 7 只实现当前可用部分。

---

# 95. Acceptance Center — Day 7 只做数据契约，不做正式页面建设

重要：

Acceptance Center 不放弃。

但 Day 7 不全面建设。

Day 7 只确保 Algorithm / Optimization Evidence
未来可以被 Acceptance Center 查询。

新增轻量：

EvidenceDescriptor

至少：

evidence_id

evidence_type

source_entity_type

source_entity_id

created_at

provenance

verification_status

acceptance_eligible

acceptance_reason

artifacts

---

# 96. acceptance_eligible

Day 7 所有当前仿真证据：

acceptance_eligible = false

原因例如：

simulation_only

not_measured

not_huawei_data

engineering_baseline

unconfirmed_acceptance_kpi

不要因为 verifier PASS：

就变成 acceptance evidence。

---

# 97. Verification != Acceptance

正式区分：

verified:
YES

和：

acceptance_eligible:
NO

例如 Day 6：

Independent Verification:
PASS

但：

Acceptance Evidence:
NO

这两个概念必须长期分离。

---

# 98. Acceptance Center 当前 UI

当前 Coming Soon 页面：

不要删除。

可以轻量更新为：

“验收中心正在积累证据”

显示：

Simulation Evidence
已产生

Measured Validation
尚未接入

Acceptance KPI Mapping
待确认

Third-party / Expert Validation
尚未接入

不要显示：

项目已通过 / 未通过。

---

# 99. Acceptance Center 不做假进度条

禁止：

Acceptance Progress 65%

因为目前没有科学依据。

可以显示：

Evidence Readiness

但必须是离散状态：

Available

Pending

Not Available

Not Applicable

---

# 100. Future Acceptance Mapping

未来 Acceptance Center 会负责：

Task Requirement
        ↓
Software Capability
        ↓
Dataset
        ↓
Experiment
        ↓
KPI
        ↓
Verification
        ↓
Evidence Artifact
        ↓
Acceptance Status

Day 7 只预留 EvidenceDescriptor。

---

# 101. Day 7 不做 Acceptance KPI 判定

不要现在写：

Throughput +10% PASS

Edge +20% FAIL

1000 BS FAIL

这些等后续正式验收协议确定。

---

# 102. Day 7 不做华为数据 Adapter

只保证：

EvidenceDescriptor

未来可以引用：

dataset provenance。

---

# 103. Day 7 不做科研成果认定

Research Demo：

不是：

Project Algorithm

不是：

Research Deliverable

不是：

Acceptance Algorithm

---

# 104. Day 7 Definition of Done

全部满足才算完成：

[ ] Day 4 regression PASS

[ ] Day 5 regression PASS

[ ] Day 6 regression PASS

[ ] AlgorithmAdapter / equivalent interface

[ ] Algorithm lifecycle

[ ] Algorithm Registry

[ ] Algorithm Metadata

[ ] Algorithm Capabilities

[ ] SDK Version

[ ] ParameterDefinition completed

[ ] ParameterSpace

[ ] Continuous parameter

[ ] Discrete parameter

[ ] Integer schema

[ ] Categorical schema

[ ] Vector schema

[ ] Network Variable / Hyperparameter separated

[ ] Algorithm Hyperparameter Schema

[ ] Compatibility validation

[ ] Evaluation budget

[ ] Budget enforcement

[ ] Candidate deduplication

[ ] Evaluation cache

[ ] Grid Search registered as Engineering Baseline

[ ] Research Demo Optimizer

[ ] Research Demo learning_algorithm=false

[ ] Iterative suggest/evaluate/observe works

[ ] Algorithm trace persisted

[ ] Stop reason persisted

[ ] Algorithm provenance persisted

[ ] Algorithm Center enabled

[ ] Algorithm Catalog UI

[ ] Algorithm Detail UI

[ ] Integration Guide

[ ] Optimization Create uses Registry

[ ] Continuous parameter UI

[ ] Algorithm Settings UI

[ ] Compatibility feedback

[ ] Algorithm Trace UI

[ ] Real Research Demo Optimization

[ ] Same Day 6 fair protocol

[ ] Independent verification PASS

[ ] EvidenceDescriptor

[ ] verified != acceptance_eligible

[ ] Acceptance Center placeholder updated honestly

[ ] Unit Tests PASS

[ ] API Tests PASS

[ ] Sionna Integration PASS

[ ] Frontend Tests PASS

[ ] Typecheck PASS

[ ] Build PASS

[ ] Browser Smoke PASS

[ ] Console Error = 0

[ ] Reference Evidence

[ ] Git Commit

[ ] Push

---

# 105. Cursor 最终报告必须包含

1. Code Commit

2. Evidence Commit

3. Changed Files

4. Algorithm SDK Version

5. Registered Algorithms

6. Grid Search Metadata

7. Research Demo Algorithm ID

8. Research Demo Version

9. Research Demo Category

10. learning_algorithm

11. Algorithm Capabilities

12. Supported Parameter Types

13. Parameter Space

14. Algorithm Hyperparameters

15. Auto Configuration

16. Evaluation Budget

17. Evaluations Used

18. Stop Reason

19. Algorithm Trace

20. Scenario

21. Backend

22. Benchmark Protocol

23. Evaluation Context

24. Objective

25. Baseline Parameter

26. Suggested Parameters in Order

27. Candidate Experiment IDs

28. Objective Values

29. Best Candidate

30. Network Throughput Change

31. P5 Change

32. Same UE Verified

33. Same Channel Verified

34. Same Traffic Verified

35. Same Horizon Verified

36. Cache / Dedup Result

37. Independent Verification

38. Algorithm Unit Tests

39. Parameter Tests

40. Compatibility Tests

41. API Tests

42. Sionna Integration Tests

43. Frontend Tests

44. Browser Smoke

45. Console Errors

46. Reference Evidence Path

47. Screenshots

48. Algorithm Provenance

49. EvidenceDescriptor

50. verified status

51. acceptance_eligible status

52. Acceptance Center Current State

53. Assumptions

54. Known Limitations

55. Day 4 Regression

56. Day 5 Regression

57. Day 6 Regression

58. Day 8 Ready YES / NO

---

# 106. Cursor 执行顺序

A. git pull

B. 确认 HEAD 包含 94829c3

C. Day 4–6 regression

D. 阅读当前 Optimizer Interface

E. 阅读 SystemOptimizationService

F. 设计最小 Algorithm Lifecycle

G. Algorithm Metadata / Capabilities

H. ParameterDefinition / ParameterSpace

I. Hyperparameter Schema

J. Compatibility Layer

K. Evaluation Budget

L. Cache / Dedup

M. Algorithm Registry

N. 将 Grid Search 注册进 Registry

O. Research Demo Optimizer

P. Algorithm Tests

Q. Parameter Tests

R. Compatibility Tests

S. API

T. API Tests

U. Algorithm Integration Contract Docs

V. How-to Integration Guide

W. Example Algorithm

X. Algorithm Center

Y. Algorithm Detail

Z. Optimization Create Registry Integration

AA. Continuous Parameter Editor

AB. Algorithm Settings

AC. Compatibility Feedback

AD. Algorithm Trace

AE. EvidenceDescriptor

AF. Acceptance Center honest placeholder

AG. Real Sionna Research Demo Optimization

AH. Independent Verification

AI. Frontend Tests

AJ. Typecheck

AK. Build

AL. Browser Smoke

AM. Console Check

AN. Reference Evidence

AO. Docs / README

AP. Full Regression

AQ. git diff review

AR. Code Commit

AS. Evidence Commit

AT. Push

AU. Final Report

---

# 107. Anti-Cheating / Scientific Integrity

禁止：

把 Research Demo 称为学习优化算法。

禁止：

把 Research Demo 称为项目科研成果。

禁止：

为了超过 Grid Search 调 seed。

禁止：

为了超过 Grid Search 改 benchmark。

禁止：

算法直接访问 Sionna。

禁止：

算法直接访问 KPI implementation。

禁止：

算法直接访问 Experiment Store。

禁止：

算法绕过 Evaluation Budget。

禁止：

跨 Evaluation Context 错误复用 Cache。

禁止：

把 verifier PASS 当成 acceptance PASS。

禁止：

把 simulation evidence 当 measured evidence。

禁止：

把 P5 当验收 Edge User Rate。

禁止：

把 Algorithm Center 做成只有 Grid Search 的硬编码页面。

---

# 108. Day 7 真正成功标准

不是：

“增加了一个算法。”

而是：

“平台第一次形成稳定的算法接入契约，
算法可以独立于仿真器、KPI、前端和证据系统存在，
通过统一 Parameter Space 与 Evaluation Interface
参与真实系统优化实验。”

---

# 109. Day 7 完成后的平台

Research Algorithm
        ↓
Algorithm Adapter
        ↓
Parameter Space
        ↓
Evaluation Budget
        ↓
Fair Evaluation Context
        ↓
Simulation Backend
        ↓
System KPI
        ↓
Objective
        ↓
Observation
        ↓
Research Algorithm
        ↓
Best Candidate
        ↓
Evidence

同时：

Simulation Backend

仍然可以未来：

Sionna
↓
Other Simulator

Algorithm

仍然可以未来：

Python
↓
MATLAB
↓
External
↓
Research Team Algorithm

Parameter Space

仍然可以未来：

Scalar
↓
Continuous
↓
Vector
↓
Large-scale

---

# 110. Day 8 Preview — 不要实现

Day 8 应开始：

First Real Network Optimization Case

优先候选：

User Association / Load Balancing

原因：

它直接对应项目三类问题中的：

用户接入参数优化

并且自然要求：

Multi-cell
Multiple UE
Association Variable
Load
Throughput
Edge-user Metric

Day 8 再正式设计。

不要 Day 7 提前实现。

---

# 111. Acceptance Center Roadmap — 不要提前实现

Acceptance Center 后续阶段：

Phase A
Evidence Contract
← Day 7

Phase B
Acceptance Requirement Matrix

Phase C
KPI Mapping

Phase D
Dataset Provenance / Huawei Data Mapping

Phase E
Scale Benchmark Mapping

Phase F
Expert / Third-party Evidence

Phase G
One-click Acceptance Report

Day 7 只做 Phase A。

---

# 112. Final Instruction

现在执行 Day 7。

重点：

Algorithm Contract
↓
Parameter Space
↓
Research Algorithm Slot
↓
Fair Evaluation
↓
System Simulation
↓
KPI / Objective
↓
Algorithm Feedback
↓
Trace
↓
Evidence

同时：

为 Acceptance Center 建立 Evidence Contract，

但不要提前伪造验收结果。

完成：

Tests
↓
Real Algorithm Run
↓
Independent Verification
↓
Browser E2E
↓
Reference Evidence
↓
Git Commit
↓
Push
↓
Final Report

然后停止。

# END OF DAY 7