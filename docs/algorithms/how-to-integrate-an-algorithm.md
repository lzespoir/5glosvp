# How to Integrate an Algorithm / 如何接入一个优化算法

目标读者：项目科研团队。读完本文，不了解平台内部实现也能接入一个算法。
接口的完整定义见 [algorithm-integration-contract-v0.1.md](algorithm-integration-contract-v0.1.md)。
可直接复制的模板：`src/algorithms/examples/research_demo_optimizer/`（约 260 行）。

---

## 0. 你负责什么，平台负责什么

| 你（算法） | 平台 |
|---|---|
| 决定下一批要评价的参数值 | 场景、冻结信道 / UE / 业务、Sionna 仿真 |
| 根据目标值反馈更新内部状态 | KPI、目标函数、最优选择、公平性检查 |
| 决定何时停止 | 评价预算（强制）、缓存、trace、证据导出 |

你的代码 **不能** import Sionna、KPI 引擎、实验仓库或 `system_optimization`；你只拿到参数与目标值。

## 1. 要实现什么接口？

继承 `algorithms.Algorithm`，实现 7 个方法：

```python
from algorithms import (Algorithm, AlgorithmMetadata, AlgorithmProblem, AlgorithmRecommendation,
                        EvaluationResult, StopReason)

class MyOptimizer(Algorithm):
    @classmethod
    def metadata(cls) -> AlgorithmMetadata: ...                       # 身份 + 能力 + 超参数 schema
    def initialize(self, problem, hyperparameters, incumbents): ...   # 读取参数空间 / 超参数 / 基线
    def suggest(self, max_suggestions) -> list[dict]: ...             # 下一批候选（≤ max_suggestions）
    def observe(self, results: list[EvaluationResult]): ...           # 收到这批候选的评价结果
    def should_stop(self) -> StopReason | None: ...                   # None = 继续
    def finalize(self) -> AlgorithmRecommendation: ...                # 推荐参数（可为 None）
    def state_metadata(self) -> dict: ...                             # 可选：写入 trace 的 JSON 状态
```

可选：`validate_problem(problem, hyperparameters)` 返回额外的 `CompatibilityIssue`
（例如 “min_step 必须 ≤ initial_step”）。

## 2. 输入是什么？

`initialize` 收到：

- `problem.parameter_space.parameters`：每个参数的 `id`、`type`、`bounds` / `choices`、`unit`；
- `problem.objective_direction`：`maximize` / `minimize`；
- `problem.baseline_parameters`：场景当前取值（例如 `{"scheduler_beta": 0.9}`）；
- `problem.max_evaluations`：平台预算（你可以参考，但平台会强制执行）；
- `hyperparameters`：已按你的 schema 校验并补齐默认值的超参数；
- `incumbents`：平台已评价的基线结果（`EvaluationResult`）。

`observe` 收到的每个 `EvaluationResult`：`parameters`、`objective`、`status`、`cache_hit`、
`secondary_metrics`，以及 `score()`（方向归一化后越大越好，失败为 `None`）。

## 3. 输出是什么？

- `suggest` 返回 `[{"scheduler_beta": 0.734}, ...]`：必须覆盖参数空间中的全部参数，值必须合法。
  非法建议会让运行失败（`failed`），不会被静默修正。
- 返回空列表 = 没有更多建议（运行以 `completed` 或你给出的 stop reason 结束）。
- 重复建议是允许的：平台会命中缓存、不重复仿真，但仍消耗预算。
- `finalize` 返回推荐参数；平台另行按统一规则选出最优候选，并记录两者是否一致。

## 4. 怎么声明参数能力？

在 `AlgorithmCapabilities` 中只把真实支持的类型置为 `true`：

```python
capabilities=AlgorithmCapabilities(
    supports_discrete=False, supports_continuous=True, supports_integer=False,
    supports_categorical=False, supports_vector=False, supports_constraints=False,
    supports_multi_objective=False, supports_batch_suggestions=True,
    supports_iterative_feedback=True, supports_auto_configuration=True, max_parameters=1,
)
```

用户选了你不支持的参数类型时，平台在运行前返回 422 `ALGORITHM_PARAMETER_TYPE_NOT_SUPPORTED`，你的代码不会被调用。

## 5. 怎么声明超参数？

```python
hyperparameter_schema=[
    HyperparameterDefinition(id="initial_step", name_zh="初始步长", name_en="Initial Step",
                             type=HyperparameterType.FLOAT, default=0.2,
                             bounds=ParameterBounds(lower=0.0, upper=1.0, lower_inclusive=False)),
    HyperparameterDefinition(id="start_point", name_zh="起点", name_en="Start Point",
                             type=HyperparameterType.CATEGORICAL, default="baseline",
                             choices=["baseline", "center"]),
]
```

- 每个超参数都必须有推荐默认值：前端 “Recommended” 模式直接使用默认值（`auto_configured = true`）。
- 超参数不是网络优化变量，不要把它们放进参数空间。

## 6. 怎么填写元数据？

```python
AlgorithmMetadata(
    algorithm_id="my_optimizer", version="0.1.0", category=AlgorithmCategory.RESEARCH,
    name_zh=..., name_en=..., description_zh=..., description_en=..., purpose_zh=..., purpose_en=...,
    provider="<团队名>", learning_algorithm=False,          # 只有真正基于数据学习才可为 True
    project_research_deliverable=False,                     # 由项目组确认后才可置 True
    acceptance_algorithm=False,                             # Day 7 恒为 False
    capabilities=..., hyperparameter_schema=..., supported_problem_types=["system"],
    source="src/algorithms/<path>/algorithm.py", status=AlgorithmStatus.EXPERIMENTAL,
)
```

## 7. 怎么本地测试？

不需要 Sionna，用假后端即可跑完整链路（数秒）：

```python
from algorithms import default_algorithm_registry
from system_optimization import ParameterSpec
from system_helpers import TEST_PROTOCOL_ID, make_optimization_service   # tests/system_helpers.py

registry = default_algorithm_registry()
registry.register(MyOptimizer)
service = make_optimization_service(tmp_path, algorithms=registry)
record = service.create_run(
    name="local", scenario_id="SYSTEM-TEST-001", algorithm_id="my_optimizer",
    objective_id="NETWORK_THROUGHPUT_MAX_V0_1",
    parameter_space=[ParameterSpec(id="scheduler_beta", type="continuous")],
    benchmark_protocol_id=TEST_PROTOCOL_ID, max_evaluations=6,
)
assert record.status.value == "succeeded", record.error
print(record.algorithm_trace.stop_reason, [c.parameters for c in record.candidates])
```

参考 `tests/test_algorithm_integration.py` 与 `tests/test_algorithms.py`。
假后端输出标记为 `test_fixture`，只用于软件测试，不能作为结果证据。

## 8. 怎么注册？

在 `src/algorithms/registry.py` 的 `default_algorithm_registry()` 中加一行：

```python
registry.register(MyOptimizer)
```

Day 7 只支持仓库内静态注册（代码评审后合入）；不支持上传代码 / 动态插件 / 远程执行。
注册后 `GET /api/v1/algorithms` 与前端 Algorithm Center 会自动列出你的算法。

## 9. 怎么运行？

前端：Optimization Center → New System Optimization → 选择算法 → 设置参数空间 → Algorithm Settings → Run。

API：

```bash
# 先做兼容性检查（不创建运行）
curl -X POST localhost:8000/api/v1/algorithms/my_optimizer/validate -H 'Content-Type: application/json' -d '{
  "objective_id": "NETWORK_THROUGHPUT_MAX_V0_1",
  "parameter_space": {"parameters": [{"id": "scheduler_beta", "type": "continuous", "lower": 0.05, "upper": 0.99}]},
  "evaluation_budget": {"max_evaluations": 8}}'

# 创建运行
curl -X POST localhost:8000/api/v1/system-optimizations -H 'Content-Type: application/json' -d '{
  "name": "my run", "scenario_id": "SYSTEM-DEMO-001", "algorithm_id": "my_optimizer",
  "objective_id": "NETWORK_THROUGHPUT_MAX_V0_1", "benchmark_protocol_id": "SYSTEM_BENCHMARK_V0_1",
  "parameter_space": {"parameters": [{"id": "scheduler_beta", "type": "continuous"}]},
  "algorithm_hyperparameters": {}, "evaluation_budget": {"max_evaluations": 8}}'
```

## 10. 怎么生成证据？

运行成功后平台自动导出到 `data/system_optimizations/OPT-XXXX/artifacts/`：算法元数据、参数空间、算法配置
（含 config hash 与 git commit）、算法 trace、证据描述符，以及候选实验、KPI、公平性报告。

独立复核（不 import 平台代码）：

```bash
python scripts/verify_algorithm_run.py OPT-XXXX --out verification.json
```

它复算 KPI / 目标 / 最优、哈希、预算、缓存与 trace 一致性。对 Grid Search 与 Research Demo 还会独立重放决策序列；
新算法没有重放器时只做通用检查（报告中注明）。

**复核 PASS ≠ 验收 PASS。** 所有 Day 7 证据 `acceptance_eligible = false`。

## 11. 检查清单

- [ ] `metadata()` 能力声明与实现一致，`learning_algorithm` 诚实
- [ ] 所有超参数有默认值与合法范围
- [ ] `suggest` 只返回参数空间内的值；不访问仿真 / KPI / 文件系统
- [ ] `state_metadata()` 可 JSON 序列化，足够解释每一步决策
- [ ] 本地假后端测试通过；registry 注册；`verify_algorithm_run.py` 通过
