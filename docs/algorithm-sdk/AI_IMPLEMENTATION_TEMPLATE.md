# AI Implementation Template（AI 实现模板）

使用本模板生成外部算法前，先明确边界：AI 生成的实现仍然是 trusted Python，必须
经过人工审阅、manifest 校验、接口校验和 smoke test；不要把“能运行”写成“算法正确”。

## Implementation contract

```python
from algorithms import Algorithm, AlgorithmProblem, AlgorithmRecommendation

class MyOptimizer(Algorithm):
    @classmethod
    def metadata(cls):
        ...  # id/version/sdk/能力/兼容 problem type

    def initialize(self, problem: AlgorithmProblem, hyperparameters, incumbents):
        ...  # 保存问题摘要，不读取平台 backend

    def suggest(self, max_suggestions):
        ...  # 只返回候选参数

    def observe(self, results):
        ...  # 只消费平台 EvaluationResult

    def should_stop(self):
        ...  # 返回 StopReason 或 None

    def finalize(self) -> AlgorithmRecommendation:
        ...
```

## Checklist

- [ ] 不导入 Sionna、backend、实验仓库或 KPI 模块。
- [ ] metadata 与 `algorithm.yaml` 的 id/version/SDK 完全一致。
- [ ] 能力声明只描述真实支持的 parameter types。
- [ ] 超参数有类型、默认值和边界；不依赖隐含 wall-clock 默认值。
- [ ] 不写文件到平台证据目录，不上传数据，不自动安装依赖。
- [ ] `state_metadata()` 仅返回 JSON 可序列化、可审计状态。
- [ ] 通过 Package Validation、Smoke Test 后再注册。
- [ ] 结果声明保持克制：integration evidence ≠ correctness/paper reproduction。
