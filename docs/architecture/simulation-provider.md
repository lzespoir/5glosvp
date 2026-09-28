# 仿真提供方架构 / Simulation Provider Architecture

平台拥有统一领域模型、KPI 定义与实验记录；具体仿真器只是可替换的 Provider。

```text
Frontend  ──(按 capability 展示，不按后端 ID 判断)──►  API  (/api/v1/…)
                                                         │
             ┌───────────────────────────────────────────┼─────────────────────────────┐
             ▼                                           ▼                             ▼
   ExperimentService (传播)              SystemExperimentService (系统级)     OptimizationService
             │                                           │                             │
   BackendRegistry                        SystemBackendRegistry ──► KPI Registry (evaluation.kpi)
             │                                           │
   SimulationBackend (ABC)                SystemSimulationBackend (ABC)
      ├─ SionnaBackend  (sionna_rt)          ├─ SionnaSystemBackend (sionna_system)
      └─ FakeBackend    (test_fixture)       ├─ FakeSystemBackend   (fake_system, test_fixture)
                                             └─ (future) FastSystemBackend / MATLAB / ns-3 / external
```

## 规则 / Rules

1. **只有适配器 import 引擎**：`simulation/backends/sionna_backend.py` 与 `simulation/backends/sionna_system_backend.py`
   是仅有的可以 import Sionna / Mitsuba / Dr.Jit / PyTorch 的平台模块（`tests/test_sionna_backend.py::test_only_adapter_imports_sionna`）。
   `evaluation/` 与 `system_simulation/` 不得 import 任何引擎或 `simulation.backends`
   （`tests/test_system_backends.py::test_domain_layers_do_not_import_engines`）。
2. **能力声明 / Capabilities**：每个系统级后端通过 `SystemBackendDescriptor.capabilities` 声明能力
   （`propagation`、`radio_map`、`system_simulation`、`scheduling`、`link_adaptation`、`ue_metrics`、`throughput`）。
   未知能力在注册时即报错。服务在运行前检查 `system_simulation` 能力，否则返回 `SYSTEM_CAPABILITY_NOT_SUPPORTED`。
3. **结果来源 / Model type**：`sionna_sys`（Sionna Simulation Generated）、`engineering_approximation`
   （Fast Engineering Approximation）、`test_fixture`（TEST FIXTURE）。前端用不同颜色明确区分；
   `test_fixture` 结果永远不能作为参考证据。
4. **统一结果 / Canonical result**：后端返回 `SystemRunOutput(result: SystemSimulationResult, slot_trace)`，
   不包含任何引擎对象；KPI 由 `KpiRegistry` 在服务层计算后写回。
5. **装配点**：`api/main.py` 是唯一选择具体后端的位置（`default_registry`、`default_system_registry`）；
   `TESTING=true` 时才注册 Fake 后端。
6. **新增 Provider**：实现 `SystemSimulationBackend`（`health_check`、`run`），在 `default_system_registry` 注册描述符，
   无需修改服务、API、KPI 或前端。

## API

| Method | Path | 说明 |
|---|---|---|
| GET | `/system-backends?capability=` | 系统级后端、能力、可用性、结果来源 |
| GET | `/system-scenarios`、`/system-scenarios/{id}` | 系统级场景 |
| GET | `/kpis` | 冻结的 KPI 定义 |
| POST | `/system-experiments` | 创建并同步运行（失败也返回 201 + status=failed） |
| GET | `/system-experiments`、`/system-experiments/{id}` | 列表 / 详情 |
| GET | `/system-experiments/{id}/artifacts/{name}` | 产物 |

错误码：`SYSTEM_BACKEND_NOT_FOUND`、`SYSTEM_CAPABILITY_NOT_SUPPORTED`、`SYSTEM_BACKEND_UNAVAILABLE`、
`SYSTEM_SCENARIO_NOT_FOUND`、`SYSTEM_EXPERIMENT_NOT_FOUND`、`INVALID_SYSTEM_SCENARIO`；
持久化在失败实验中的：`SYSTEM_SIMULATION_FAILED`、`INVALID_SYSTEM_SCENARIO`、`NO_UE_RESULTS`、`KPI_CALCULATION_FAILED`、`ARTIFACT_EXPORT_FAILED`。
