# Day 10 --- Algorithm Onboarding & Experiment Workspace

## 算法接入与实验工作台

> Frozen baseline: Day 9 `PASS WITH DOCUMENTED LIMITATIONS / FROZEN`,
> closure commit `866b2e2`, benchmark `BENCH-DAY9-3C12U001`.
>
> **目标：把算法接入从"修改平台源码"升级为平台正式用户工作流。**
>
> 第三方、研究人员自有、论文复现或 AI 辅助实现的算法，只要遵循 Algorithm
> Package / SDK 契约，就能：
>
> `Package → Validate → Smoke Test → Register → Configure → Run → Observe → Compare → Export`
>
> Day 10 不以算法性能、算法先进性或 KPI 提升为成功标准。

## 1. 工程边界

平台负责 Package 契约、接口/参数校验、Problem
compatibility、注册版本、实验配置、SDK 调用、平台
Evaluation、日志/trace、KPI、Benchmark、Evidence/Provenance、导出和易用性。

平台不负责选择研究路线、证明论文复现正确、证明 AI
生成算法科学正确、提高算法质量/效率或为了漂亮结果修改算法。

## 2. 用户故事

A. 研究人员：按模板包装 Python optimizer → Validate → Smoke → Register →
选择 Problem/Scenario → 参数配置 → Run → KPI/trace → Benchmark →
Export。

B. 论文/AI 实现：平台只验证 package 格式、SDK
接口、schema、compatibility、suggestion 和 lifecycle
可运行；`Validation PASS` 绝不等于 `Paper Reproduced`。

C.
运营商/验证人员：无需看源码即可选择算法/场景、配置公开参数、运行、看日志/KPI/证据、比较和导出。

## 3. Algorithm-Agnostic

平台业务逻辑不得散落具体算法名判断。通过
`Algorithm Registry + SDK + Adapter` 驱动。

算法只负责 `Observation → Candidate Suggestion`；平台负责
`Candidate → Validation → Simulation/Evaluation → KPI → Objective/Constraints → Observation`。

第三方算法不得直接调用 Sionna、修改 Scenario/Dataset、写 Experiment
DB、覆盖平台 KPI/Objective、决定 verification/acceptance。

## 4. Algorithm Package V0.1

最小结构：

``` text
my_algorithm/
├── algorithm.yaml
├── optimizer.py
├── README.md
└── requirements.txt   # optional
```

Manifest 至少声明：schema version、algorithm
id/name/version/description/provider/category/learning flag、SDK
version、entrypoint、problem/parameter compatibility、参数
schema、CPU/GPU 声明、execution capability。

示例：

``` yaml
schema_version: "0.1"
algorithm:
  id: my_algorithm
  name: My Algorithm
  version: "0.1.0"
  provider: user
  category: external
  learning_algorithm: false
sdk:
  version: "0.1"
entrypoint:
  module: optimizer
  class: MyOptimizer
compatibility:
  problem_types: [user_association]
  parameter_types: [categorical_vector]
parameters:
  budget: {type: integer, default: 10, minimum: 1}
  seed: {type: integer, default: 42}
resources:
  cpu: true
  gpu: optional
execution:
  supports_cancel: false
```

字段以当前 canonical SDK 为准，不为名称统一重写已有稳定接口。

## 5. Validation

Manifest
Validation：schema/version、ID/version、entrypoint、SDK、category、parameters、compatibility、duplicate
ID/version、unknown/invalid fields。错误必须给可理解的
code/stage/message，不只抛 traceback。

Import
Validation：module/class/import/interface/constructor；缺依赖返回明确
`IMPORT_ERROR`，不自动 pip install。

SDK 不兼容在运行前标记 `INCOMPATIBLE_SDK`。

## 6. SDK 与受控 Context

复用现有 SDK；等价生命周期可保持现状。建议语义：initialize → suggest →
observe → should_stop → finalize。

算法 context 只暴露 problem metadata、parameter
space、objective/constraints
metadata、budget、seed、baseline、observations；不暴露 DB
session、backend/Sionna object、内部文件路径、acceptance control。

统一 Observation 至少包含
candidate_id、parameters、objective、feasible、constraint_results、kpi_summary、evaluation_status。

Suggestion 必须经过 schema/type/range/dimension/allowed-values/duplicate
validation 后才进入 simulator。Validation rejection 默认不消耗 expensive
evaluation budget，但记录
rejected_suggestions；如历史协议不同则保持兼容并明确记录。

## 7. Package Source 与安全边界

V0.1 正式支持 Local Package Directory / 平台指定 workspace
即可；不要同时实现 Git/PyPI/Docker/Notebook/remote URL。

**V0.1 是 trusted-code integration，不是 sandboxed untrusted-code
execution。** UI/README 明确只运行可信来源 Python。 hostile-code
sandbox、container/OS isolation、resource quota 留待后续。

`requirements.txt` 只记录/展示；禁止静默 `pip install`
到平台主环境。依赖安装由受控环境人工管理。

## 8. Package Identity

注册记录 manifest_hash、source_hash、package_hash，hash 方法版本化。相同
`algorithm_id + version` 但 source hash
不同必须拒绝或显著警告，禁止静默覆盖。

Run/Evidence 绑定
`algorithm_id + version + package_hash + sdk_version`。

Manifest 可选
implementation_origin：`paper_reimplementation / ai_assisted / original / imported`，仅作为
provenance，不作为 Warning。paper_reference 不等于 verified
reproduction。

## 9. Validation Pipeline

``` text
DISCOVERED
→ MANIFEST_VALIDATED
→ IMPORT_VALIDATED
→ INTERFACE_VALIDATED
→ SMOKE_TESTED
→ REGISTERED
```

失败必须保存 stage/reason。

Smoke Test 只验证 lifecycle、candidate validation、observe/next
suggestion/stop/finalize，默认 Fake/lightweight evaluator，不跑重型
Sionna，不验证算法性能。

错误至少分类：MANIFEST_ERROR、SDK_INCOMPATIBLE、IMPORT_ERROR、INTERFACE_ERROR、SMOKE_TEST_FAILED、PARAMETER_ERROR、PROBLEM_INCOMPATIBLE、RUNTIME_ERROR。普通
UI 显示简洁错误，technical details 再展开 traceback。

## 10. Registry

统一支持 built_in / external。状态至少
DRAFT、VALIDATED、REGISTERED、DISABLED、INCOMPATIBLE、FAILED。

Disable 后历史 run/evidence
仍可解析，新实验不可选择。已有实验引用的算法版本不物理删除，优先
archive/soft-delete。

## 11. Algorithm Center

保留 Runnable Algorithms / Research Catalog；Runnable 增 Built-in /
External filter。

Algorithm Detail 显示 Name/Version/Provider/Category/Package
Hash/SDK/Compatibility/Parameter Schema/CPU-GPU
Requirement/Validation/Smoke Test/README/Usage History。

新增 Import Algorithm 流程：
`Package → Validate → Smoke Test → Review → Register`，全部显示真实状态。

Research Catalog 可以关联 `implementation_algorithm_id`，但必须区分 User
Implementation 与 Official Implementation。

## 12. Experiment Workspace

目标是不懂源码也能：
`Problem → Scenario → Compatible Algorithms → Algorithm Parameters → Evaluation Protocol → Review → Run`。

Problem-first，避免先选不兼容算法。参数表单由 schema 动态生成，不
hard-code alpha/beta/budget/seed。支持
integer/float/select/boolean/vector
基础编辑、default、description、unit、validation；支持 basic/advanced
参数分层。

继续严格区分 Algorithm Hyperparameter 与 Optimization Variable。

Run 前 Review 展示 Problem、Scenario、Algorithm+Version、Package
Hash、Parameters、Objective、Constraints、Budget、Data Source、Backend。

## 13. Running / Logs / Trace

Running 至少显示 Status、Elapsed Time、Evaluations Used、Budget、Current
Best Feasible Objective、Last Evaluation、Logs。

禁止虚假 `73% Complete`；只有总量明确时显示 `7/20 evaluations`，否则显示
Running + elapsed + evaluations。

持久化日志，尽量区分 platform/algorithm/evaluation
source；支持基本查看、auto-scroll/pause/download（按工程可行性）。

Trace 展示 suggest → candidate → validation → evaluation → observation →
next suggestion → stop。

KPI drill-down 复用现有系统，不重做。

## 14. Benchmark Integration

Registered + compatible + smoke-pass 的 external algorithm 可进入 Day 9
Benchmark。built-in/external 使用相同公平协议。

BenchmarkRun 必须记录
package_hash、algorithm_version、sdk_version、provider。

创建新的 Day 10 reference benchmark，证明 external algorithm
可参与公平比较；**不得修改 frozen `BENCH-DAY9-3C12U001`**。算法是否胜过
baseline 不是验收条件。

## 15. Export / Rerun

提供基础 `Export Experiment Bundle`：metadata、algorithm
identity、parameters、scenario、protocol、KPI、trace、logs、provenance、EvidenceDescriptor。默认不打包第三方源码，只记录
id/version/package hash。

Run Again 复制配置并创建新 Run ID，不覆盖历史。Clone Configuration
可修改算法、hyperparameters、scenario、budget 后创建新实验。

## 16. Timeout Audit --- Day 10 必做

审计代码中所有 timeout/time_limit/wait_for/asyncio/subprocess/request
timeout，生成 `DAY10_TIMEOUT_AUDIT.md`。

每个 timeout
分类：HTTP/UI、Simulation、Algorithm、Worker/Process、Test-only、External
Library；记录 source、current behavior、risk、Day10 action、Day11
action。

**核心原则：长时间运行 ≠ 假死。**

不得因数据量大、场景大、算法复杂、GPU kernel 长、simulator 慢而使用固定
wall-clock 默认判失败。

如果发现
`algorithm runtime > N → failed`，必须审查并移除/改造危险默认行为。

## 17. time_limit 语义

设计为 optional execution policy： `time_limit_seconds: null | number`。

`null` = 无平台算法时间上限。只有用户或 Benchmark Protocol
明确设置才生效。

HTTP request timeout 与 Algorithm Run 生命周期严格分离：API 可返回
run_id 后 poll/stream；HTTP 超时不能自动意味着后台 run 被终止。

## 18. Cancellation 边界

Day 10 **不要求**完整 process kill / GPU cleanup，但 model/API
不得封死未来取消能力，可预留 cancel_requested/等价状态。

如果 Force Terminate 未真实实现，UI 不得出现假按钮，必须明确
`NOT YET AVAILABLE`。

Day 10 结束生成
`DAY11_EXECUTION_MANAGEMENT_REQUIREMENTS.md`，至少记录：independent
worker/process、process ownership、heartbeat、graceful cancel、force
terminate、process group、child cleanup、GPU process cleanup、crash
recovery、log streaming、resource metadata、optional time limit。

GPU requirement 在 V0.1 只用于 compatibility/UI/provenance，不实现 GPU
scheduler。

## 19. Quickstart 与 AI 接入辅助

新增中文优先 `docs/algorithm-sdk/QUICKSTART.md`：最小
package、接口、validate、smoke、register、run、benchmark、常见错误。

新增 `ExampleExternalOptimizer`，逻辑故意简单，必须完整走 external
package path，不可偷偷注册 built-in。

推荐提供 `AI_IMPLEMENTATION_TEMPLATE.md`：告诉 AI 不调用
simulator、不计算平台 KPI、只 suggest、遵循
schema、不修改平台源码。它只是开发辅助文档，不是自动执行任意 AI
代码功能。

## 20. API

按当前风格实现/等价实现： - POST algorithm-packages validate - POST
package smoke-test - POST package register - GET packages / detail -
POST algorithm disable - Experiment create 接受 registry algorithm
id/version/parameters，而非 Python class - 结构化 error
`{code, stage, message, details}`

Package source 可在文件系统；Registry 保存
path/hash/metadata/status，不把大量源码复制进 DB。

## 21. Provenance / Evidence

新增/扩展
AlgorithmPackageProvenance：package_id、algorithm_id、version、provider、manifest/source/package
hash、sdk_version、implementation_origin、registered_at、validation/smoke
result。

External experiment evidence 必须追溯到 package provenance。

Independent verifier 至少验证 algorithm id/version/package hash/manifest
hash/parameters/compatibility/scenario/protocol/trace/KPI/EvidenceDescriptor。

Verifier 只验证 Platform execution evidence integrity，禁止输出
`Algorithm Correct` 或 `Paper Reproduced`。

## 22. Reference Run

使用 ExampleExternalOptimizer 接入现有稳定 Problem（优先
`MULTICELL-DEMO-001 / USER_ASSOCIATION`，不要新建复杂 5G 模型）。

成功条件：package validated、smoke passed、registered、experiment
completed、KPI/trace/evidence produced、benchmark compatible。完全不要求
throughput/P5 improvement。

## 23. Provenance UI

延续 Day 9 降噪：普通页面 `仿真 / ✓ 已验证`；Algorithm Detail 展示
Provider/Package Version/Hash/SDK/Validation/Smoke。不要恢复 Not Huawei
式 Warning。

Acceptance Center 可新增 External Algorithm Integration / Algorithm
Experiment Execution / Algorithm Comparative Validation，状态只写
Simulation Capability Available，不写 Acceptance PASS。

## 24. Tests

Manifest：valid、missing field、invalid version、duplicate、invalid
parameter schema、unsupported SDK。

Package：valid import、missing module/class、wrong interface、missing
dependency、stable hash、same-version changed-source rejection。

Smoke：lifecycle pass、invalid candidate、observe/finalize
failure、does-not-use-real-Sionna。

Registry：register validated、reject unvalidated、disable、disabled not
selectable、historical resolve、external visible。

Workspace：compatibility filter、dynamic form、parameter validation、run
identity contains package hash、rerun new ID、clone config。

Benchmark：external enters benchmark、same
protocol/channel/budget、package hash evidence、comparison eligible。

Timeout policy regression：long-running algorithm not failed solely by
default wall clock；HTTP timeout does not mark run failed；optional time
limit explicit。若暂不能构造长任务，至少测试 policy semantics。

Frontend：Import、validation、smoke、register、detail、dynamic
params、filter、review、running、logs、result、benchmark link、error
states、provenance。

## 25. Browser E2E

真实浏览器完成：
`Home → Algorithm Center → Import ExampleExternalOptimizer → Validate → Smoke → Register → Detail → Create Experiment → Problem → Scenario → Parameters → Review → Run → Running/Logs → Result → Evidence → Day10 Benchmark → external algorithm visible → Comparison`

Console Errors = 0。

## 26. Evidence

创建 `reference/algorithm_onboarding/<REFERENCE-ID>/`，合理保存
README、manifest、validation、smoke、registration、experiment、trace、KPI、verification、provenance、EvidenceDescriptor、screenshots。

Timeout audit 也放入 reference evidence。不要为了数量重复相同信息。

## 27. Claims

允许： "ExampleExternalOptimizer 已通过平台 Package Validation、Smoke
Test，并成功接入现有仿真 Problem 完成实验和 Benchmark。"

禁止： "ExampleExternalOptimizer 是先进/有效的 5G 优化算法。" "AI
可以自动正确复现任意论文算法。"

## 28. Security Limitation

明确 V0.1 是 trusted external Python code，尚未实现 hostile-code
sandbox、container/OS isolation、resource quota
enforcement。这是已知边界，不是伪装成已解决。

## 29. Stop Conditions

立即停止并报告，如果： 1. External Algorithm
必须修改平台核心代码才能注册； 2. 第三方算法可绕过平台 Evaluation； 3.
Validation PASS 被解释成科学正确； 4. Smoke 必须跑真实重型 Sionna； 5.
同 ID/version 静默覆盖不同 source； 6. 自动 pip install 污染主环境； 7.
默认固定 timeout 把长算法判失败； 8. HTTP timeout 直接终止后台
experiment； 9. UI 有 Force Kill 但后台未真实实现； 10. 修改 Day 9
frozen benchmark； 11. Day 4--9 regression 出现无法解释失败。

## 30. Definition of Done

必须完成：Day9 frozen check；Package
V0.1/manifest/version/hash；manifest/SDK/interface
validation；trusted-code boundary；lightweight
smoke；registry/disable/history identity；Algorithm Center
Import/Detail；dynamic parameter form；Experiment
Workspace/Review/Run/logs/trace/KPI/evidence/export/rerun/clone；Benchmark
integration + new Day10 benchmark；Research Catalog implementation
link；implementation-origin provenance；timeout audit；无危险默认
algorithm timeout；optional time-limit semantics；HTTP timeout 与 run
lifecycle 分离；Day11 execution requirements；Quickstart；minimal
external example；AI
template（若实际可行）；backend/frontend/typecheck/build/browser
E2E；independent verification；evidence；Day4--9
regression；commit/push。

## 31. Final Report

必须报告：Code/Evidence commit、HEAD/origin、working tree、Package
Schema/SDK version、Reference
Package/Algorithm/version/provider/category/origin、manifest/source/package
hash、SDK/manifest/import/interface/smoke validation、smoke
evaluator、registration、compatibility/schema、CPU/GPU、dependency/security
policy、reference
experiment/problem/scenario/parameters/objective/constraints/budget/status/evaluations/rejections/logs/trace/KPI/evidence/verifier/export/rerun/clone、Day10
benchmark/comparable/package hash evidence、Timeout Audit path/dangerous
fixed timeout/action/HTTP separation/optional time-limit/cancellation
preparation/force terminate implemented?、Day11
requirements、Quickstart/example/AI template、all
tests/build/browser/console/evidence/screenshots、Day4--9
regression、limitations/debt、Day10 Final/Frozen、Day11 Ready。

# Day 11 Preview --- 不实现

下一阶段专门做 `Execution Management & Safe Cancellation`： Execution
Worker、Process Ownership、Heartbeat、Graceful Cancel、Force
Terminate、Process Group、Child/GPU Process Cleanup、Crash Recovery、Log
Streaming、Resource Metadata、Optional Time Limit。

不要 Day 10 提前做半套。

# 最终成功标准

Day 10 完成后必须能演示：

`平台之外实现的算法 → Package → Validate → Smoke → Register → Algorithm Center → Experiment Workspace → Platform Evaluation → KPI/Trace/Logs → Benchmark → Evidence/Export`

整个过程不修改平台核心算法执行逻辑。

**算法是否比 baseline 好，不是 Day 10 验收条件。**

# END OF DAY 10
