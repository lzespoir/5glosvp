# Algorithm SDK Quickstart（算法 SDK 快速开始）

本页面向外部算法作者。Day 10 的 V0.1 是 trusted external Python：算法包必须
是平台工作区内的本地目录，平台不会自动安装 `requirements.txt`，也没有恶意代码
隔离。因此只能接入你信任的代码。

## 1. 包目录

```text
my_optimizer/
├── algorithm.yaml
├── optimizer.py
├── README.md
└── requirements.txt   # 可选，仅供人工审阅；不会自动安装
```

入口类必须继承 `algorithms.Algorithm`，只通过 SDK 生命周期提出候选：

`initialize → suggest → observe → should_stop → finalize`

算法不能读取 Sionna、仿真 backend 或 KPI 实现。平台负责候选校验、评价、约束、
指标、trace、证据和导出。

## 2. 最小清单

`algorithm.yaml` 至少声明 `schema_version: "0.1"`、算法 id/version、SDK 版本、
entrypoint、problem/parameter compatibility、超参数和资源声明。`algorithm_id +
version` 对应的 `package_hash` 必须稳定；同版本换源代码会被拒绝。

## 3. 接入流程

在 Algorithm Center 中依次执行：

`Package → Validate → Smoke Test → Register → Configure → Run → Observe → Compare → Export`

先验证 manifest、导入和 SDK 接口，再用轻量 fake evaluator 做 smoke test；真实运行
时平台使用正式仿真问题和 Day 8 冻结信道。注册后可从 Experiment Workspace 创建实验，
并在 Benchmark Center 进入独立的 Day 10 benchmark。

## 4. 结果边界

通过校验、冒烟和仿真运行只证明“接入链路可用”。它不证明算法正确、不证明论文复现、
不构成现网或实测数据，也不自动获得验收资格。

## 5. API 速查

```text
POST /api/v1/algorithm-packages/validate
POST /api/v1/algorithm-packages/smoke-test
POST /api/v1/algorithm-packages/register
GET  /api/v1/algorithm-packages/{package_id}/detail
POST /api/v1/algorithm-experiments
GET  /api/v1/algorithm-experiments/{run_id}
GET  /api/v1/algorithm-experiments/{run_id}/export
```
