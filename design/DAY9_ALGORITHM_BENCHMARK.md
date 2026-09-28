# Day 9 --- Algorithm Benchmark & Comparison Framework

## 算法基准、兼容性与公平对比：从"能接算法"升级到"能验证算法"

> Day 8 Frozen Baseline: code `1e4cd88`, reference `OPT-9748F677`,
> `MULTICELL-DEMO-001`, 3 Cells / 12 UEs, scientific audit
> `PASS WITH LIMITATIONS / FROZEN`.
>
> **核心目标：把平台升级为多个算法在同一问题、同一场景、同一评价协议下进行公平、可复现、可验证
> Benchmark 的平台。**

## 0. Day 9 定位

Day 7 已完成 Algorithm Integration，Day 8 已完成真实 Multi-Cell User
Association Problem。Day 9 不以"增加一个高级科研算法"为目标，而建立
Engineering Baseline、Classical Optimization、Research
Algorithm、External Algorithm 共用的比较基础设施。

公平比较必须满足：Same Problem、Scenario、Initial
State、Channel/Dataset、Traffic、Objective、Constraints、KPI
Definitions、Evaluation Budget、Evaluation
Protocol。任一关键条件不同，不得直接给出算法优劣结论。

## 1. Algorithm--Problem Compatibility

新增 `AlgorithmCompatibility`，至少描述 variable types、constraint
support、objective support、batch、iterative feedback、training
required、gradient required、black-box support、multi-objective
support。

参数类型至少支持
`continuous / integer / discrete / categorical / vector / categorical_vector / mixed`。

算法 metadata 至少包含
algorithm_id、name、version、category、provider、learning_algorithm、training_required、gradient_required、black_box_support、supported_parameter_types、supported_constraint_types、supported_objective_directions、deterministic、supports_seed、sdk_version。

统一新分类：`engineering_baseline / classical_optimization / research / integration_demo / external`。历史
Day 7 `research_demo` 保持兼容，不改 frozen evidence。

## 2. Day 9 可运行基准算法

保留 Grid Search、Day 8 Association Optimizer、Research Demo
历史算法。新增少量可审计基准： - Random
Search：engineering_baseline，learning=false，seeded，同 seed
可复现，budget/constraint aware。 - First-Improvement Local
Search：classical_optimization，learning=false，单 UE reassociation
neighborhood，deterministic ordering。 - Best-Improvement Local Search
可选。

不要一次实现大量算法。

## 3. Research Algorithm Catalog

新增 `ResearchAlgorithmReference`，与可运行 `AlgorithmRegistry`
严格分离。字段至少包括
reference_id、algorithm_family、paper_title、authors、year、problem_types、parameter_types、requires_training、black_box、implementation_status、notes、source/DOI。

首批登记但**不要求实现**： - ZO-PGD /
ZO-BCPGD：连续/分块连续黑盒网络参数，status=`not_integrated`。 -
Solution Mapping / Learning to
Optimize：training_required=true，learning_algorithm=true，status=`not_integrated`。 -
Learning-assisted B&B / LORM-like：面向 mixed-integer/resource
management 的 research candidate；未来自研不得冒充论文官方实现。

Research Catalog 未进入 Registry 的算法绝不能出现在可运行下拉框。

## 4. 不把 ZO 强塞进 Day 8

Day 8 User Association 是 categorical-vector/combinatorial problem。经典
continuous ZO-PGD 并非天然匹配。Day 9 只登记研究候选，不把 association
人为连续化来制造 ZO demo。

## 5. Benchmark Canonical Entity

新增 `Benchmark`：
`benchmark_id, name, problem_id, scenario_set, protocol_id, algorithm_configs, status, created_at, completed_at, provenance`。

新增 `BenchmarkProtocol`：
`protocol_id/version/problem_type/scenario_ids/evaluation_context_policy/objective/constraints/kpi_versions/evaluation_budget/time_budget/initial_solution_policy/seed_policy/repeat_policy/channel_realization_policy/traffic_realization_policy/aggregation_policy/runtime_measurement_policy/hardware_environment_policy`。

创建 `ALGORITHM_BENCHMARK_V0_1`，第一版只针对
`MULTICELL-DEMO-001 / USER_ASSOCIATION`。

## 6. 公平协议

V0.1 所有算法共享： - Day 8 baseline association； - frozen channel
realization `CH-MULTICELL-FBD449D7`； - 同 traffic model/realization； -
`NETWORK_THROUGHPUT_WITH_P5_FLOOR_V0_1`； - `P5 >= baseline P5`； - 同
KPI versions； - 同 evaluation budget。

`evaluation_budget` 与 `time_budget` 必须分开。V0.1 可只强制 same
evaluation budget，runtime 作为观测值。提前停止允许，但必须记录
evaluations_used 和 stop_reason。

随机算法必须记录 seed。未记录随机源不得进入 comparable benchmark。

## 7. Channel Provenance V0.2

不改 Day 8 历史 hash。Day 9 新 run 建议将 channel provenance hash 绑定
scenario/version、cell IDs+coordinates、UE IDs+coordinates、carrier
frequency、scene、seed、link artifact、provider versions。

## 8. BenchmarkRun / Result

每个 Algorithm × Repeat 形成
`BenchmarkRun`：benchmark_run_id、benchmark_id、algorithm_id/version/config、seed、optimization_id、status、runtime、evaluations_used、best_candidate、feasible。

BenchmarkService 只能 orchestration 现有 OptimizationService：
`BenchmarkService → OptimizationService → Algorithm SDK → Evaluation → Backend`。
禁止复制第二套 optimizer engine。

`BenchmarkResult` 至少聚合 algorithm、objective、network throughput、avg
UE throughput、P5、feasible、evaluations_used、runtime、stop_reason。

## 9. Runtime 语义

定义 `ALGORITHM_RUNTIME_V0_1`，尽可能拆分： - optimizer_overhead_time -
simulation_evaluation_time - total_wall_time

如果当前只能可靠记录 total，必须明确限制。不得把 simulator runtime
冒充纯算法 runtime。

硬件 provenance
至少记录环境标识、CPU、GPU（若用）、Python、Sionna、Torch。单机单 repeat
只能描述"当前硬件与冻结协议下"的 runtime，不得泛化。

## 10. Convergence Trace

统一使用：
`evaluation_index / elapsed_time / current_objective / best_feasible_objective / current_feasible / best_candidate_id`。

Benchmark 横轴优先 Simulator Evaluations，而非 iteration，因为不同算法
iteration 语义不同。

核心图： 1. Best Feasible Objective vs Evaluations 2. Best Feasible
Objective vs Time 3. KPI Comparison 4. Evaluations / Runtime Comparison

## 11. Comparison

比较表至少显示 Algorithm、Category、Learning?、Best Objective、Network
Throughput、P5、Feasible、Evaluations Used、Total Runtime、Stop
Reason、Verification。

**禁止 Overall Score、自动冠军、排行榜。** 平台展示
quality/speed/feasibility/trade-off，不替研究人员决定"最好算法"。

新增 `comparison_eligible` 与 `comparison_reason`。它与
`verified`、`acceptance_eligible`、`data_source` 完全分离。

若 context/budget/objective/constraint/KPI version
等关键公平条件不一致： `comparison_eligible=false`，UI 禁止直接
comparison chart，并显示 `Runs are not directly comparable`。

## 12. Repeat

schema 必须支持 `num_repeats > 1`，但 Day 9 Reference 可使用 1 次 repeat
控制成本。单 repeat 禁止 confidence interval、variance、statistical
significance、statistically better 等表述。

未来 repeat dimensions 支持 scenario × channel × traffic × seed。

## 13. Day 9 Reference Benchmark

建议： - Scenario: `MULTICELL-DEMO-001` - Algorithms: Day 8 Association
Baseline + Random Search + First-Improvement Local Search - Same
evaluation budget: Agent 根据真实 runtime 选择并说明 - Repeats: 1

不要求算法得到不同最终结果；三个算法都停在 baseline 仍可
PASS。成功标准是公平比较链成立。

## 14. Provenance / Evidence UI 降噪

普通页面不再反复显示 "Not Huawei / Not Measured / Not Acceptance"。

统一拆成： - Data Source: simulation / measured / semi_synthetic /
calibrated / imported - Provider: nvidia_sionna / huawei / third_party /
research_team / unknown - Verification: unverified / verified /
independent_verified / failed - Evidence Level: simulation_evidence /
measured_validation / acceptance_evidence

Huawei 是 provider，不是 evidence type。

普通页面最多显示 `仿真`、`✓ 已验证` 小 badge；Simulation 本身不是
Warning。Warning 只用于 dirty tree、verification failed、provenance
incomplete、context mismatch、KPI mismatch 等异常。

Detail 页面显示紧凑 Evidence & Provenance，完整 provenance
点击展开。Acceptance Center 仍完整显示 Simulation Evidence、Measured
Validation、Acceptance KPI Mapping、Expert/Third-party
Validation、Acceptance Eligible。

保留 legacy measured/huawei/acceptance 字段的兼容映射，不破坏 Day 4--8
historical evidence。

## 15. Algorithm Center

增加： - Runnable Algorithms - Research Catalog - Algorithm × Problem
Compatibility Matrix

Compatibility
状态：`compatible / compatible_with_limits / research_candidate / incompatible / unknown`。矩阵由
metadata/rules 生成，不得前端 hard-code，也不得用它宣称论文性能。

## 16. Benchmark Center

新增一级页或 Optimization Center 子页 `Benchmark / 算法对比`。

Create：Problem、Scenario、Algorithms、Protocol、Evaluation
Budget、Repeats。默认只显示 compatible；advanced 可看
compatible_with_limits；incompatible 不可提交。

Detail tabs： - Overview - Comparison - Convergence - Runs - Evidence

Run 可 drill down 到原 Optimization Detail，保持
`Benchmark → Optimization → Experiment → Artifact` 证据链。

## 17. EvidenceDescriptor

扩展：
`evidence_type=algorithm_benchmark / comparison_eligible / comparison_reason / benchmark_id / protocol_id / protocol_hash / run_ids`。

Day 9 reference：
`verified=true, comparison_eligible=true, acceptance_eligible=false, data_source=simulation`。

Acceptance Center 新增能力 `Algorithm Comparative Validation`，状态
`Simulation Evidence Available`，不是 Acceptance PASS。

## 18. Independent Verifier

新增/扩展 `verify_benchmark.py`，独立检查 protocol hash、same
problem/scenario/baseline/channel/traffic/objective/constraints/KPI/budget、algorithm
metadata/seeds、optimization IDs、result
KPI、feasibility、evaluations、convergence、runtime
fields、aggregation、EvidenceDescriptor。

Verifier 不得调用 production benchmark comparison evaluator
来"验证自己"。

输出 `Comparable = YES/NO`。

Tamper tests 至少覆盖 protocol
hash、channel、budget、objective、constraint、algorithm config、result
KPI、convergence trace、comparison eligibility。

## 19. Tests

Compatibility：compatible/incompatible parameter type、constraint
support、training metadata、research catalog not runnable。

Protocol：deterministic hash、same
context/budget/objective/constraints/KPI required。

Execution：multiple algorithms、shared
baseline/channel/traffic/budget、seed recorded、early
stop、run→optimization link。

Comparison：eligible、context mismatch、budget mismatch、KPI
mismatch、infeasible preserved、no overall score。

Provenance：simulation not warning、provider independent from source
type、verified independent from acceptance、comparison independent from
acceptance、legacy mapping。

前端覆盖 Runnable/Research Catalog/Compatibility/Benchmark
Create/Running/Comparison/Convergence/Runs/Evidence/provenance
badges/Acceptance mapping。

## 20. Browser Smoke

真实浏览器：
`Home → Algorithm Center → Runnable → Research Catalog → Compatibility → Benchmark Center → Create → MULTICELL-DEMO-001 → compatible algorithms → Freeze Protocol → Run → Comparison → Convergence → Open Run → Back → Evidence → Acceptance Center`

Console Errors = 0。

## 21. Reference Evidence

创建 `reference/benchmarks/BENCH-XXXXXXXX/`，至少合理保存
README、benchmark、protocol、algorithms、runs、comparison、convergence、verification、evidence-descriptor、provenance；不要为凑数量重复数据。

README： - Purpose: Algorithm Benchmark and Comparative Validation -
Problem: User Association - Data Source: Simulation - Verification:
Independent - Comparison Eligible: YES - Acceptance Eligible: NO

不再写大段"非华为实测"免责声明。

## 22. Definition of Done

必须完成：Day 8 frozen check；compatibility model；Research
Catalog；Runnable/Research separation；Random Search；Local
Search；Benchmark/Protocol/Run/Result；same
baseline/channel/traffic/objective/constraints/KPI/budget；seed/repeat
schema；convergence/runtime；comparison eligibility；independent
verifier + tamper；provenance normalization + UI 降噪；Benchmark
Center；reference
benchmark；plots/screenshots；backend/frontend/typecheck/build/browser
smoke；Day 4--8 regression；commit + push。

## 23. Stop Conditions

立即停止并报告，如果： 1. 不同算法使用不同 channel 却标 comparable； 2.
budget 不一致却标 comparable； 3. 算法绕过 OptimizationService 直接调用
backend； 4. Research Catalog 未实现算法可运行； 5. simulator time
被冒充 algorithm-only runtime； 6. UI 自动排名/综合评分； 7. 修改 Day 8
frozen baseline 来制造差异； 8. 为接 ZO 强行连续化离散 association； 9.
provenance 改造破坏 Day 4--8 evidence； 10. Day 4--8 regression
出现无法解释失败。

## 24. Final Report

必须报告：Code/Evidence Commit、HEAD/origin、working tree、SDK、Protocol
ID/version、Benchmark ID、Problem/Scenario/Channel/hash
version/Traffic/Objective/Constraints/KPI/Budget/Repeats、Algorithms/versions/categories/learning
flags/seeds/compatibility、Optimization
IDs、evaluations/cache/rejections/stop
reasons、objective/KPI/feasibility/runtime/evaluation
time/overhead、comparison eligibility/reason、independent
verification/tamper/tests/Sionna/frontend/typecheck/build/browser/console、evidence/screenshots、Data
Source/Provider/Verification/Evidence Level/Acceptance、Research Catalog
statuses、Day 4--8 regression、limitations/debt、Day 10 Ready YES/NO。

## 25. Day 10 Preview --- 不要实现

Day 10 根据 Day 9 结果选择： - Route A：建立连续网络参数案例，再接
ZO-PGD / ZO-BCPGD； - Route B：继续离散/混合 User Association/Resource
Allocation，调研 Branch-and-Bound / learning-assisted search
等匹配算法。

不要在 Day 9 提前决定。

# Final Instruction

Day 9 成功不是"平台算法更多了"，而是：

`Same Problem + Same Evaluation Protocol + Multiple Compatible Algorithms + Independent Verification → Fair Algorithm Benchmark`

平台应该能够科学回答：在同一冻结仿真条件和评价预算下，各算法产生了什么结果、消耗多少计算资源、是否满足约束、优化轨迹有何差异。

平台展示证据，不替研究人员宣布哪个算法"最好"。

# END OF DAY 9
