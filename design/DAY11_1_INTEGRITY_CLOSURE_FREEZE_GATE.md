# Day 11.1 --- Integrity Closure & Freeze Gate

## Day 11 收口：Timeout、独立验证、Comparison 身份完整性与浏览器 E2E

> **Base HEAD:** `f4a1858`
>
> **性质：** Day 11.1 是收口任务，不是新功能日。
>
> **禁止进入 Day 12 功能开发，直到本任务全部完成并通过。**
>
> Day 11 主体方向正确，但源码审计仍有 4 个冻结 blocker：
>
> 1.  legacy `ExperimentService` 的 600 秒 soft timeout
>     仍可能把合法长实验标记 FAILED；
> 2.  explicit time limit 尚未形成完整的 graceful → force terminate →
>     terminal state 自动闭环；
> 3.  Comparison verifier 仍复用 production
>     `preview()`，不是真正独立验证；
> 4.  Comparison scientific identity 不完整，缺失 provenance
>     时不能靠默认值推断"相同"。
>
> 同时收口：
>
> -   Benchmark README 在 verifier 未运行前不得写
>     `Verification: Independent`；
> -   User Association evaluation adapter 不应通过 `BenchmarkService`
>     private method 获取 frozen channel。
>
> **不新增算法、不新增 5G 问题、不追求 KPI 改善、不修改历史 reference
> 数值。**

------------------------------------------------------------------------

# 1. Freeze Gate

完成前：

``` text
DAY 11 FROZEN = NO
DAY 12 READY = NO
```

全部通过后才允许：

``` text
DAY 11.1 FINAL = PASS WITH DOCUMENTED LIMITATIONS
DAY 11 FROZEN = YES
DAY 12 READY = YES
```

------------------------------------------------------------------------

# 2. P0 --- 移除 legacy 600 秒 scientific failure

当前 legacy propagation `ExperimentService` 仍存在类似：

``` python
DEFAULT_TIMEOUT_SECONDS = 600
future.result(timeout=self._timeout)
```

并可能在 timeout 后把实验写成：

``` text
FAILED
SIMULATION_TIMEOUT
```

但 worker thread 继续运行。

必须修复。

## 正确区分三种时间

### HTTP / request wait timeout

只表示客户端不再等待当前请求。

**不得改变后台实验的科学状态。**

### User/Protocol explicit time limit

只有用户或协议明确配置：

``` text
time_limit_seconds = N
```

才允许因 wall-clock 达到 N 而终止 Run。

默认：

``` text
time_limit_seconds = null
```

### Worker health / stale heartbeat

只用于判断 worker 是否失联。

**算法运行时间长、objective 长时间不改善，都不是 hung 的充分证据。**

## 禁止伪修复

以下都不算完成：

``` text
600 → 3600
600 → 86400
600 → configurable default 600
```

正确语义是：

``` text
no implicit scientific wall-clock failure
```

## Regression

不真的 sleep 600 秒。使用 fake future / injectable clock / monkeypatch。

必须证明：

``` text
request wait expires
→ background run is NOT marked FAILED merely for elapsed wall time
```

------------------------------------------------------------------------

# 3. P0 --- Explicit Time Limit 自动闭环

不能只：

``` text
request_cancel()
time_limit_pending=true
```

然后等待人工再次操作。

必须自动：

``` text
RUNNING
→ time limit reached
→ CANCEL_REQUESTED
→ CANCELLING
→ graceful wait
→ worker exits OR owned process-group termination
→ TIME_LIMIT_EXCEEDED
```

如果 graceful 不响应：

``` text
SIGTERM owned process group
→ terminate grace
→ SIGKILL owned process group if required
→ TIME_LIMIT_EXCEEDED
```

状态语义必须区分：

``` text
用户正常停止       → CANCELLED
用户强制终止       → TERMINATED
明确 time limit    → TIME_LIMIT_EXCEEDED
运行异常           → FAILED
```

统一配置：

``` text
cancel_grace_seconds
terminate_grace_seconds
```

禁止散落 magic numbers。

------------------------------------------------------------------------

# 4. Process Ownership / Child Cleanup

只允许操作：

``` text
run.worker_pid
run.process_group_id
owned child pids
```

严禁：

``` text
killall python
pkill python
kill all GPU processes
global CUDA reset
```

Force/time-limit 后验证：

``` text
worker PID gone
owned child PIDs gone
process group has no owned live members
```

不能确认时记录 cleanup warning，不能假装 PASS。

当前 CUDA 不可用时：

``` text
GPU cleanup path implemented
GPU cleanup runtime verification = NOT VERIFIED IN CURRENT ENVIRONMENT
```

------------------------------------------------------------------------

# 5. HTTP / Browser 生命周期独立

必须测试：

``` text
request ends
browser refreshes
user leaves page
client stops polling
```

均不得自动造成：

``` text
FAILED
CANCELLED
TERMINATED
```

后台 Run 按自身生命周期继续。

------------------------------------------------------------------------

# 6. P0 --- 真正独立的 Comparison Verifier

建议：

``` text
src/comparison/verifier.py
```

或等价独立模块。

**不得 import/call：**

``` text
ComparisonService
ComparisonService.preview()
production compatibility evaluator/helper
```

可以读取：

-   canonical models/schema；
-   persisted Run/evidence；
-   immutable identity constants；
-   hash utilities。

Verifier 自己重算：

``` text
selected_run_ids
comparison_intent
problem
dataset
scenario
channel
traffic
objective
constraints
KPI
protocol
budget
backend
algorithm/package/parameters
```

输出至少：

``` text
status
comparison_id
recomputed_eligibility
stored_eligibility
checks
mismatches
verified_at
verifier_version
```

Verifier 只验证可比性描述是否正确，不推荐算法、不评判哪个算法"更好"。

------------------------------------------------------------------------

# 7. P0 --- Scientific Identity 补全

Comparison 的关键 identity 至少：

``` text
problem_type

dataset_id
dataset_version/hash

scenario_id
scenario_version/hash

channel_artifact_id
channel_hash

traffic_realization_id
traffic_hash

objective_id
objective_version

constraints_id/version or canonical hash

kpi_definitions
kpi_versions

protocol_id
protocol_version

evaluation_budget

backend_id
backend_version
```

另行展示：

``` text
algorithm_id
algorithm_version
package_hash
hyperparameters
optimization variables
seed
```

哪些允许变化由 `comparison_intent` 决定。

------------------------------------------------------------------------

# 8. Missing != Equal

这是 Day 11.1 的强制原则。

错误：

``` text
Run A dataset missing → default
Run B dataset missing → default
→ SAME
```

正确：

``` text
dataset = UNKNOWN
→ insufficient scientific context
```

关键 identity 不得在 `_snapshot()` 读取阶段用默认值补齐，除非该值是 Run
创建时真实持久化的数据。

建议 eligibility：

``` text
COMPARABLE
COMPARABLE_WITH_DECLARED_DIFFERENCES
NOT_DIRECTLY_COMPARABLE
INSUFFICIENT_CONTEXT
```

如果不扩 enum，也必须能区分：

``` text
known mismatch
```

和：

``` text
missing/unknown
```

UI 中文显示：

``` text
一致
不同
允许变化
未知
历史实验未记录
证据不足，不能确认直接可比
```

------------------------------------------------------------------------

# 9. Legacy Run Identity

历史 Day 8/9/10 evidence 不重写。

如需：

``` text
LegacyRunIdentityAdapter
```

只能从已有可信 evidence 提取。

不能证明的字段：

``` text
UNKNOWN
```

不得为了让 Comparison PASS 而推断历史缺失数据。

------------------------------------------------------------------------

# 10. Comparison Reference Cases

Day 11.1 建立三个新 reference。

## Positive

关键 identity 全部一致。

``` text
Comparable = YES
```

## Known mismatch

例如 channel/scenario/protocol/backend version 不同。

``` text
Not Directly Comparable
```

## Missing identity

至少一个关键 identity 缺失。

``` text
Insufficient Context
```

或等价的不可直接比较状态。

三者都必须通过独立 verifier。

------------------------------------------------------------------------

# 11. Tamper Tests

至少：

``` text
selected run substitution
dataset hash tamper
scenario identity tamper
channel hash tamper
traffic identity tamper
objective version tamper
constraint tamper
KPI version tamper
protocol version tamper
budget tamper
backend version tamper
package hash tamper
hidden hyperparameter difference
stored eligibility tamper
fake verification PASS
```

------------------------------------------------------------------------

# 12. Verification State

继续保持：

新 evidence 初始：

``` text
verified=false
verification_status=PENDING/UNVERIFIED
```

只有 independent verifier 真正 PASS 后：

``` text
verified=true
verification_status=VERIFIED / independently_verified
verifier_id
verifier_version
verified_at
verification_hash
```

Verifier FAIL 不删除原 Run。

------------------------------------------------------------------------

# 13. Benchmark README Premature Verification

Verifier 未执行前不得写：

``` text
Verification: Independent
```

应写：

``` text
验证状态：待独立验证
```

或等价表述。

历史 Benchmark KPI/Run 数值不得修改。

允许新增：

``` text
legacy semantics note
migration note
verifier sidecar
```

------------------------------------------------------------------------

# 14. Frozen Channel Loader 解耦

移除：

``` text
UserAssociationEvaluationAdapter
→ BenchmarkService._load_day8_frozen_channel()
```

抽独立服务，例如：

``` text
FrozenArtifactService
ChannelArtifactRepository
ScenarioArtifactService
```

职责：

``` text
load artifact
verify artifact hash
return canonical frozen artifact
```

Benchmark 与 Problem Adapter 都依赖该 artifact layer。

历史：

``` text
CH-MULTICELL-FBD449D7
```

不得重新运行 Sionna RT 替换。

------------------------------------------------------------------------

# 15. Regression Guards

继续确认：

``` text
unknown scenario → SCENARIO_NOT_FOUND
```

绝不 silent fallback。

继续确认：

``` text
evaluation_budget = 13 / 20
```

业务层能够接受，不再存在全局 `<=12`。

不要求真正执行巨大 budget。

------------------------------------------------------------------------

# 16. Managed Execution Scope

Day 11.1 不扩大范围。

必须真实 managed：

``` text
external algorithm runs
```

Legacy propagation/system/system optimization 尚未全部迁移时，可以作为
documented debt。

但：

**legacy 默认 600 秒自动 scientific failure 必须消失。**

------------------------------------------------------------------------

# 17. Browser E2E --- 强制 Freeze Gate

这次不能再写：

``` text
Browser E2E not run
```

必须执行。

## E2E A --- Positive Comparison

``` text
对比分析
→ 选择两个真正可比 Run
→ 算法对比
→ 查看条件一致性
→ 创建 Comparison
→ KPI
→ 运行时间
→ 收敛
→ 参数差异
→ 证据
```

结果：

``` text
Comparable
console errors = 0
```

## E2E B --- Known Mismatch

选择关键 context 不同的 Runs。

结果：

``` text
不可直接比较
```

允许：

``` text
并排查看
```

禁止：

``` text
gain
winner
ranking
```

## E2E C --- Missing Identity

选择 incomplete/legacy Run。

结果：

``` text
未知 / 证据不足
```

不得自动补默认值显示"一致"。

## E2E D --- Graceful Cancel

``` text
RUNNING
→ 停止运行
→ CANCEL_REQUESTED/CANCELLING
→ CANCELLED
```

检查 worker 消失、logs/trace 保留。

## E2E E --- Force Terminate

启动 deliberately unresponsive trusted test worker：

``` text
RUNNING
→ graceful cancel 无响应
→ 强制终止
→ 二次确认
→ TERMINATED
```

检查 owned worker/child gone。

## E2E F --- Explicit Time Limit

短测试 time limit：

``` text
RUNNING
→ limit reached
→ automatic graceful attempt
→ escalation if needed
→ TIME_LIMIT_EXCEEDED
```

不得人工再次触发。

## E2E G --- Refresh Independence

Run 运行中刷新/离开再返回：

``` text
Run remains RUNNING
```

------------------------------------------------------------------------

# 18. Browser Evidence

保存到：

``` text
reference/day11_1/<REFERENCE-ID>/screenshots/
```

至少覆盖：

``` text
positive comparison
known mismatch
missing identity
graceful cancel
force terminate
time limit
refresh-running
```

所有 E2E：

``` text
console errors = 0
```

warning 如存在必须解释。

------------------------------------------------------------------------

# 19. Backend Tests

至少覆盖：

``` text
legacy timeout separation
explicit time-limit lifecycle
automatic time-limit escalation
process ownership
child cleanup
HTTP lifecycle independence
independent comparison verifier
verifier does not call production preview
positive comparison
known mismatch
missing identity
tamper cases
artifact loader
scenario not found
budget >12
verification transition
Benchmark README pending state
```

------------------------------------------------------------------------

# 20. Frontend Tests

至少：

``` text
comparison positive state
comparison mismatch state
comparison unknown state
Chinese labels
cancel action
force-terminate confirmation
TIME_LIMIT_EXCEEDED display
```

最终报告必须给实际：

``` text
node --version
npm --version
frontend test count
typecheck
production build
```

------------------------------------------------------------------------

# 21. Regression

完整运行 Day 4--11 regression。

特别冻结：

``` text
Day4 objective semantics
Day5 KPI
Day6 frozen-context fairness
Day7 SDK
Day8 association/reference
Day9 benchmark
Day10 package/onboarding
Day11 comparison/execution
```

不得为了 Day 11.1 PASS 修改历史 KPI/reference 数值。

------------------------------------------------------------------------

# 22. 禁止事项

Day 11.1 不做：

``` text
新算法
新 optimizer
算法调参
换 seed 获取更好 KPI
新 5G optimization problem
新 Sionna scenario
```

这是工程收口，不是功能扩张。

------------------------------------------------------------------------

# 23. Stop Conditions

任一出现立即停止并报告：

1.  仍存在默认 600 秒 scientific failure；
2.  只是把 600 改成更大默认值；
3.  explicit time limit 需要人工第二次操作才完成；
4.  time-limit 最终写成 CANCELLED；
5.  Force Terminate 只改数据库状态；
6.  owned child 仍活着却报告 cleanup PASS；
7.  Comparison verifier 调用 production `preview()`；
8.  missing scientific identity 被默认值补成 SAME；
9.  Dataset/traffic/backend version 不参与 identity；
10. verifier 未运行就写 independently_verified；
11. Benchmark README 未验证就写 Independent；
12. Problem adapter 仍调用 BenchmarkService private loader；
13. 为修复 reference 重新运行 Sionna RT；
14. scenario silent fallback 重新出现；
15. budget \<=12 重新出现；
16. 浏览器 E2E 未执行；
17. console errors 非 0 且未解释；
18. 历史 KPI/reference 被改写。

------------------------------------------------------------------------

# 24. Definition of Done

-   [ ] legacy default 600s scientific failure removed
-   [ ] request wait separated from scientific state
-   [ ] default time_limit=null
-   [ ] explicit time-limit automatic lifecycle
-   [ ] TIME_LIMIT_EXCEEDED terminal semantics
-   [ ] graceful cancel
-   [ ] force terminate escalation
-   [ ] process ownership
-   [ ] child cleanup
-   [ ] GPU limitation honest
-   [ ] HTTP/page lifecycle independent
-   [ ] independent Comparison verifier
-   [ ] verifier does not call production preview
-   [ ] dataset identity included
-   [ ] traffic identity included
-   [ ] backend version included
-   [ ] objective/constraint/KPI/protocol versions included
-   [ ] missing != equal
-   [ ] unknown/insufficient context represented
-   [ ] positive comparison reference
-   [ ] mismatch reference
-   [ ] missing-identity reference
-   [ ] tamper tests
-   [ ] evidence transition correct
-   [ ] Benchmark README pending verification fixed
-   [ ] frozen artifact loader extracted
-   [ ] Problem adapter no BenchmarkService private dependency
-   [ ] Day8 frozen artifact preserved
-   [ ] scenario-not-found regression
-   [ ] budget \>12 regression
-   [ ] browser positive comparison E2E
-   [ ] browser mismatch E2E
-   [ ] browser unknown E2E
-   [ ] browser graceful cancel E2E
-   [ ] browser force terminate E2E
-   [ ] browser time-limit E2E
-   [ ] browser refresh-running E2E
-   [ ] console errors 0
-   [ ] backend tests
-   [ ] frontend tests
-   [ ] typecheck
-   [ ] production build
-   [ ] Day4--11 regression
-   [ ] evidence committed
-   [ ] commit pushed
-   [ ] clean worktree

------------------------------------------------------------------------

# 25. Final Report --- 必须逐项回答

1.  Base commit
2.  Day 11.1 code commit
3.  Day 11.1 evidence/docs commit
4.  HEAD
5.  origin/main
6.  working tree
7.  legacy 600s behavior before
8.  legacy timeout behavior after
9.  default scientific time limit
10. request wait semantics
11. explicit time-limit lifecycle
12. cancel grace
13. terminate grace
14. TIME_LIMIT_EXCEEDED verified YES/NO
15. graceful cancel verified YES/NO
16. force terminate verified YES/NO
17. worker PID cleanup
18. child PID cleanup
19. GPU cleanup runtime status
20. HTTP/page lifecycle independence
21. Comparison verifier path
22. imports ComparisonService YES/NO
23. calls production preview YES/NO
24. verifier version
25. dataset identity
26. dataset version/hash
27. scenario identity
28. channel artifact/hash
29. traffic identity/hash
30. objective id/version
31. constraints id/version/hash
32. KPI versions
33. protocol id/version
34. evaluation budget
35. backend id/version
36. missing identity behavior
37. positive comparison ID
38. positive eligibility
39. mismatch comparison ID
40. mismatch reason
41. missing-identity comparison ID
42. missing-identity result
43. tamper tests
44. evidence initial state
45. evidence post-verifier state
46. Benchmark README pre-verifier text
47. artifact loader path
48. Problem adapter private BenchmarkService dependency removed YES/NO
49. Day8 frozen channel ID
50. Day8 frozen hash unchanged YES/NO
51. scenario fallback absent YES/NO
52. budget 13/20 accepted YES/NO
53. Node version
54. npm version
55. frontend tests
56. typecheck
57. production build
58. browser positive comparison
59. browser mismatch
60. browser unknown identity
61. browser graceful cancel
62. browser force terminate
63. browser time limit
64. browser refresh-running
65. console errors
66. backend tests
67. Day4 regression
68. Day5 regression
69. Day6 regression
70. Day7 regression
71. Day8 regression
72. Day9 regression
73. Day10 regression
74. Day11 regression
75. evidence paths
76. known limitations
77. technical debt
78. Day11.1 Final
79. Day11 Frozen
80. Day12 Ready

------------------------------------------------------------------------

# 26. 最终验收口径

只有以下四句话都有代码、测试和浏览器证据直接支持时，才能冻结 Day 11：

> **一个正常的长实验不会因为平台默认等待时间而被误判失败。**

> **用户明确设置的 time limit 会真正停止属于该 Run 的 worker，并以
> TIME_LIMIT_EXCEEDED 结束。**

> **Comparison 是否可直接比较，由独立 verifier 根据完整 scientific
> identity 重算，而不是 production service 自证。**

> **用户已经在真实浏览器中走通过 Comparison、Cancel、Force Terminate 和
> Time Limit 的完整流程。**

否则：

``` text
DAY 11 FROZEN = NO
DAY 12 READY = NO
```

# END OF DAY 11.1
