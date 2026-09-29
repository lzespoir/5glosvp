# Day 11 --- Platform Integrity Closure, Execution Management & User-Directed Comparison

## 历史源码审计收口 + 执行生命周期管理 + 用户主导的对比分析重构

> **Base commit:** `29fa38a feat: complete day10 algorithm onboarding`
>
> 本任务书不是只根据 Day 10 报告编写。
>
> 在进入 Day 11 前，对 Day 4--Day 10 关键提交和当前 `29fa38a`
> 源码进行了回溯审计。
>
> 目标不是推翻历史成果，而是把此前"报告审查通过、但源码层仍存在的工程债务"一次收口，再继续扩展平台。

------------------------------------------------------------------------

# 0. 平台定位再次冻结

本项目是：

**5G 学习优化仿真验证平台**

平台负责：

-   接入算法；
-   接入问题；
-   接入数据/场景；
-   执行实验；
-   管理资源和生命周期；
-   计算/展示 KPI；
-   记录条件和参数；
-   判断是否具备直接比较条件；
-   允许用户主动创建对比；
-   生成可追溯证据。

平台不负责：

-   选择"最优算法"；
-   替研究人员决定研究路线；
-   为算法调参获得更漂亮结果；
-   自动宣布某算法先进；
-   把所有历史实验自动拼成排行榜。

------------------------------------------------------------------------

# 1. 回溯源码审计结论

## Day 4 --- Optimization Loop

结论：**核心实现 PASS，保留。**

源码/设计明确：

-   Grid Search 是 engineering baseline；
-   Objective 在后端计算；
-   `PROPAGATION_UTILITY_V0_1` 明确不是吞吐率、边缘用户速率或验收 KPI；
-   候选通过统一 evaluator 运行。

Day 11 不修改冻结 Objective 语义。

遗留工程债：

-   传播实验仍继承 Day 2 同步/soft-timeout 执行模型；
-   未来统一纳入 Execution Manager。

------------------------------------------------------------------------

# 2. Day 5 --- System-Level KPI

结论：**核心仿真链 PASS，保留。**

当前源码真实链：

`Sionna RT → CFR → PFSchedulerSUMIMO → power control → RZF/LMMSE → OLLA → PHYAbstraction → decoded bits → KPI`

KPI 仍由平台 evaluation 层计算，而不是前端伪造。

P5 继续保持：

`engineering metric`

不得映射成任务书最终"边缘用户速率"。

遗留债：

-   SystemExperimentService 仍是同步执行；
-   进程内 `_run_lock` 一次只允许一个系统实验；
-   没有独立 worker / cancel / force terminate；
-   后续统一纳入 Execution Manager。

------------------------------------------------------------------------

# 3. Day 6 --- Fair System Optimization

结论：**候选内公平评价 PASS，保留。**

源码确认：

-   每次 optimization 先 `realize_channel()` 一次；
-   baseline/candidates 共享 frozen channel；
-   candidate 运行不重新 RT；
-   `CommonEvaluationContext` 思路成立。

但必须保持历史解释：

不同 optimization run 之间如果重新 RT：

不能直接把差异解释成算法收益。

Day 11 不修改 `SYSTEM_BENCHMARK_V0_1` 历史 reference。

遗留债：

-   system optimization 使用 daemon thread；
-   执行生命周期仍属于进程内线程；
-   无正式 cancellation/process ownership；
-   纳入 Day 11 Execution Manager 的迁移计划，但不要一次重写所有历史
    service。

------------------------------------------------------------------------

# 4. Day 7 --- Algorithm SDK

结论：**SDK 核心边界 PASS，保留。**

源码确认：

-   AlgorithmDriver 不接触 simulator；
-   平台执行 evaluation budget；
-   `suggest → evaluate → observe` 链真实存在；
-   Registry 不依赖业务层算法名分支；
-   Research Demo 是 integration demo，不是 learning/research result。

需要修正的工程语义：

当前 AlgorithmDriver 对 parameter-space validation 失败直接抛
`AlgorithmExecutionError`，会终止整个 run。

Day 11 不强制改变这一行为，但要明确：

-   `suggestions beyond remaining budget` = rejected suggestion；
-   `invalid suggestion` = algorithm contract violation；
-   两者不能混为同一种 rejected。

Trace/UI 必须区分。

------------------------------------------------------------------------

# 5. Day 8 --- Multi-Cell User Association

结论：**核心因果链 PASS WITH SOURCE-LEVEL DEBT。**

源码确认：

-   真实 Sionna RT 多 Cell→UE link gain；
-   association 进入 signal/interference/resource share/throughput
    计算；
-   interference 明确是 platform approximation；
-   不是 Sionna SYS multi-cell scheduler。

## P0-8A --- Scenario ID 静默回退

当前：

``` python
p = configs_dir / f"{scenario_id.lower()}.yaml"
if not p.exists():
    p = configs_dir / "multicell_demo.yaml"
```

这是证据完整性风险。

请求不存在的 Scenario：

**绝不能静默跑 MULTICELL-DEMO-001。**

Day 11 必须改成：

`SCENARIO_NOT_FOUND`

API 返回明确 404/业务错误。

禁止 fallback。

必须增加 regression/tamper test。

## P1-8B --- Channel Hash V0.1 未直接绑定完整几何

当前 hash 主要绑定：

-   scenario_id；
-   UE IDs；
-   Cell IDs；
-   gains；
-   seed。

没有直接把 UE/Cell coordinates/full geometry 纳入 canonical payload。

Day 8 历史 hash 不重写。

Day 11 新增：

`ChannelProvenanceHash V0.2`

至少绑定：

-   scenario ID/version；
-   UE IDs + coordinates；
-   Cell/BS IDs + coordinates；
-   frequency；
-   bandwidth；
-   antenna/config if propagation-relevant；
-   scene；
-   seed；
-   link artifact digest；
-   provider versions where appropriate。

历史：

`CH-MULTICELL-FBD449D7`

继续保留 V0.1 身份。

------------------------------------------------------------------------

# 6. Day 9 --- Algorithm Benchmark

结论：**公平 Benchmark reference 有价值，但"通用 Benchmark
平台"程度被高估，需要收口。**

源码确认：

-   Day 8 frozen link artifact 被恢复；
-   Benchmark 不重新 trace RT；
-   三个 runnable algorithms 使用同一 frozen context；
-   runtime split 存在；
-   Research Catalog 与 runnable registry 分离。

## P0-9A --- Verification 状态矛盾

当前 `_export()` 同时写：

``` text
verification.json:
status = pending_independent_verifier
```

但：

``` text
evidence-descriptor.json:
verified = true
verification = independent_verified
```

并且 Benchmark provenance 也提前写：

`verification = independent_verified`

这是错误的 evidence state semantics。

必须修。

正确状态机：

``` text
UNVERIFIED
→ PENDING
→ VERIFIED
   or FAILED
```

只有 verifier 实际 PASS 后才能写：

``` text
verified = true
verification_status = independently_verified
verifier_id
verified_at
verification_hash
```

## P1-9B --- BenchmarkService 是 Problem-specific，不是通用 Benchmark Engine

当前 BenchmarkService 直接依赖：

-   UserAssociationService；
-   MultiCellBackend；
-   AssociationOptimizationService；
-   Day 8 frozen reference path。

所以 Day 9 已经证明：

`USER_ASSOCIATION algorithm benchmark`

但不能把当前 service 当成完全 problem-agnostic benchmark engine。

Day 11 不要求把所有 Benchmark 泛化。

先建立通用：

`Comparison`

和：

`ProblemEvaluationAdapter`

再逐步迁移。

## P1-9C --- Association Baseline 不是公平的"算法速度竞争者"

`association_baseline_v0_1` 本质是 common
incumbent/reference，几乎不执行搜索。

因此：

-   可以作为 KPI reference；
-   可以出现在结果表；
-   不应该和真正搜索算法直接解释成"算法速度优劣"。

UI/Comparison metadata 增加：

`role = reference | optimizer`

Runtime 图中明确区分。

## P1-9D --- 参数类型 metadata

当前 association vector 在底层 ParameterDefinition 使用
`CATEGORICAL`，同时 metadata 标注 `categorical_vector`。

Day 11 做 schema consistency audit。

不要为了改名字破坏 SDK 0.1。

如需正式增加 `CATEGORICAL_VECTOR`：

升级 schema/SDK version，并保持兼容。

------------------------------------------------------------------------

# 7. Day 9.1 --- Runtime Closure

结论：**runtime provenance 真实存在，但 UI 中文化不足。**

源码确认：

-   total wall time；
-   simulator evaluation time；
-   optimizer overhead；
-   CPU/GPU/Python/Sionna/Torch/CUDA provenance。

但页面仍存在大量：

-   `Total wall time`
-   `Runtime environment provenance`
-   `Feasible`
-   `Stop reason`
-   `Verification`
-   `Best candidate KPI`

等英文用户文字。

Day 11 必须整体中文优先。

技术 ID/协议 ID 可保留英文。

------------------------------------------------------------------------

# 8. Day 10 --- Algorithm Onboarding

结论：

**Package/Validation/Smoke/Registry 主链 PASS。**

但源码审计发现 4 个必须修复的问题。

## P0-10A --- 实验完成后自动生成 Benchmark

当前：

`_export_experiment()`

直接调用：

`_export_day10_benchmark()`

把 external run 和 Day 9 baseline 自动拼在一起。

这是错误的产品逻辑。

**Run 完成 ≠ 用户要求比较。**

Day 11 必须删除自动 Benchmark/Comparison 创建。

历史 `BENCH-DAY10-EXT-3C12U001` 不重写。

------------------------------------------------------------------------

# 9. P0-10B --- Day 10 提前写 independently_verified

当前 export 在真正独立 verifier 执行前直接生成：

``` text
verification.status = PASS
verified = true
verification_status = independently_verified
```

这是证据语义错误。

与 Day 9 一并修复。

Evidence 生成默认：

``` text
verified = false
verification_status = unverified/pending
```

Verifier PASS 后再 transition。

------------------------------------------------------------------------

# 10. P0-10C --- External Experiment 写死 USER_ASSOCIATION

当前 AlgorithmPackageService 直接 import/构造：

``` text
UserAssociationService
MultiCellBackend
BenchmarkService._load_day8_frozen_channel
AssociationOptimizationService
```

所以当前能力准确表述应是：

**External Algorithm Package → USER_ASSOCIATION problem execution
已跑通。**

还不是：

**External Algorithm → arbitrary platform problem**

Day 11 建立：

`ProblemEvaluationAdapter`

和：

`ProblemEvaluationRegistry`

AlgorithmPackageService 以后只依赖 registry。

V0.1 只迁移 USER_ASSOCIATION。

------------------------------------------------------------------------

# 11. P0-10D --- evaluation_budget 全局硬限制 12

当前：

``` python
if not 1 <= evaluation_budget <= 12:
    raise ...
```

这是 demo 限制泄漏到平台能力。

删除业务代码中的固定 12。

Budget 来源应为：

-   Experiment configuration；
-   Benchmark protocol；
-   optional resource policy。

默认：

`>= 1`

如果需要 safety maximum：

必须是可配置 policy，不是算法业务常量。

------------------------------------------------------------------------

# 12. 历史 Day 2 Timeout 债务升级为 P0

当前传播 ExperimentService：

``` text
DEFAULT_TIMEOUT_SECONDS = 600
future.result(timeout=600)
timeout → experiment FAILED / SIMULATION_TIMEOUT
worker thread continues running
```

这正是平台现在不能继续保留的语义。

问题：

一个合法长实验运行超过 600 秒：

平台会：

1.  标记 FAILED；
2.  实际 worker 继续占资源；
3.  用户可能重新启动；
4.  老 worker 仍然运行；
5.  可能造成 CPU/GPU 资源竞争。

Day 11 必须修复。

------------------------------------------------------------------------

# 13. Timeout 新原则

**wall-clock 时间长不是失败证据。**

默认：

``` text
time_limit = null
```

只有用户或 Protocol 明确设置 time limit：

才允许触发时间限制。

HTTP/request timeout：

不得改变后台 Run 的科学状态。

------------------------------------------------------------------------

# 14. Execution Manager

Day 11 正式引入：

``` text
API
 ↓
Run Service
 ↓
Execution Manager
 ↓
Worker Process
 ↓
Problem Evaluation / Algorithm
```

优先用于：

-   External Algorithm Run；
-   新创建的 managed run。

同时为传播/system/system-optimization 迁移提供 adapter。

不要一次性重写所有历史服务。

------------------------------------------------------------------------

# 15. Worker Process Boundary

外部算法不得继续只依赖 daemon thread。

每个 managed Run：

``` text
run_id
worker_id
pid
process_group_id
status
started_at
heartbeat_at
device
cancel_requested
```

停止只能针对所属 worker/process group。

禁止：

`kill all python`

------------------------------------------------------------------------

# 16. Run State Machine

至少：

``` text
QUEUED
STARTING
RUNNING
CANCEL_REQUESTED
CANCELLING
CANCELLED
COMPLETED
FAILED
TIME_LIMIT_EXCEEDED
TERMINATED
STALE
```

终态不可随意覆盖。

------------------------------------------------------------------------

# 17. Graceful Cancel

用户点击：

`停止运行`

流程：

1.  persist cancel request；
2.  worker 在安全点检查；
3.  不再产生新 suggestion/evaluation；
4.  finalize partial trace；
5.  保存 logs/artifacts/evidence；
6.  `CANCELLED`。

------------------------------------------------------------------------

# 18. Force Terminate

Graceful cancel 不响应时：

提供：

`强制终止`

必须二次确认。

真实动作：

-   terminate process group；
-   grace period；
-   escalate if needed；
-   child cleanup；
-   preserve logs；
-   status=`TERMINATED`。

如果只是改 DB 状态而进程仍活：

测试必须 FAIL。

------------------------------------------------------------------------

# 19. GPU Process Cleanup

如果 worker/algorithm 使用 GPU：

停止后不得留下属于该 run 的孤儿 child process。

记录：

``` text
declared_device
observed_device
worker_pid
child_pids
```

当前 CUDA 不可用时：

GPU cleanup 标：

`NOT VERIFIED IN CURRENT ENVIRONMENT`

不能伪造 PASS。

------------------------------------------------------------------------

# 20. Heartbeat

Heartbeat 只判断 worker health。

不能把：

-   objective 长时间不改善；
-   evaluation 很慢；
-   GPU kernel 长；

当作 hung。

worker process 消失 / IPC broken / heartbeat stale：

才进入异常恢复逻辑。

------------------------------------------------------------------------

# 21. Explicit Time Limit

`time_limit_seconds = null | positive number`

null：

无平台 wall-clock limit。

明确设置后：

达到 limit → graceful cancel → grace → force terminate →
`TIME_LIMIT_EXCEEDED`。

不是"结束后补标签"。

------------------------------------------------------------------------

# 22. Legacy Experiment Timeout Migration

Day 11 必须处理 Day 2 `GLOSVP_EXPERIMENT_TIMEOUT=600`。

最低要求：

-   默认不再把 600 秒解释成 simulation failure；
-   legacy synchronous API 若必须保留 request wait limit：
    -   request wait timeout 与 run state 分离；
    -   后台 run 继续显示 RUNNING；
    -   不写 `SIMULATION_TIMEOUT`；
-   新 managed API 返回 run_id。

README 同步修正。

------------------------------------------------------------------------

# 23. System Experiment / Optimization 执行策略

Day 5/6 当前：

-   system experiment 同步 + lock；
-   system optimization daemon thread。

Day 11 不要求完全迁移全部实现。

但必须写清：

``` text
Managed Execution Supported:
External Algorithm Runs = YES

Legacy Propagation/System/System Optimization:
legacy adapter / migration pending
```

如果工程成本允许：

可接入统一 Execution Manager。

禁止为了"一次性统一"破坏 Day 4--10 regression。

------------------------------------------------------------------------

# 24. User-Directed Comparison --- 核心产品修复

新 canonical object：

`Comparison`

Comparison 是用户主动创建的分析对象。

不是 Run 自动副产品。

------------------------------------------------------------------------

# 25. 正确流程

``` text
实验列表
 ↓
用户勾选 2..N Runs
 ↓
点击“对比分析”
 ↓
选择对比目的
 ↓
平台生成差异报告
 ↓
用户确认
 ↓
创建 Comparison
```

------------------------------------------------------------------------

# 26. Comparison Intent

至少：

``` text
ALGORITHM_COMPARISON
HYPERPARAMETER_COMPARISON
CONFIGURATION_COMPARISON
RUN_REPRODUCIBILITY
SCENARIO_ANALYSIS
CUSTOM_ANALYSIS
```

------------------------------------------------------------------------

# 27. Frozen vs Varying Dimensions

平台不能简单规定：

`参数不同 = 不能比较`

因为用户可能就是要比较参数。

必须区分：

``` text
intended varying dimensions
```

和：

``` text
required frozen dimensions
```

------------------------------------------------------------------------

# 28. ALGORITHM_COMPARISON 默认规则

默认允许变化：

-   algorithm identity；
-   用户明确选择的 algorithm hyperparameters。

默认冻结：

-   problem；
-   dataset；
-   scenario；
-   channel realization/artifact；
-   traffic；
-   objective；
-   constraints；
-   KPI versions；
-   evaluation protocol；
-   evaluation budget；
-   backend/version。

------------------------------------------------------------------------

# 29. Compatibility Preview

创建 Comparison 前返回：

``` text
Comparable
Comparable With Declared Differences
Not Directly Comparable
```

逐项展示：

``` text
问题
数据集
场景
信道
业务
目标函数
约束
KPI
评估预算
算法
算法参数
Backend
```

------------------------------------------------------------------------

# 30. 不可直接比较 ≠ 不能查看

用户仍可：

`并排查看`

但平台不得生成：

-   gain；
-   winner；
-   ranking；
-   直接 convergence overlay；
-   "A 优于 B"。

------------------------------------------------------------------------

# 31. Benchmark 与 Comparison 分离

Benchmark：

`预先定义 Protocol → 计划运行一组算法`

Comparison：

`用户选择已有 Runs → 分析`

关系：

``` text
Benchmark → may create Comparison
Existing Runs → may create Comparison
```

------------------------------------------------------------------------

# 32. Benchmark 首页重构

不再默认显示"所有算法整体对比"。

建议中文导航：

``` text
基准任务
对比分析
实验运行
算法目录
```

------------------------------------------------------------------------

# 33. Comparison Wizard

``` text
1 选择实验
2 选择对比目的
3 查看条件差异
4 确认比较维度
5 创建对比
```

------------------------------------------------------------------------

# 34. 中文优先 UI

Day 11 强制修复 Benchmark/Comparison/Runtime 页面。

必须中文：

-   页面标题；
-   Tabs；
-   按钮；
-   表头；
-   状态；
-   Tooltip；
-   Empty/Error state；
-   runtime 解释；
-   verification 解释。

允许英文：

-   Algorithm ID；
-   Protocol ID；
-   KPI ID；
-   SDK；
-   技术名词必要括注。

例如：

`总运行时间（Total wall time）`

而不是纯英文。

------------------------------------------------------------------------

# 35. 参数差异面板

Comparison 必须展示：

``` text
算法
算法版本
Package Hash
算法超参数
优化变量
预算
Seed
```

不能隐藏。

------------------------------------------------------------------------

# 36. Dataset / Scenario / Channel

关键 identity 不一致时：

必须显著提示。

用户不能通过 UI checkbox 强行把 scientifically incompatible runs 变成
`Comparable=YES`。

可以切换成：

`并排查看模式`

------------------------------------------------------------------------

# 37. No Auto Ranking

禁止：

-   Overall Score；
-   Champion；
-   Best Algorithm；
-   自动算法排行榜。

表格允许用户自己排序：

这只是 UI 工具，不是平台结论。

------------------------------------------------------------------------

# 38. Reference Role

为 run/algorithm 增加：

``` text
comparison_role:
reference
optimizer
```

Day 8 Association Baseline：

默认 `reference`。

避免把"零搜索 baseline"与 optimizer 做误导性的优化速度竞争。

------------------------------------------------------------------------

# 39. ProblemEvaluationAdapter

接口至少：

``` text
problem_type
load_problem_context()
parameter_space()
baseline()
evaluate(candidate)
objective_metadata()
constraint_metadata()
kpi_metadata()
provenance()
```

Registry：

``` text
USER_ASSOCIATION → UserAssociationEvaluationAdapter
```

未来：

``` text
SYSTEM_PARAMETER
NETWORK_STRUCTURE
RESOURCE_ALLOCATION
```

只新增 adapter。

------------------------------------------------------------------------

# 40. Scenario Loading Integrity

修复 UserAssociationService：

不存在 scenario：

`raise ScenarioNotFound`

禁止 fallback。

所有其他 catalog/service 做一次审计：

-   不存在 ID；
-   错误 ID；
-   case mismatch；
-   malformed config。

不得静默换场景。

------------------------------------------------------------------------

# 41. ChannelProvenanceHash V0.2

新运行使用 V0.2。

历史 V0.1 不改。

V0.2 canonical payload 至少：

``` text
scenario id/version
scene
frequency
bandwidth
BS/Cell IDs + positions
UE IDs + positions
propagation-relevant antenna/config
seed
link artifact digest
```

provider version 可记录在 provenance；是否进入 hash 要版本化说明。

------------------------------------------------------------------------

# 42. Same Seed 文档修复

全仓库搜索：

`same seed` `同种子` `reproducible` `可复现`

区分：

-   deterministic platform RNG；
-   deterministic SYS under frozen channel；
-   Sionna RT realization。

禁止继续写：

`same seed ⇒ same channel realization`

Benchmark fairness：

`same frozen artifact ID + artifact hash`

------------------------------------------------------------------------

# 43. Evidence State Machine

统一：

``` text
UNVERIFIED
PENDING
VERIFIED
FAILED
```

EvidenceDescriptor：

``` text
execution_status
verification_status
comparison_eligible
acceptance_eligible
```

四者独立。

------------------------------------------------------------------------

# 44. Verifier Transition

Verifier PASS 后才写 verified。

记录：

``` text
verifier_id
verifier_version
verified_at
verification_hash
```

Verifier FAIL：

``` text
verified=false
verification_status=failed
```

不能删除原 run。

------------------------------------------------------------------------

# 45. Historical Evidence

Day 4--10 reference：

不重写数值/结果。

对于历史存在提前 verified 的 evidence：

记录：

`legacy_verification_semantics=true`

或 migration note。

不要伪造历史 state transition。

------------------------------------------------------------------------

# 46. Independent Verifier Strengthening

Day 11 Comparison verifier 不 import production eligibility evaluator。

独立检查：

-   selected runs；
-   intent；
-   frozen/varying dimensions；
-   problem；
-   dataset；
-   scenario；
-   channel；
-   traffic；
-   objective；
-   constraints；
-   KPI versions；
-   budget；
-   backend；
-   package hash；
-   parameter differences；
-   eligibility。

------------------------------------------------------------------------

# 47. Day 10 Verifier 修复

至少独立重算/检查：

-   manifest hash；
-   source/package hash where available；
-   run/package identity；
-   trace evaluation count；
-   persisted KPI consistency；
-   channel identity；
-   evidence verification transition。

不能只检查自己写出的 `PASS` 文件。

------------------------------------------------------------------------

# 48. Tamper Tests

至少：

-   scenario ID tamper；
-   silent fallback regression；
-   UE coordinate tamper；
-   Cell coordinate tamper；
-   channel hash tamper；
-   dataset identity tamper；
-   objective tamper；
-   constraint tamper；
-   KPI version tamper；
-   budget tamper；
-   hidden hyperparameter difference；
-   fake verified status；
-   selected run substitution；
-   comparison eligibility tamper。

------------------------------------------------------------------------

# 49. Execution Tests

至少：

-   normal completion；
-   queued cancel；
-   running graceful cancel；
-   unresponsive force terminate；
-   worker crash；
-   stale heartbeat；
-   child cleanup；
-   explicit time limit；
-   no default time limit；
-   HTTP wait timeout does not mark scientific run failed；
-   repeated cancel idempotent；
-   repeated terminate idempotent；
-   two independent workers；
-   resource unavailable；
-   restart recovery。

------------------------------------------------------------------------

# 50. Legacy Timeout Regression

必须有测试证明：

合法长任务超过旧 600 秒语义阈值时：

**不会仅因为默认 wall clock 被标 FAILED。**

测试不需要真的 sleep 600 秒。

使用 injectable clock/fake worker。

------------------------------------------------------------------------

# 51. Comparison Positive Reference

创建 Day 11 reference：

用户显式选择两个满足同 frozen context 的 optimizer runs。

Intent：

`ALGORITHM_COMPARISON`

结果：

`Comparable = YES`

------------------------------------------------------------------------

# 52. Comparison Negative Reference

再创建一个：

关键 context 不同，例如：

-   channel artifact；
-   scenario；
-   dataset；
-   protocol。

结果：

`Not Directly Comparable`

UI 只允许：

`并排查看`

证明平台不会硬凑。

------------------------------------------------------------------------

# 53. Browser E2E

至少：

``` text
实验运行
→ 启动 external algorithm
→ RUNNING
→ 停止
→ CANCELLED

再启动 unresponsive test worker
→ 强制终止
→ TERMINATED

对比分析
→ 选择 Runs
→ 选择“算法对比”
→ 条件差异
→ Comparable
→ 创建 Comparison
→ KPI/运行时间/收敛/参数差异/证据

选择不兼容 Runs
→ Not Directly Comparable
→ 并排查看
```

Console Errors = 0。

------------------------------------------------------------------------

# 54. UI Language E2E

浏览器逐页检查：

``` text
Benchmark Center
Comparison
Convergence
Runs
Evidence
Runtime
Algorithm Detail
```

主要用户文案必须中文优先。

输出：

`DAY11_UI_LANGUAGE_AUDIT.md`

列出剩余英文及理由。

------------------------------------------------------------------------

# 55. Regression

完整运行 Day 4--10 regression。

特别冻结：

-   Day 4 objective semantics；
-   Day 5 KPI；
-   Day 6 fair context；
-   Day 7 SDK；
-   Day 8 reference；
-   Day 9 frozen benchmark；
-   Day 10 package hash/reference experiment。

不得为了 Day 11 获得 PASS 修改历史 reference 数值。

------------------------------------------------------------------------

# 56. Stop Conditions

任一出现立即停止：

1.  scenario 不存在仍静默 fallback；
2.  默认 wall-clock timeout 仍能把正常长 run 标 FAILED；
3.  Force Terminate 只改状态、不杀 worker；
4.  kill 一个 run 会影响其他 run；
5.  HTTP timeout 会改变后台 scientific run 状态；
6.  verifier 未运行就写 independently_verified；
7.  experiment 完成自动创建 Comparison；
8.  所有历史 run 被自动塞入一个整体排行榜；
9.  incompatible context 被标 Comparable；
10. 为了比较重新调用 Sionna RT；
11. same seed 被当作 same channel proof；
12. external execution 仍必须在 AlgorithmPackageService 硬编码
    UserAssociation；
13. evaluation budget 仍全局固定 \<=12；
14. Benchmark/Comparison 页面仍以英文为主；
15. Day 4--10 reference 被重写。

------------------------------------------------------------------------

# 57. Definition of Done

-   [ ] Day 4--10 audit findings documented
-   [ ] UserAssociation scenario fallback removed
-   [ ] scenario-not-found tests
-   [ ] ChannelProvenanceHash V0.2
-   [ ] historical channel V0.1 preserved
-   [ ] same-seed docs corrected
-   [ ] Day9 premature verification fixed
-   [ ] Day10 premature verification fixed
-   [ ] Evidence state machine
-   [ ] verifier transition real
-   [ ] legacy evidence migration note
-   [ ] automatic Day10 benchmark creation removed
-   [ ] Comparison canonical object
-   [ ] user-selected runs
-   [ ] comparison intent
-   [ ] frozen/varying dimensions
-   [ ] preview compatibility report
-   [ ] non-comparable side-by-side mode
-   [ ] no auto winner/ranking
-   [ ] reference vs optimizer role
-   [ ] ProblemEvaluationAdapter
-   [ ] USER_ASSOCIATION migrated
-   [ ] AlgorithmPackageService decoupled
-   [ ] hard-coded budget \<=12 removed
-   [ ] configurable budget policy
-   [ ] legacy 600s failure semantics removed
-   [ ] default time_limit=null
-   [ ] Execution Manager
-   [ ] worker process ownership
-   [ ] heartbeat
-   [ ] graceful cancel
-   [ ] force terminate
-   [ ] child cleanup
-   [ ] optional real time limit
-   [ ] HTTP lifecycle separated
-   [ ] crash/stale recovery
-   [ ] concurrency/queue
-   [ ] GPU cleanup limitation honest
-   [ ] Chinese-first Benchmark UI
-   [ ] Chinese-first Comparison UI
-   [ ] UI language audit
-   [ ] positive comparison reference
-   [ ] negative comparison reference
-   [ ] independent verifier
-   [ ] tamper tests
-   [ ] backend tests
-   [ ] frontend tests
-   [ ] typecheck
-   [ ] build
-   [ ] browser E2E
-   [ ] console errors 0
-   [ ] Day4--10 regression
-   [ ] commit
-   [ ] push

------------------------------------------------------------------------

# 58. Final Report --- 必须逐项回答

1.  Base commit
2.  Day 11 commit
3.  HEAD
4.  origin/main
5.  working tree
6.  Day4 audit status
7.  Day5 audit status
8.  Day6 audit status
9.  Day7 audit status
10. Day8 audit status
11. Day9 audit status
12. Day9.1 audit status
13. Day10 audit status
14. scenario silent fallback removed YES/NO
15. scenario-not-found behavior
16. ChannelProvenanceHash version
17. geometry fields included
18. historical Day8 hash modified YES/NO
19. same-seed docs corrected
20. Evidence verification state model
21. pre-verifier verified eliminated YES/NO
22. legacy evidence handling
23. automatic benchmark creation removed YES/NO
24. Comparison model/version
25. comparison intents
26. positive comparison ID
27. negative comparison ID
28. frozen dimensions
29. varying dimensions
30. non-comparable behavior
31. reference/optimizer role
32. auto ranking absent YES/NO
33. ProblemEvaluationAdapter
34. migrated problem types
35. AlgorithmPackageService direct UserAssociation dependency removed
    YES/NO
36. budget policy
37. hard-coded \<=12 removed YES/NO
38. old GLOSVP_EXPERIMENT_TIMEOUT behavior
39. legacy 600s scientific-failure semantics removed YES/NO
40. default time limit
41. Execution Manager
42. worker model
43. process ownership
44. heartbeat
45. graceful cancel
46. force terminate
47. child cleanup
48. GPU cleanup status/limitation
49. explicit time limit
50. HTTP lifecycle separation
51. worker crash recovery
52. stale recovery
53. concurrency test
54. resource admission
55. Chinese-first UI status
56. UI language audit path
57. remaining English text
58. Day10 verifier strengthening
59. Comparison independent verifier
60. tamper tests
61. backend tests
62. frontend tests
63. TypeScript
64. build
65. browser E2E
66. console errors
67. Day4 regression
68. Day5 regression
69. Day6 regression
70. Day7 regression
71. Day8 regression
72. Day9 regression
73. Day10 regression
74. evidence paths
75. known limitations
76. technical debt
77. Day11 Final
78. Day11 Frozen
79. Day12 Ready

------------------------------------------------------------------------

# 59. Day 11 最终成功标准

Day 11 结束后，平台必须清楚分成三层：

``` text
算法接入
Package → Validate → Register
```

``` text
实验执行
Run → Managed Worker → Evaluation → KPI/Evidence
```

``` text
用户分析
Select Runs → Comparison Intent → Compatibility Preview
→ User Confirm → Comparison
```

并满足：

**平台负责保证运行和证据正确。**

**平台负责告诉用户这些实验是否具备直接比较条件。**

**用户负责决定自己想比较什么。**

**运行时间长本身不是失败。**

**相同 seed 本身不是相同信道 realization 的证明。**

**Verifier 没有真正执行之前，平台绝不能提前宣布 independently
verified。**

# END OF DAY 11
