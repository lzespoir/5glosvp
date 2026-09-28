# Algorithm Integration Contract v0.1 / 算法接入契约 v0.1

`ALGORITHM_SDK_VERSION = "0.1"`（`src/algorithms/sdk.py`）

本文件定义平台与优化算法之间的稳定接口。它规定 **算法可以做什么、平台保证什么**，
不评价任何算法的科研价值。

> 边界：平台拥有场景、参数空间、评价协议、仿真、KPI、目标函数、实验、预算与证据；
> 算法只拥有候选生成 / 搜索逻辑。

---

## 1. Lifecycle / 生命周期

平台的 `AlgorithmDriver`（`src/algorithms/driver.py`）驱动一次运行，算法不能自行调用仿真：

```text
check_compatibility(algorithm, problem, hyperparameters)      # 平台：能力 / 超参数 / 预算检查（4xx）
algorithm.validate_problem(problem, hyperparameters)          # 算法：额外的特定检查
algorithm.initialize(problem, hyperparameters, incumbents)    # incumbents = 已评价的基线
loop:
    stop = algorithm.should_stop()            → 非 None 则停止（算法给出 stop reason）
    remaining = max_evaluations − used        → ≤ 0 则 BUDGET_EXHAUSTED
    suggestions = algorithm.suggest(remaining) → 空列表则 COMPLETED（或算法已声明的 stop）
    accepted = suggestions[:remaining]        → 其余被拒绝并记录，本轮后 BUDGET_EXHAUSTED
    每个 accepted：ParameterSpace.validate_point → 平台评价（同一冻结上下文，可命中缓存）
    algorithm.observe(results)
recommendation = algorithm.finalize()
```

| 方法 | 输入 | 输出 | 约束 |
|---|---|---|---|
| `metadata()`（classmethod） | – | `AlgorithmMetadata` | 纯声明，不得有副作用 |
| `validate_problem` | `AlgorithmProblem`、已解析超参数 | `list[CompatibilityIssue]` | 只做检查，不评价 |
| `initialize` | 问题、超参数、incumbents | – | 每次运行一个新实例（`registry.create`） |
| `suggest(max_suggestions)` | 剩余预算 | `list[dict[param_id, value]]` | 值必须位于参数空间内，否则运行 FAILED |
| `observe(results)` | `list[EvaluationResult]` | – | 结果顺序与被接受的建议顺序一致 |
| `should_stop()` | – | `StopReason \| None` | – |
| `finalize()` | – | `AlgorithmRecommendation` | `parameters=None` 表示由平台选最优 |
| `state_metadata()` | – | JSON 可序列化 dict | 写入 trace；不得含二进制 / pickle |

算法抛出的任何异常或非法建议都会被转为 `AlgorithmExecutionError`：
运行状态 `failed`、trace `stop_reason = failed`，已有 trace 与候选保留。

## 2. Metadata / 元数据

`AlgorithmMetadata` 字段：`algorithm_id`、`name_zh/en`、`version`、`category`、`description_zh/en`、
`purpose_zh/en`、`provider`、`learning_algorithm`、`project_research_deliverable`、`acceptance_algorithm`、
`capabilities`、`hyperparameter_schema`、`supported_problem_types`、`source`、`status`、`sdk_version`、`labels`；
计算字段 `supported_parameter_types`、`auto_configuration`。

| category | 含义 |
|---|---|
| `engineering_baseline` | 工程基线（例如 Grid Search），不是科研成果 |
| `research_demo` | 接入验证算法（例如 Research Demo Optimizer），不是科研成果 |
| `research` | 项目科研团队交付的算法（Day 7 没有） |
| `external` | 第三方算法 |

诚实声明规则：

- `learning_algorithm = true` 只能用于真正基于数据学习的算法；“会根据反馈调整步长”不算学习。
- `capabilities` 只声明真实实现的能力；未实现的全部为 `false`。
- `acceptance_algorithm` 在 Day 7 全部为 `false`。

## 3. Parameter Space / 参数空间

`ParameterSpace`（`src/algorithms/parameter_space.py`）= `parameters: list[ParameterDefinition]`（≥ 1，id 唯一，
只允许 `role = optimization_variable`）+ 声明式 `constraints` + `metadata`。

| type | 必填 | Day 7 端到端 |
|---|---|---|
| `continuous` | `bounds`（可开 / 闭区间） | 是（Research Demo） |
| `discrete` | `choices` | 是（Grid Search） |
| `integer` | `bounds` | 仅 schema / 校验 |
| `categorical` | `choices` | 仅 schema / 校验 |
| `vector` | `shape`、`element_type`、逐元素 `bounds` | 仅 schema / 校验 |

- 超参数（`HyperparameterDefinition`：float / integer / boolean / categorical）与网络变量完全分离，
  不会出现在参数空间中。
- 参数空间哈希：`sha256(canonical_json(parameter_space.model_dump(mode="json")))`，
  `canonical_json = json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`。
- 平台对搜索区间只允许 **收窄**：请求的 bounds 必须位于平台推荐区间内（例如 `scheduler_beta ∈ [0.05, 0.99]`，
  标注 [A] 工程演示区间）。

## 4. Evaluation Interface / 评价接口

算法看到的 `AlgorithmProblem`：`problem_type`、`parameter_space`、`objective_id`、`objective_direction`、
`objective_count`、`baseline_parameters`、`max_evaluations`。

算法收到的 `EvaluationResult`：`candidate_id`、`parameters`、`objective`、`objective_direction`、
`secondary_metrics`、`constraint_results`、`status`（evaluated / failed）、`runtime_seconds`、`cache_hit`，
以及 `score()`（方向归一化：越大越好；失败为 `None`）。

算法 **看不到**：Sionna / 仿真器对象、实验仓库、NPZ 路径、KPI 实现、随机种子。
`src/algorithms` 包不得 import `sionna`、`system_simulation`、`experiments`、`evaluation.kpi`、
`system_optimization`、`simulation`（由测试强制）。

同一次运行的所有评价在同一个 `CommonEvaluationContext` 中进行（相同信道、UE、业务、时隙、协议、后端），
公平性由平台检查与记录。

## 5. Budget / 评价预算

- `max_evaluations`：每个被接受的建议计 1 次（包括缓存命中）；基线不计入。
- 默认 `DEFAULT_EVALUATION_BUDGET = 8`，上限 `MAX_EVALUATION_BUDGET = 12`；Grid Search 默认 = 候选数。
- 预算由平台执行：超出剩余预算的建议被拒绝（记录在 trace 的 `rejected_suggestions`），运行 `budget_exhausted`。
- 记录：`max_evaluations`、`evaluations_used`、`simulations_run`、`cache_hits`、`rejected_suggestions`。

### Evaluation cache / 评价缓存

```text
key = sha256(canonical_json({
  context:    {ue_population_sha256, channel_sha256, traffic_sha256, simulation_horizon,
               benchmark_protocol: [id, version], scheduler_config, link_adaptation_config,
               power_control_config, scenario_version},
  parameters: 按 key 排序,
  backend:    {id, version}}))
```

- 只在同一运行、同一上下文内复用；不同信道 / UE / 协议 / 后端版本的键必然不同。
- 失败的评价不缓存。
- 命中时生成新的候选记录：`cache_hit = true`、`reused_candidate_id` 指向源候选（基线值则 `reused_baseline = true`），
  复用同一实验 id；仍消耗 1 次预算，不重复仿真。

## 6. Stop reasons / 停止原因

`completed`、`max_iterations`、`converged`、`no_improvement`、`budget_exhausted`、`failed`、`cancelled`。
`budget_exhausted` 由平台给出；`failed` 表示算法异常或违反契约；`cancelled` 表示服务中断后恢复。

## 7. Errors / 错误

兼容性检查在创建运行 **之前** 完成，失败返回 HTTP 422（未知算法 404），`detail.errors` 列出全部问题：

| code | 触发条件 |
|---|---|
| `ALGORITHM_PROBLEM_TYPE_NOT_SUPPORTED` | 问题类型不在 `supported_problem_types` |
| `ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED` | 参数类型不在能力声明中（例如 Grid Search × continuous） |
| `ALGORITHM_PARAMETER_COUNT_NOT_SUPPORTED` | 参数数 > `max_parameters` |
| `ALGORITHM_CONSTRAINTS_NOT_SUPPORTED` | 有约束但 `supports_constraints = false` |
| `ALGORITHM_MULTI_OBJECTIVE_NOT_SUPPORTED` | 多目标但不支持 |
| `INVALID_HYPERPARAMETER` | 未知 / 越界 / 类型错误的超参数，或 `validate_problem` 报告的问题 |
| `INVALID_EVALUATION_BUDGET` | 预算 < 1 或 > 平台上限 |

运行中算法异常 → 运行 `failed`，错误码 `ALGORITHM_FAILED`。

## 8. Trace / 可审计轨迹

`algorithm-trace.json`：`algorithm_id/version`、`sdk_version`、`hyperparameters`、`max_evaluations`、
`initial_state`、`evaluations[]`（sequence、round、candidate_id、parameters、objective、secondary_metrics、
status、cache_hit、best_so_far_*）、`rounds[]`（state_before、suggestions、evaluated_candidate_ids、
rejected_suggestions、state_after）、`evaluations_used`、`rejected_suggestions`、`stop_reason`、`stop_detail`、
`recommendation`、`final_state`、`error`。

best-so-far 与平台最优选择使用同一规则：方向归一化目标值最大；相同时基线参数值优先，其次候选顺序靠前。

## 9. Evidence / 证据

每次运行导出：`algorithm-metadata.json`、`parameter-space.json`、`algorithm-config.json`
（超参数、预算、`algorithm_config_hash`、`parameter_space_hash`、`source_revision`）、`algorithm-trace.json`、
`evidence-descriptor.json`，以及 Day 6 的优化证据。

`algorithm_config_hash = sha256(canonical_json({algorithm_id, algorithm_version, sdk_version,
hyperparameters, max_evaluations}))`；`source_revision = {"type": "git_commit", "value": <commit>}`。

`EvidenceDescriptor`：

- `verification_status`：`not_verified` / `platform_checks_passed` / `platform_checks_failed` /
  `independently_verified` / `independent_verification_failed`；`verified` 仅对 `independently_verified` 为真。
- `acceptance_eligible` 在 Day 7 恒为 `false`，并列出原因（`simulation_only`、`not_measured`、`not_huawei_data`、
  `unconfirmed_acceptance_kpi`，以及 `engineering_baseline` / `integration_demo_algorithm` 等）。
- **Verification ≠ Acceptance**：独立复核 PASS 只说明产物自洽、可复算，不代表满足任何验收指标。

独立复核：`scripts/verify_algorithm_run.py OPT-XXXX`（不 import `src/` 下任何模块；
对 Grid Search 与 Research Demo 独立重放决策序列）。

## 10. Versioning / 版本

- `ALGORITHM_SDK_VERSION`：接口不兼容变更时递增；每次运行记录 `sdk_version`。
- 算法 `version`：算法逻辑或默认超参数变化时递增（语义化版本）。
- 每次运行记录 `algorithm_config_hash`、`parameter_space_hash`、`source`、`source_revision`（git commit），
  保证能定位到产生结果的确切代码与配置。

## 11. Out of scope (Day 7) / 不在范围内

动态插件加载、上传代码、远程执行、沙箱、多目标、约束求解、学习优化器、验收判定。
