# Research Demo Optimizer（自适应局部搜索）

> **Integration Demo / 接入验证算法 · Not Project Research Deliverable · learning_algorithm = false**
>
> 这个算法只用来证明平台的 suggest → evaluate → observe 链路可用，并作为科研团队接入算法的模板。
> 它不是项目科研成果，不是学习优化算法，也不用于验收；不要求优于 Grid Search。

| 字段 | 值 |
|---|---|
| algorithm_id | `research_demo_optimizer` |
| version | `0.1.0` |
| category | `research_demo` |
| status | `experimental` |
| 参数类型 | 1 个 `continuous` 参数（例如 `scheduler_beta`） |
| 问题类型 | `system` |

## 规则

一维连续参数 `x ∈ [lower, upper]`（开区间端点向内收缩 `min_step`），所有建议值舍入到 6 位小数：

1. **start**：从基线值（或 `start_point = center` 时从区间中点）出发；若该点已由平台评价（基线），直接进入 explore。
2. **explore**：评价 `x − step` 与 `x + step`（裁剪到区间内，去掉与 `x` 相同或重复的点）。
   若更优者严格优于 `x` → 移动到该点、记住方向，进入 extend；否则 `step *= shrink_factor`。
3. **extend**：沿同一方向再走一步 `x + direction·step`；更优则继续 extend，否则缩小步长并回到 explore。
4. 已评价过的点直接用记忆决策，不再请求评价。
5. **停止**：`step < min_step` → `converged`；完成 `max_iterations` 轮 → `max_iterations`；
   评价预算由平台执行 → `budget_exhausted`。

每一步都依据上一轮的目标值反馈决定下一个参数，这正是它用于验证 “迭代反馈链路” 的原因；
但它没有从数据中学习任何模型。

## 超参数

| id | 类型 | 默认 | 范围 |
|---|---|---|---|
| `initial_step` | float | 0.2 | (0, 1] |
| `min_step` | float | 0.05 | (0, 1]，且 ≤ initial_step |
| `shrink_factor` | float | 0.5 | (0, 1) |
| `max_iterations` | integer | 8 | [1, 50] |
| `start_point` | categorical | `baseline` | `baseline` / `center` |

## 代码结构（`algorithm.py`）

| 部分 | 作用 |
|---|---|
| `_METADATA` | 身份、能力声明（只有 continuous）、超参数 schema |
| `validate_problem` | `min_step ≤ initial_step`；连续参数必须有 bounds |
| `initialize` | 读取区间 / 超参数；把基线放入记忆；确定起点 |
| `suggest` → `_next_points` | 生成下一批未评价的点 |
| `observe` → `_decide` | 记录结果，移动 / 缩小步长 / 停止 |
| `finalize` | 推荐当前 incumbent |
| `state_metadata` | 每轮写入 trace 的 mode / incumbent / step / direction / last_decision |

## 独立复核

`scripts/verify_algorithm_run.py` 内有一份不依赖本文件的规则实现：它用记录的目标值逐轮重放，
要求建议序列、停止原因与推荐值和 trace 完全一致。
