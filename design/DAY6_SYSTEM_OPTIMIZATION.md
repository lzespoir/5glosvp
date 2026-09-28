# Day 6 — System Optimization & Fair Benchmark Protocol
# 系统级优化与公平比较协议

> 项目：5G 网络学习优化仿真验证平台
>
> Day 4 Optimization Baseline:
> e2f9100
>
> Day 5 Code:
> fbe2d19
>
> Day 5 Evidence:
> 85fc13f
>
> Day 5 Reference:
> EXP-FC79FFC2
>
> Day 6 目标：
> 第一次把 Optimization Loop 与 System-Level KPI 合并，
> 建立一个真实、可复核、公平比较的 5G 网络优化闭环。
>
> 本任务书供 Cursor Auto 直接执行。
>
> 不要只输出设计。
> 必须实现、测试、真实运行、独立验证、浏览器验证、保存证据、提交 Git。

---

# 0. Day 6 唯一主线

Day 4 已完成：

Network Parameter
    ↓
Optimizer
    ↓
Propagation Simulation
    ↓
Propagation Objective
    ↓
Best Configuration

Day 5 已完成：

BS / Cell / UE
    ↓
Sionna RT
    ↓
Sionna SYS
    ↓
Scheduling
    ↓
Link Adaptation
    ↓
PHY Abstraction
    ↓
UE Throughput
    ↓
Network KPI

Day 6 合并为：

Network Parameter
       ↓
Optimizer
       ↓
Candidate Configuration
       ↓
Fair Evaluation Protocol
       ↓
System Simulation
       ↓
UE Throughput
       ↓
Network KPI
       ↓
System Objective
       ↓
Best Configuration
       ↓
Before / After
       ↓
Evidence

这是 Day 6 唯一主线。

---

# 1. Day 6 最重要的科学约束

禁止：

Baseline 单独随机跑一次
VS
Candidate 单独随机跑一次

然后直接把差值称为：

Optimization Improvement

Day 5 已发现：

相同 Scenario / Seed / UE / Configuration

重复运行 Network Throughput 仍可能约在：

130–139 Mbps

范围内波动。

因此 Day 6 必须首先解决：

FAIR COMPARISON
公平比较

Simulation Noise
不能冒充
Optimization Gain

---

# 2. Day 6 第一原则

所有候选配置必须尽量在：

Same Scenario
Same UE Population
Same Traffic Assumption
Same Channel Realization
Same Simulation Horizon
Same Evaluation Protocol

下进行比较。

目标：

Candidate A
Candidate B
Candidate C

之间唯一应该主动变化的是：

Optimization Variable

其他评价条件必须保持一致。

---

# 3. Common Evaluation Context

新增：

CommonEvaluationContext

或语义等价的数据模型。

至少包含：

context_id

scenario_id

scenario_version

seed

ue_population_id

traffic_realization_id

channel_realization_id

simulation_horizon

backend_id

backend_version

scheduler_config

link_adaptation_config

created_at

metadata

---

# 4. Evaluation Context 的意义

一次 Optimization Run：

不能让每个 Candidate 自己重新随机生成：

UE

Traffic

Channel

应该：

Optimization Run
       ↓
Create / Load Evaluation Context
       ↓
Freeze Evaluation Conditions
       ↓
Evaluate Baseline
       ↓
Evaluate Candidate 1
       ↓
Evaluate Candidate 2
       ↓
...

---

# 5. Channel Realization

Day 6 优先实现：

Channel Snapshot / Channel Realization Reuse

目标：

Sionna RT
    ↓
生成一次固定传播 / channel realization
    ↓
保存
    ↓
Baseline SYS 使用
Candidate SYS 使用
Candidate SYS 使用
...

不要每个候选重新运行 GPU Ray Tracing，
如果优化变量本身不改变传播环境。

---

# 6. 什么时候允许重新运行 RT

如果优化变量本身影响：

Propagation

例如：

TX Power

Antenna Tilt

Antenna Orientation

Antenna Position

则不能机械复用完全相同的最终 channel result。

必须区分：

Geometry / Path Structure

与：

Configuration-dependent Radio Result

Day 6 第一个优化案例应尽量选择：

不要求重新生成随机 RT 路径结构

或可以在固定 channel realization 上公平比较的参数。

---

# 7. Day 6 第一个优化问题

Day 6 不继续使用：

TX Power Grid Search

作为主系统优化案例。

优先选择：

Resource Allocation / Scheduler Parameter

或者：

System-Level Config Parameter

要求：

1. 能影响 UE Throughput；
2. 不要求改变场景几何；
3. 可以共享相同 RT channel realization；
4. 可以通过 System Backend 正式配置；
5. 优化前后因果关系容易解释。

---

# 8. 首选变量：PF Scheduler Beta

如果当前 Sionna SYS API 支持稳定配置：

PFSchedulerSUMIMO beta

优先作为 Day 6 第一个系统优化变量。

候选示例：

0.0
0.3
0.6
0.9
0.99

注意：

这只是建议。

Cursor 必须先检查：

当前 Sionna 2.1 API

当前 backend

官方文档

确认 beta 的实际语义和允许范围。

禁止凭记忆猜 API。

如果 beta 不适合作为优化变量：

选择另一个明确、稳定、系统级、非几何参数。

---

# 9. 不允许为了漂亮结果选参数

选择优化变量的标准：

Scientific Meaning
科学意义

Backend Controllability
后端可控

Fair Evaluation
公平评价

Traceability
可追溯

而不是：

“哪个参数能产生最大的提升”。

---

# 10. Day 6 Optimizer

继续使用：

Grid Search

作为第一版系统优化器。

原因：

Grid Search 已经过 Day 4 验证。

Day 6 要验证的是：

System Optimization Pipeline

不是：

新的优化算法。

必须继续标记：

category = engineering_baseline

learning_algorithm = false

---

# 11. 不接科研学习算法

Day 6 禁止顺手接：

Zero-order Learning

Algorithm Unrolling

Prediction Search

Branch-and-Bound

Research Learning Optimizer

这些后续再接。

先把系统优化协议做正确。

---

# 12. Parameter Space 不能写死为几个值

Day 4 当前 Grid Search 可以继续使用：

choices

但 Day 6 应开始形成：

ParameterDefinition

至少能够表达：

name

type

unit

default

bounds

choices

constraints

source

---

# 13. Parameter Type

至少设计支持：

continuous

integer

discrete

categorical

vector

Day 6 Grid Search 实际只需：

discrete choices

但 domain model 不得写死：

list[float]

未来算法必须允许直接产生：

0.734

而不需要预先枚举。

---

# 14. Network Variable 与 Algorithm Hyperparameter

必须区分：

Optimization Variable
网络优化变量

例如：

scheduler_beta

与：

Algorithm Hyperparameter
算法超参数

例如：

max_iterations

tolerance

Day 6 UI 不要把两者混成一个：

Parameters

---

# 15. System Objective

Day 6 建立第一个：

SYSTEM_OBJECTIVE_V0_1

但不要立刻设计复杂加权公式。

优先选择：

单一、明确、可解释 KPI。

建议：

NETWORK_THROUGHPUT_MAX_V0_1

Objective：

maximize

NETWORK_THROUGHPUT_V0_1

---

# 16. 为什么第一版只优化 Network Throughput

Day 6 的目标是：

证明系统 KPI 能真正进入 Optimization Loop。

因此先：

J = Network Throughput

不要一开始：

Throughput
+
P5
+
Power
+
Fairness
+
Coverage

混成复杂 Objective。

否则无法判断优化到底为什么成功。

---

# 17. Objective Definition

新增：

docs/objectives/network-throughput-max-v0.1.md

至少写：

ID

Version

Direction

Input KPI

Formula

Unit

Required Experiment Type

Required Backend Capability

Assumptions

Limitations

Acceptance Status

---

# 18. Acceptance Status

必须：

Acceptance KPI:
NO

Measured Data:
NO

Huawei Data:
NO

Day 6 是：

System Optimization Validation

不是：

Project Acceptance Validation

---

# 19. Optimization Result

System Optimization Result 必须保存：

optimization_id

optimizer

objective

parameter_definition

baseline

candidates

best_candidate

evaluation_context

comparison

provenance

runtime

warnings

---

# 20. Candidate Result

每个 Candidate 至少：

candidate_id

parameter_value

experiment_id

evaluation_context_id

network_throughput

average_ue_throughput

p5_ue_throughput

objective_value

runtime

status

artifacts

---

# 21. 不只保存 Objective

即使 Objective 只有：

Network Throughput

仍必须同时保存：

Average UE Throughput

P5 UE Throughput

原因：

防止出现：

Network Throughput ↑
但
P5 Throughput ↓↓↓

却被 UI 简化成：

Optimization Successful

---

# 22. Trade-off 必须可见

如果：

Network Throughput
+5%

但：

P5 UE Throughput
-20%

UI 必须展示。

不能只显示绿色：

+5%

---

# 23. “Best” 的语义

Best Candidate 只能表示：

Best under
NETWORK_THROUGHPUT_MAX_V0_1

不能表示：

Best Network Configuration

更不能表示：

Best 5G Configuration

UI 推荐：

“当前目标下最优候选”

Best Candidate Under Current Objective

---

# 24. Improvement

保存：

absolute_improvement

relative_improvement

但 relative improvement 只在：

baseline != 0

时计算。

不要强制为正。

如果：

Best == Baseline

允许：

0%

如果所有 candidate 更差：

Baseline 可以保持最优。

---

# 25. Baseline 必须进入同一个 Evaluation Context

禁止：

Day 5 Reference EXP-FC79FFC2

直接拿来与 Day 6 Candidate 比较。

Day 5 Reference：

可以作为系统链证据。

但 Day 6：

Baseline 必须在 Day 6 的同一个：

Evaluation Context

中重新评价。

---

# 26. Benchmark Protocol

新增：

BenchmarkProtocol

至少：

protocol_id

version

num_repeats

simulation_slots

warmup_slots

aggregation_method

common_channel

common_ue_population

common_traffic

seed_policy

---

# 27. Day 6 先做 Simulation Horizon Study

在正式优化前：

必须运行：

200 slots
500 slots
1000 slots

或在当前性能允许下类似梯度。

目的：

观察：

Network Throughput

Average UE Throughput

P5 UE Throughput

随 simulation horizon 的稳定性。

---

# 28. Horizon Study 不是挑最好看的

禁止：

“500 slots 提升最大，所以选 500”。

选择标准：

KPI Stability
vs
Runtime Cost

保存：

reference/day6_horizon_study/

README.md

results.json

plot.png

---

# 29. Warm-up

检查当前：

PF Scheduler

OLLA

HARQ

是否存在明显启动 transient。

如果存在：

Benchmark Protocol 应支持：

warmup_slots

例如：

前 N slots 不进入 KPI aggregation。

但：

不要凭感觉设值。

先观察。

如果 Day 6 不实现 warm-up：

明确：

warmup_slots = 0

并记录限制。

---

# 30. Repeat Protocol

如果固定 Channel Realization 后：

SYS CPU 完全 deterministic

则：

num_repeats = 1

可以成立。

但必须通过实验验证。

如果仍有随机性：

必须：

num_repeats > 1

并使用：

mean

或明确的 aggregation。

---

# 31. Candidate Comparison Noise

如果候选仍存在重复运行波动：

必须保存：

mean

std

min

max

n

不能只保存：

single value

---

# 32. Improvement Significance

Day 6 不要求正式统计显著性检验。

但如果：

candidate improvement

小于或接近：

simulation variability

UI 必须警告：

“Improvement is within observed simulation variability.”

中文：

“改善幅度处于已观测仿真波动范围内。”

---

# 33. 不伪造置信区间

除非真正有足够重复实验并实现统计计算。

禁止：

Confidence = 95%

这种装饰性数字。

---

# 34. Evaluation Protocol Evidence

每个 Optimization Run 必须能够回答：

Baseline 和 Candidate：

是否使用相同 UE？

YES / NO

是否使用相同 Traffic？

YES / NO

是否使用相同 Channel Realization？

YES / NO

Simulation Slots 是否相同？

YES / NO

Backend Version 是否相同？

YES / NO

---

# 35. Fairness Badge

前端 Optimization Detail 增加：

Evaluation Protocol

例如：

✓ Same UE Population

✓ Same Channel Realization

✓ Same Traffic Model

✓ Same Simulation Horizon

✓ Same Backend Version

不要叫：

Scientifically Proven

只叫：

Fair Evaluation Conditions

---

# 36. Channel Realization ID

保存：

channel_realization_id

例如：

CH-XXXXXXXX

并记录：

source scenario

seed

provider

provider version

hash

created_at

---

# 37. Channel Artifact Hash

如果保存 channel snapshot：

计算：

SHA-256

Baseline / Candidate 必须引用相同：

channel_realization_id

和：

hash

才能声称：

Same Channel Realization

---

# 38. 如果 Channel 太大

不要提交巨大 channel artifact 到 Git。

Artifact Store 保存。

Reference Evidence：

只保存：

metadata

hash

shape

summary

---

# 39. Traffic Realization

Day 6 当前：

Full Buffer

因此可以：

traffic_realization_id

指向固定：

FULL_BUFFER_V0_1

未来真实 Traffic Replay：

再扩展。

---

# 40. UE Population

保存：

ue_population_id

UE positions

serving cell

生成器

seed

hash

Baseline / Candidate 必须一致。

---

# 41. SystemOptimizationService

新增或扩展：

SystemOptimizationService

职责：

1. validate problem
2. create evaluation context
3. prepare shared artifacts
4. evaluate baseline
5. enumerate candidates
6. evaluate candidates
7. compute KPI
8. evaluate objective
9. select best
10. compare
11. persist
12. produce evidence

---

# 42. Optimizer 不得直接调用 Sionna

保持：

GridSearchOptimizer
       ↓
CandidateEvaluator
       ↓
SystemOptimizationService
       ↓
SystemSimulationBackend

禁止：

GridSearchOptimizer
       ↓
SionnaSystemBackend

---

# 43. Objective 不得调用 Sionna

正确：

System Result
    ↓
KPI Engine
    ↓
Objective Evaluator

---

# 44. Frontend 不得计算 Objective

继续后端计算。

Frontend：

display only

---

# 45. API

至少：

GET /api/v1/system-optimizers

GET /api/v1/system-objectives

GET /api/v1/benchmark-protocols

POST /api/v1/system-optimizations

GET /api/v1/system-optimizations

GET /api/v1/system-optimizations/{id}

如果能自然复用现有：

/optimizers
/objectives
/optimizations

可以复用。

不要为了 Day 6 复制两套架构。

---

# 46. API Contract 优先统一

如果现有 Optimization API 可以增加：

problem_type:
propagation | system

优先采用。

例如：

{
  "problem_type": "system",
  "scenario_id": "SYSTEM-DEMO-001",
  "optimizer_id": "grid_search",
  "objective_id": "NETWORK_THROUGHPUT_MAX_V0_1",
  "parameter": {...},
  "benchmark_protocol_id": "SYSTEM_BENCHMARK_V0_1"
}

---

# 47. 不破坏 Day 4 Optimization

现有：

PROPAGATION_UTILITY_V0_1

必须继续工作。

旧 Optimization Records：

必须继续打开。

---

# 48. Day 6 UI 入口

Optimization Center 增加：

Optimization Type

传播层优化
Propagation Optimization

系统级优化
System Optimization

新用户不应该面对两个完全独立系统。

---

# 49. New System Optimization

用户选择：

Scenario

Objective

Optimization Variable

Optimizer

Evaluation Protocol

然后：

Run

---

# 50. Advanced Settings

Simulation Slots

Repeat Count

Scheduler Settings

等放：

Advanced

默认使用：

Frozen Benchmark Protocol

避免普通用户面对几十个参数。

---

# 51. Parameter UI

Day 6 当前 Grid Search：

可以显示：

Candidate Values

例如：

0.0
0.3
0.6
0.9
0.99

但 UI 不得暗示：

所有算法都只能枚举候选值。

ParameterDefinition 要允许未来：

Range

Continuous

Algorithm Generated

---

# 52. Algorithm Settings

Grid Search：

无需复杂设置。

未来 Algorithm Hyperparameters：

预留独立区域：

Algorithm Settings

不要和：

Optimization Variable

混在一起。

---

# 53. Running State

系统优化可能：

Baseline
+
多个 Candidates
+
SYS Simulation

运行时间较长。

UI 可以显示真实阶段：

Preparing Evaluation Context

Running Baseline

Evaluating Candidate 1/5

Evaluating Candidate 2/5

...

Selecting Best

Persisting Evidence

---

# 54. 不要 Fake Progress

可以：

Candidate 2 / 5

不可以：

73%

除非后端确实提供真实进度。

---

# 55. System Optimization Detail

顶部：

Optimization ID

Scenario

Status

Optimizer

Objective

Optimization Variable

Benchmark Protocol

Backend

Runtime

---

# 56. Hero Comparison

显示：

BASELINE

VS

BEST CANDIDATE

例如：

Scheduler Beta
0.9
→
0.6

Network Throughput
XXX
→
YYY Mbps

Δ
+Z%

---

# 57. Secondary KPI

同时显示：

Average UE Throughput

P5 UE Throughput

必须展示方向。

例如：

Network Throughput
+4.2%

Average UE Throughput
+4.2%

P5 UE Throughput
-8.1%

不能隐藏负值。

---

# 58. Candidate History

真实 candidate results：

X:
Parameter Value

Y:
Objective

不使用平滑曲线伪造连续优化过程。

Grid Search：

用 point / bar 更合适。

---

# 59. Candidate Table

至少：

Candidate

Parameter

Experiment

Network Throughput

Average Throughput

P5 Throughput

Objective

Runtime

Status

---

# 60. Candidate → Experiment

点击：

进入 System Experiment Detail

必须保留回链：

Experiment
→
Optimization

---

# 61. UE Before / After

增加：

Per-UE Throughput Comparison

例如：

UE-001
Baseline vs Best

...

这样可以看到：

整体吞吐率提升是否牺牲某些用户。

---

# 62. UE Distribution Before / After

可以：

CDF

或：

sorted UE throughput

但 Day 6 不要求复杂统计图。

优先清晰。

---

# 63. Objective Detail

点击：

NETWORK_THROUGHPUT_MAX_V0_1

显示：

Definition

Version

Direction

Input KPI

Baseline Value

Best Value

Absolute Improvement

Relative Improvement

Acceptance:
NO

---

# 64. Evaluation Protocol Panel

必须突出显示：

Benchmark Protocol

Same UE Population

Same Traffic

Same Channel

Simulation Slots

Warmup Slots

Repeat Count

Aggregation

Backend

Provider Version

Hashes

---

# 65. Provenance

System Optimization provenance 至少：

optimizer

optimizer_version

learning_algorithm

objective

objective_version

scenario

evaluation_context

backend

backend_version

channel_realization

ue_population

traffic_model

benchmark_protocol

seed

git_commit

measured

acceptance_evidence

---

# 66. Scientific Boundary

页面明确：

“当前结果来自系统级仿真优化验证，不是华为实测网络优化结果。”

并：

“Grid Search 为工程基线优化器，不属于项目学习优化算法。”

---

# 67. Improvement 文案

允许：

“Network Throughput improved by X% under the frozen simulation protocol.”

中文：

“在当前冻结仿真协议下，网络吞吐率提高 X%。”

禁止：

“5G 网络性能提升 X%”

禁止：

“项目指标提升 X%”

禁止：

“现网提升 X%”

---

# 68. If No Improvement

如果结果：

Baseline 最好

UI：

“No candidate improved the objective.”

中文：

“当前候选范围内未发现优于基线的配置。”

这属于有效实验结果。

---

# 69. 不调参数追求 Improvement

禁止：

发现没有提升
→
换 seed
→
换 UE
→
换 candidate
→
直到变绿

如果参数空间需要改变：

必须产生：

new experiment / new protocol version

不能覆盖 Reference Run。

---

# 70. Independent Verification

新增：

scripts/verify_system_optimization.py

不得 import：

production objective evaluator

production KPI evaluator

它独立读取：

optimization.json

candidate experiment artifacts

KPI

evaluation context

重新验证：

candidate parameter

experiment link

same UE hash

same channel hash

same traffic

same horizon

network throughput

objective

best selection

improvement

---

# 71. Independent Verification 至少检查

Baseline exists

Candidates exist

Candidate count

Parameter values

Unique candidate IDs

Experiment IDs

Context ID

UE hash equality

Channel hash equality

Traffic equality

Slots equality

Backend equality

Network throughput recomputation

Average recomputation

P5 recomputation

Objective recomputation

Best candidate selection

Absolute improvement

Relative improvement

Negative KPI changes preserved

Provenance

---

# 72. Tie Break

如果 Objective 相同：

必须 deterministic。

对于 Scheduler Beta：

不要随便假设越低越好。

优先：

baseline value if tied

否则：

candidate order

并记录 tie_break_rule。

---

# 73. Tests — Evaluation Context

至少：

test_evaluation_context_creation

test_ue_population_frozen

test_channel_realization_frozen

test_traffic_frozen

test_context_hashes

test_context_serialization

---

# 74. Tests — Parameter Definition

至少：

test_discrete_parameter

test_continuous_parameter_schema

test_invalid_bounds

test_invalid_choice

test_parameter_unit

test_algorithm_generated_future_schema

不要求实现 continuous optimizer。

---

# 75. Tests — System Objective

至少：

test_network_throughput_objective

test_objective_direction_maximize

test_objective_version

test_zero_baseline_relative_improvement

test_negative_improvement

test_tie_break

---

# 76. Tests — Optimization Service

至少：

test_baseline_same_context

test_candidate_same_context

test_candidate_parameter_applied

test_candidate_experiment_created

test_best_candidate_selected

test_no_improvement

test_failed_candidate

test_partial_failure_policy

---

# 77. Failed Candidate Policy

一个 Candidate 仿真失败：

不要整个 Optimization 自动丢失。

记录：

status = failed

error

其他 Candidate 继续。

如果：

Baseline failed

则 Optimization：

FAILED

因为没有比较基准。

---

# 78. All Candidates Failed

Optimization：

FAILED

保留所有 evidence。

---

# 79. Tests — Fairness

至少：

test_same_ue_hash

test_same_channel_hash

test_same_traffic

test_same_slots

test_backend_version_same

test_fairness_false_if_context_differs

---

# 80. Tests — API

至少：

test_create_system_optimization

test_get_system_optimization

test_list_system_optimizations

test_invalid_objective

test_invalid_parameter

test_backend_missing_capability

test_failed_baseline

test_failed_candidate_preserved

---

# 81. FakeSystemOptimizationBackend

Unit tests 使用 deterministic backend。

不要每个测试跑 40 秒 Sionna。

---

# 82. Real Sionna Integration

至少一条真实：

System Optimization

但 Candidate 数量可以小：

3 candidates

用于 CI/integration。

Reference Run 可以使用：

完整候选集合。

---

# 83. Horizon Study Test

真实执行：

200
500
1000

如果 1000 成本不可接受：

200
400
600

也可以。

但必须报告：

runtime

network throughput

average

P5

variation

---

# 84. Benchmark Protocol Freeze

Horizon Study 后冻结：

SYSTEM_BENCHMARK_V0_1

文档：

docs/benchmark/system-benchmark-v0.1.md

内容：

simulation slots

warmup

repeats

aggregation

shared channel

shared UE

traffic

backend

limitations

---

# 85. 不要偷偷修改 Protocol

Reference Optimization 一旦运行：

Protocol V0.1

冻结。

未来改变：

slots
warmup
repeat
aggregation

必须：

V0.2

---

# 86. Browser Smoke

真实浏览器：

首页
↓
Optimization Center
↓
System Optimization
↓
选择 Scenario
↓
选择 Objective
↓
选择 Parameter
↓
选择 Grid Search
↓
Run
↓
真实 Baseline
↓
真实 Candidates
↓
Detail
↓
Before / After
↓
Secondary KPI
↓
Candidate History
↓
Candidate Table
↓
Candidate Experiment
↓
Back Link
↓
Evaluation Protocol
↓
Provenance

Console Error = 0

---

# 87. Reference Evidence

保存：

reference/system_optimization/OPT-XXXXXXXX/

至少：

README.md

optimization.json

evaluation-context.json

benchmark-protocol.json

candidate-summary.json

verification.json

comparison.png

per-ue-comparison.png

---

# 88. Screenshot

至少：

01_create.png

02_running.png

03_result.png

04_candidate_history.png

05_candidate_table.png

06_per_ue.png

07_evaluation_protocol.png

08_candidate_experiment.png

---

# 89. Reference README

必须：

Optimization ID

Commit

Scenario

Backend

Backend Version

Optimizer

Learning Algorithm:
NO

Objective

Optimization Variable

Baseline Parameter

Candidate Values

Best Parameter

Baseline Network Throughput

Best Network Throughput

Absolute Improvement

Relative Improvement

Baseline P5

Best P5

Benchmark Protocol

Simulation Slots

Warmup

Repeat Count

Same UE:
YES/NO

Same Channel:
YES/NO

Same Traffic:
YES/NO

Measured:
NO

Huawei:
NO

Acceptance:
NO

---

# 90. Reference Run 不要求 Improvement

Reference Run 的价值：

真实

公平

可重复

可追溯

不是：

必须绿色。

如果：

0%

或：

negative

照样提交。

---

# 91. Day 6 不做科研算法

再次强调：

不要因为 Day 6 已经有 System Objective，

顺手接研究组算法。

Day 7 或后续专门接。

---

# 92. Day 6 不做多小区

保持：

SYSTEM-DEMO-001

1 BS / 1 Cell / 6 UE

除非优化变量本身必须多 Cell。

如果选择 Scheduler Beta：

不需要多 Cell。

---

# 93. Day 6 不做 1000 Cells

禁止。

---

# 94. Day 6 不做华为数据

禁止把 simulation result 叫：

Measured Validation。

---

# 95. Day 6 不做 Acceptance KPI

P5 仍然：

Engineering Metric

不是：

Acceptance Edge User Rate。

---

# 96. Day 6 不做通用插件系统

继续保持：

interface-ready

implementation-focused

不要：

Plugin Marketplace

Dynamic Loader

Remote Runtime Manager

---

# 97. Day 6 不做复杂权限

No Auth

No RBAC

No User Management

---

# 98. Day 6 Definition of Done

全部满足才算完成：

[ ] Day 4 regression PASS

[ ] Day 5 regression PASS

[ ] Horizon Study 完成

[ ] Benchmark Protocol V0.1 冻结

[ ] CommonEvaluationContext

[ ] UE Population freeze

[ ] Traffic freeze

[ ] Channel realization freeze / reuse

[ ] Channel hash

[ ] ParameterDefinition

[ ] Network Variable / Hyperparameter 语义分离

[ ] System Objective V0.1

[ ] Grid Search reused

[ ] SystemOptimizationService

[ ] Baseline in same context

[ ] Candidates in same context

[ ] Same UE verified

[ ] Same Channel verified

[ ] Same Traffic verified

[ ] Same Horizon verified

[ ] System KPI used as Objective

[ ] Secondary KPI preserved

[ ] Negative trade-offs visible

[ ] Candidate experiments persisted

[ ] Failed candidate preserved

[ ] Optimization API

[ ] System Optimization UI

[ ] Before / After

[ ] Candidate History

[ ] Candidate Table

[ ] Per-UE Comparison

[ ] Evaluation Protocol Panel

[ ] Provenance

[ ] Scientific Boundary

[ ] Independent Verification

[ ] Unit Tests PASS

[ ] API Tests PASS

[ ] Sionna Integration PASS

[ ] Frontend Tests PASS

[ ] Typecheck PASS

[ ] Build PASS

[ ] Browser Smoke PASS

[ ] Console Error = 0

[ ] Real Reference Optimization completed

[ ] Reference Evidence saved

[ ] Git Commit

[ ] Push

---

# 99. Cursor 最终报告必须包含

1. Code Commit

2. Evidence Commit

3. Changed Files

4. Sionna Version

5. Horizon Study Results

6. Selected Simulation Horizon

7. Warmup Slots

8. Repeat Count

9. Aggregation Method

10. Benchmark Protocol ID

11. Optimization ID

12. Scenario ID

13. Evaluation Context ID

14. UE Population ID / Hash

15. Channel Realization ID / Hash

16. Traffic Realization ID

17. Backend

18. Optimizer

19. learning_algorithm

20. Objective ID

21. Parameter Definition

22. Baseline Parameter

23. Candidate Values

24. Candidate Experiment IDs

25. Candidate Network Throughputs

26. Candidate Average Throughputs

27. Candidate P5 Throughputs

28. Best Candidate

29. Baseline Objective

30. Best Objective

31. Absolute Improvement

32. Relative Improvement

33. P5 Change

34. Per-UE Before/After

35. Same UE Verified

36. Same Channel Verified

37. Same Traffic Verified

38. Same Horizon Verified

39. Independent Verification

40. Unit Tests

41. API Tests

42. Integration Tests

43. Frontend Tests

44. Browser Smoke

45. Console Errors

46. Reference Evidence Path

47. Screenshots

48. Provenance

49. Assumptions

50. Known Limitations

51. Day 4 Regression

52. Day 5 Regression

53. Day 7 Ready YES/NO

---

# 100. Cursor 执行顺序

A. git pull

B. 确认 HEAD 包含 85fc13f

C. Day 4 + Day 5 regression

D. 阅读当前 System Backend

E. 阅读当前 Scheduler API

F. 验证候选系统参数的真实可控性

G. Horizon Study

H. 分析稳定性 / runtime

I. 冻结 SYSTEM_BENCHMARK_V0_1

J. 实现 CommonEvaluationContext

K. 实现 UE population freeze/hash

L. 实现 channel realization freeze/hash

M. 实现 traffic realization identity

N. ParameterDefinition

O. System Objective

P. Objective tests

Q. Fairness tests

R. SystemOptimizationService

S. CandidateEvaluator

T. Grid Search integration

U. Fake tests

V. API

W. API tests

X. Real Sionna integration

Y. Independent verification script

Z. 真实 Reference Optimization

AA. 独立复核

AB. System Optimization frontend

AC. Before/After

AD. Candidate History

AE. Candidate Table

AF. Per-UE Comparison

AG. Evaluation Protocol

AH. Provenance

AI. Frontend tests

AJ. Typecheck

AK. Build

AL. Browser real E2E

AM. Console check

AN. Evidence

AO. Docs

AP. README

AQ. Full regression

AR. git diff review

AS. commit code

AT. commit evidence

AU. push

AV. final report

---

# 101. 最重要的 Anti-Cheating Rules

禁止：

为了获得 improvement 修改 seed。

禁止：

Baseline 和 Candidate 使用不同 UE。

禁止：

Baseline 和 Candidate 使用不同 Traffic。

禁止：

在声称 Same Channel 时使用不同 channel artifact。

禁止：

把 GPU RT 波动当成优化收益。

禁止：

发现候选不提升就调 Objective。

禁止：

发现结果不好就改变 candidate range 后覆盖旧结果。

禁止：

把 Grid Search 称为 Learning Optimization。

禁止：

把 P5 称为项目验收 Edge User Rate。

禁止：

把 simulation throughput 称为 Huawei measured throughput。

禁止：

前端重新计算 KPI。

禁止：

前端重新计算 Objective。

禁止：

Optimizer 直接调用 Sionna。

禁止：

Objective 直接调用 Sionna。

---

# 102. Day 6 的真正成功标准

不是：

“找到一个吞吐率更高的参数。”

而是：

“证明平台可以在公平、冻结、可追溯的系统仿真条件下，
使用统一 Optimizer Interface，
改变一个真实系统参数，
执行多个真实 Sionna System Experiments，
使用版本化 System KPI 评价候选，
选择当前 Objective 下的最佳配置，
并完整解释优化前后变化。”

---

# 103. Day 6 完成后的能力

Day 5：

5G System Simulation

Day 6：

5G System Optimization

平台链路变成：

Scenario
    ↓
BS / Cell / UE
    ↓
Evaluation Context
    ↓
Optimizer
    ↓
Network Parameter
    ↓
Sionna RT / SYS
    ↓
Scheduling
    ↓
Link Adaptation
    ↓
UE Throughput
    ↓
Network KPI
    ↓
Objective
    ↓
Best Candidate
    ↓
Before / After
    ↓
Evidence

---

# 104. Future Extension

Day 6 架构必须允许未来：

Grid Search
↓
Learning Optimizer

Discrete Parameter
↓
Continuous / Vector Parameter

Scheduler Parameter
↓
Antenna / Association / Resource Parameters

Single Cell
↓
Multi-Cell

Synthetic Scenario
↓
Huawei Measured Scenario

Sionna
↓
Other Simulation Backend

但 Day 6 不实现这些。

---

# 105. Day 7 Preview — 不要实现

Day 7 不应继续堆基础架构。

Day 7 候选方向：

A. Research Algorithm Integration
科研算法接入

B. Multi-Cell First Real 5G Optimization Case
第一个多小区网优案例

C. Acceptance Center / Evidence Report
验收证据中心

具体选择：

必须根据 Day 6 结果决定。

不要提前实现。

---

# 106. Final Instruction

现在执行 Day 6。

第一优先级：

FAIR COMPARISON

第二优先级：

SYSTEM OPTIMIZATION LOOP

第三优先级：

TRACEABLE EVIDENCE

不要追求漂亮提升数字。

不要增加新科研算法。

不要扩规模。

不要改 Day 4 / Day 5 已冻结定义。

完成：

Fair Context
    ↓
Grid Search
    ↓
Real System Parameter
    ↓
Sionna System Simulation
    ↓
Network Throughput Objective
    ↓
Best Candidate
    ↓
Secondary KPI Trade-off
    ↓
Independent Verification
    ↓
Browser E2E
    ↓
Reference Evidence

然后停止。

# END OF DAY 6