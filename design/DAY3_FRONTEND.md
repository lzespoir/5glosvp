# Day 3 — Web Frontend V0.1 / 前端平台 V0.1

> 项目：5G 网络学习优化仿真验证平台
> Project: 5G Learning Optimization Simulation & Validation Platform
>
> 当前基线 Commit：`84bf3ff`
>
> 阶段：Day 3 — Frontend Platform
>
> **这是开发执行任务书。Cursor Auto 应直接完成代码、运行、测试和 Git Commit，不要只输出设计方案。**

---

# 0. Day 3 唯一目标

把 Day 2 已经完成的：

```text
FastAPI
   ↓
Experiment API
   ↓
ExperimentService
   ↓
SionnaBackend
   ↓
Sionna RT
```

变成用户真正可以操作的平台：

```text
Browser
浏览器
   ↓
React Frontend
前端平台
   ↓
FastAPI
   ↓
Experiment API
   ↓
Sionna RT
```

最终用户必须能够在浏览器中完成：

```text
打开平台
   ↓
查看平台状态
   ↓
查看仿真场景
   ↓
点击“运行实验”
   ↓
等待 Sionna 完成
   ↓
看到实验成功
   ↓
查看 Radio Map
   ↓
查看 RSS / SINR / Path Gain
   ↓
查看运行时间
   ↓
查看数据来源
   ↓
查看实验产物
```

这就是 Day 3 Definition of Success。

---

# 1. 产品定位

前端不要做成普通 CRUD 后台。

视觉定位：

> **5G Network Digital Sandbox**
> **5G 网络数字沙盘**

关键词：

```text
科研
Research

网络
Network

仿真
Simulation

优化
Optimization

实验
Experiment

验证
Validation

证据
Evidence
```

整体应该让人第一眼意识到：

> 这是一个网络优化科研实验平台，而不是通用管理后台。

---

# 2. 语言策略

默认：

```text
中文为主
Chinese First
```

英文作为：

```text
技术术语
副标题
辅助说明
```

例如：

```text
实验中心
Experiment Center
```

```text
无线电地图
Radio Map
```

```text
仿真生成
Simulation Generated
```

```text
实验详情
Experiment Detail
```

不要整个 UI 全英文。

---

# 3. 技术栈冻结

使用：

```text
React
TypeScript
Vite
Ant Design
ECharts
TanStack Query
React Router
Axios
```

允许使用：

```text
dayjs
```

不要增加大型 UI 框架。

禁止：

```text
Next.js
Vue
Angular
Electron
Tailwind 重写整个 UI
Three.js
MapLibre
Deck.gl
Redux
MobX
```

Day 3 不需要。

---

# 4. 不修改后端架构

当前后端已经通过 Day 2 验收。

原则：

```text
Frontend
   ↓
HTTP API
   ↓
Existing Backend
```

禁止前端：

```text
直接读取 data/
直接读取 reference/
直接读取 outputs/
直接 import Python
直接调用 Sionna
```

所有运行数据必须来自 HTTP API。

---

# 5. 不修 Day 2 非阻塞技术债

以下问题记录即可：

```text
Soft Timeout
单 Worker

Experiment 状态机未强制 transition matrix

FileExperimentStore 全量扫描

无 Crash Recovery
```

Day 3 不解决。

不要因为这些问题引入：

```text
Celery
Redis
PostgreSQL
Worker Process
```

---

# 6. 目录结构

在仓库增加：

```text
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
│
└── src/
    ├── main.tsx
    ├── App.tsx
    │
    ├── api/
    │   ├── client.ts
    │   ├── health.ts
    │   ├── backends.ts
    │   ├── scenarios.ts
    │   └── experiments.ts
    │
    ├── types/
    │   ├── common.ts
    │   ├── backend.ts
    │   ├── scenario.ts
    │   └── experiment.ts
    │
    ├── layouts/
    │   └── PlatformLayout.tsx
    │
    ├── pages/
    │   ├── Overview/
    │   ├── Scenarios/
    │   ├── Experiments/
    │   ├── ExperimentDetail/
    │   └── ComingSoon/
    │
    ├── components/
    │   ├── PageHeader/
    │   ├── MetricCard/
    │   ├── StatusTag/
    │   ├── ProvenanceTag/
    │   ├── EmptyMetric/
    │   ├── RadioMap/
    │   ├── RuntimePanel/
    │   └── ErrorState/
    │
    └── utils/
        ├── format.ts
        └── status.ts
```

允许根据实际工程合理调整。

但不要过度拆分。

---

# 7. 页面路由

必须实现：

```text
/
```

平台概览：

```text
/overview
```

场景中心：

```text
/scenarios
```

实验中心：

```text
/experiments
```

实验详情：

```text
/experiments/:experimentId
```

预留：

```text
/algorithms
```

和：

```text
/acceptance
```

但只显示 Coming Soon。

---

# 8. 主导航

左侧导航：

```text
平台概览
Overview

场景中心
Scenario Center

算法中心
Algorithm Center

实验中心
Experiment Center

验收中心
Acceptance Center
```

其中：

```text
算法中心
验收中心
```

当前显示：

```text
即将开放
Coming Soon
```

禁止伪造内容填充页面。

---

# 9. Platform Layout

整体布局：

```text
┌──────────────────────────────────────────────────────────┐
│ LOGO  5G网络学习优化仿真验证平台             Backend ●  │
│       Learning Optimization Validation Platform          │
├─────────────┬────────────────────────────────────────────┤
│             │                                            │
│ 平台概览     │                                            │
│ Overview    │                                            │
│             │                                            │
│ 场景中心     │               PAGE                         │
│ Scenario    │                                            │
│             │                                            │
│ 算法中心     │                                            │
│ Algorithm   │                                            │
│             │                                            │
│ 实验中心     │                                            │
│ Experiment  │                                            │
│             │                                            │
│ 验收中心     │                                            │
│ Acceptance  │                                            │
│             │                                            │
├─────────────┴────────────────────────────────────────────┤
│ V0.1 · Simulation Generated Data                         │
└──────────────────────────────────────────────────────────┘
```

---

# 10. Header

Header 左侧：

```text
5G网络学习优化仿真验证平台
5G Learning Optimization Simulation & Validation Platform
```

右侧：

Backend 状态。

例如：

```text
● Sionna RT Ready
```

或者：

```text
● Sionna RT Unavailable
```

必须来自：

```text
GET /api/v1/backends
```

不能硬编码。

---

# 11. 平台概览 / Overview

这是演示入口。

页面顶部：

```text
平台概览
Platform Overview
```

副标题：

```text
面向5G网络学习优化算法的仿真、实验与验证平台
Simulation, experimentation and validation for
5G network learning optimization
```

---

# 12. Overview KPI Cards

第一排：

```text
仿真后端
Simulation Backend

场景
Scenarios

实验
Experiments

最近实验
Latest Experiment
```

例如：

```text
┌────────────────┐
│ 仿真后端        │
│ Sionna RT      │
│ ● Ready        │
└────────────────┘

┌────────────────┐
│ 场景            │
│ 1              │
│ Scenario       │
└────────────────┘

┌────────────────┐
│ 实验            │
│ 12             │
│ Experiments    │
└────────────────┘

┌────────────────┐
│ 最近实验        │
│ SUCCEEDED      │
│ 0.669 s        │
└────────────────┘
```

所有数字来自 API。

禁止硬编码。

---

# 13. Overview 最新实验

如果存在实验：

显示：

```text
最近实验
Latest Experiment
```

包含：

```text
Experiment ID

Scenario

Backend

Status

Created Time

Runtime
```

并提供：

```text
查看实验详情 →
View Experiment
```

---

# 14. Overview Radio Map

如果最近一次成功实验存在：

显示：

```text
最新无线电地图
Latest Radio Map
```

直接通过：

```text
/api/v1/experiments/{id}/artifacts/radio_map.png
```

加载。

不要：

```text
import reference/radio_map.png
```

---

# 15. Radio Map 展示原则

Radio Map 必须：

```text
保持原始宽高比

不能拉伸

支持点击放大

显示 Experiment ID

显示 Scenario

显示 Generated 标签
```

标签：

```text
仿真生成
Simulation Generated
```

---

# 16. Overview 最近实验表格

显示最近 5 条：

| 实验 | 场景 | 后端 | 状态 | 仿真时间 | 创建时间 |
| -- | -- | -- | -- | ---- | ---- |

点击整行进入详情。

---

# 17. 场景中心 / Scenario Center

路由：

```text
/scenarios
```

标题：

```text
场景中心
Scenario Center
```

说明：

```text
管理和运行用于5G网络优化验证的仿真场景
Manage simulation scenarios for 5G network
optimization validation
```

---

# 18. Scenario Card

每个 Scenario 使用 Card。

至少显示：

```text
场景名称

Scenario ID

Backend

Scene

Frequency

Bandwidth

Random Seed

Data Type
```

例如：

```text
Sionna RT 内置场景技术验证

SIONNA-DEMO-001

Backend
Sionna RT

Carrier Frequency
3.5 GHz

Bandwidth
100 MHz

Data Type
仿真生成
Simulation Generated
```

真实值从 API 获取。

---

# 19. Scenario 参数

展开：

```text
场景参数
Scenario Parameters
```

显示：

```text
Transmitters

TX Position

TX Power

Radio Map Cell Size

Radio Map Metric

Random Seed
```

如果 API 没返回某字段：

显示：

```text
—
```

不要自己补。

---

# 20. 运行实验

Scenario Card 右上：

```text
运行实验
Run Experiment
```

点击弹出确认 Modal：

```text
运行仿真实验

场景：
SIONNA-DEMO-001

后端：
Sionna RT

数据类型：
仿真生成 / Simulation Generated
```

按钮：

```text
取消

开始运行
```

---

# 21. 创建 Experiment

调用：

```text
POST /api/v1/experiments
```

Request 必须符合真实 OpenAPI Contract。

不要根据本文档猜字段。

**Cursor 必须先检查 `/openapi.json` 或后端 Pydantic Schema。**

---

# 22. Experiment Loading

运行过程中：

按钮：

```text
运行中...
Running...
```

禁用重复点击。

显示：

```text
正在执行 Sionna RT 仿真
Running Sionna RT simulation...
```

不要伪造进度：

```text
32%
68%
95%
```

因为当前 API 没有真实 progress。

可以使用：

```text
Spin
```

或 indeterminate progress。

---

# 23. Experiment Success

成功后：

```text
实验运行成功
Experiment completed successfully
```

自动跳转：

```text
/experiments/{experimentId}
```

---

# 24. Experiment Failed

如果 HTTP 成功但：

```text
status = failed
```

必须识别为实验失败。

显示：

```text
实验执行失败
Experiment Failed
```

并展示：

```text
error.code
error.message
```

不要把：

```text
HTTP 201
```

理解成：

```text
Simulation Success
```

这是硬性要求。

---

# 25. 实验中心 / Experiment Center

路由：

```text
/experiments
```

标题：

```text
实验中心
Experiment Center
```

---

# 26. Experiment Table

至少：

| 实验编号 | 场景 | 后端 | 状态 | 仿真耗时 | 总耗时 | 创建时间 |
| ---- | -- | -- | -- | ---- | --- | ---- |

状态使用 Tag：

```text
CREATED
QUEUED
RUNNING
SUCCEEDED
FAILED
```

---

# 27. 状态中文

显示：

```text
created
已创建

queued
排队中

running
运行中

succeeded
成功

failed
失败
```

英文可以作为 Tooltip 或副文字。

---

# 28. 状态颜色

允许使用 Ant Design 语义颜色：

```text
created   neutral

queued    processing

running   processing

succeeded success

failed    error
```

不要自己建立复杂 Design System。

---

# 29. Pagination

使用后端：

```text
limit
offset
```

默认：

```text
pageSize = 20
```

翻页必须真正重新请求 API。

---

# 30. Experiment Detail

这是 Day 3 最重要页面。

路由：

```text
/experiments/:experimentId
```

顶部：

```text
实验详情
Experiment Detail
```

下面：

```text
EXP-34F6F148
```

以及 Status Tag。

---

# 31. Detail 页面结构

建议：

```text
┌───────────────────────────────────────────────┐
│ EXP-XXXXXXXX                [实验成功]         │
│ Scenario · Backend · Created Time             │
├───────────────────────────────────────────────┤
│                                               │
│        Radio Map / 无线电地图                  │
│                                               │
│                 IMAGE                         │
│                                               │
├───────────────────────────────────────────────┤
│ RSS          SINR        Path Gain   Runtime  │
├───────────────────────────────────────────────┤
│ Simulation Information                        │
├───────────────────────────────────────────────┤
│ Data Provenance                               │
├───────────────────────────────────────────────┤
│ Experiment Timeline                           │
├───────────────────────────────────────────────┤
│ Artifacts                                     │
└───────────────────────────────────────────────┘
```

---

# 32. Radio Map 为视觉主角

成功实验：

Radio Map 至少占页面首屏：

```text
40%–60%
```

视觉面积。

不要把它缩成一个小 Thumbnail。

---

# 33. Metrics

根据 API **真实存在的 metrics** 动态显示。

当前可能包括：

```text
RSS

SINR

Path Gain

Coverage Ratio
```

具体字段以真实 result.json / API 为准。

---

# 34. Metric Card

例如：

```text
RSS

Mean
-62.9 dBm

Range
-118.0 ~ -35.5 dBm
```

具体数字从 API 获取。

不要使用本文档示例数字。

---

# 35. Coverage Ratio

如果 API 返回：

```text
coverage_ratio
```

显示：

```text
Radio Map Coverage
无线电地图覆盖比例
```

不要显示成：

```text
5G Network Coverage
5G网络覆盖率
```

更不能称为：

```text
验收覆盖率
```

---

# 36. 尚未实现 KPI

页面必须有：

```text
系统级 KPI
System-level KPI
```

显示：

```text
网络吞吐率
Network Throughput

—
尚未接入系统级模型
System-level model not connected
```

以及：

```text
边缘用户速率
Edge User Rate

—
验收口径待冻结
Acceptance definition TBD
```

以及：

```text
RSRP

—
当前 Radio Map 提供 RSS，
不等同于 RSRP
```

这是故意的。

不要隐藏。

---

# 37. 禁止伪造 KPI

绝对禁止前端生成：

```text
Throughput +10%

Edge Rate +20%

Optimization Speed +100%
```

这些是项目最终目标，不是当前实验结果。

当前没有真实结果：

就显示：

```text
—
```

---

# 38. Runtime Panel

显示：

```text
运行时间
Runtime
```

包含：

```text
场景加载
Scene Load

仿真计算
Simulation

产物导出
Artifact Export

总耗时
Total
```

只显示 API 中真实存在的字段。

---

# 39. Provenance Panel

必须做。

标题：

```text
数据来源
Data Provenance
```

显示：

```text
数据类型

仿真生成
Simulation Generated
```

```text
Simulation Engine
Sionna RT
```

```text
Measured Data
No
```

以及版本：

```text
Sionna RT 2.1.0
```

如果 API 有。

---

# 40. Provenance Warning

显示轻量 Alert：

```text
当前结果由 Sionna RT 仿真生成，
不属于华为实测数据或运营商现网数据，
不可作为最终项目验收实测证据。
```

不要用危险红色大警告。

用：

```text
info
```

即可。

---

# 41. Experiment Timeline

如果 Experiment API 返回：

```text
status_history
```

展示：

```text
已创建
Created

↓

排队中
Queued

↓

运行中
Running

↓

成功
Succeeded
```

附真实 timestamp。

失败则：

```text
↓

失败
Failed
```

---

# 42. Artifact Panel

列出：

```text
config.yaml

result.json

metadata.json

radio_map.npz

radio_map.png

run.log
```

具体以 API 返回为准。

---

# 43. Artifact 操作

PNG：

```text
查看
View
```

JSON/YAML/log：

```text
打开
Open
```

NPZ：

```text
下载
Download
```

Day 3 不做浏览器解析 NPZ。

---

# 44. Error State

所有页面必须处理：

```text
Loading

Empty

Error
```

不要出现：

```text
Cannot read properties of undefined
```

给用户。

---

# 45. Backend Unavailable

如果：

```text
Sionna RT available = false
```

Scenario Run Button 禁用。

显示：

```text
当前仿真后端不可用

Sionna RT backend is unavailable.
Please check backend environment.
```

---

# 46. FakeBackend 开发模式

如果后端：

```text
TESTING=true
```

并提供 FakeBackend：

前端允许运行。

但页面顶部必须明确：

```text
开发测试模式
Development Test Mode
```

并且 Fake 数据显示：

```text
测试夹具
Test Fixture
```

不能显示：

```text
Simulation Generated
```

---

# 47. Test Fixture 视觉区分

对于：

```text
source_type = test_fixture
```

显示：

```text
TEST FIXTURE
测试数据
```

不要：

```text
Measured
Simulation
```

---

# 48. API Client

统一：

```text
frontend/src/api/client.ts
```

配置：

```text
VITE_API_BASE_URL
```

例如：

```text
http://127.0.0.1:8000/api/v1
```

不要在多个组件中硬编码：

```text
http://localhost:8000
```

---

# 49. TanStack Query

用于：

```text
health

backends

scenarios

experiments

experiment detail
```

Mutation：

```text
create experiment
```

成功后：

```text
invalidateQueries
```

并跳转 Detail。

---

# 50. TypeScript

禁止大量：

```typescript
any
```

API 类型必须建立：

```text
Backend

Scenario

Experiment

Artifact

Metric

Provenance
```

如果 OpenAPI 实际字段与文档不同：

以 API 为准。

---

# 51. API Contract First

Cursor 在写 TypeScript 类型之前必须：

```text
读取后端 Pydantic Schema
或
读取 /openapi.json
```

禁止根据本任务书中的示例 JSON 猜 API。

---

# 52. Responsive

主要目标：

```text
Desktop
1920×1080
```

因为最终项目汇报大概率投屏。

同时：

```text
1366×768
```

必须基本可用。

移动端：

不是 Day 3 重点。

---

# 53. 演示分辨率

重点检查：

```text
1920 × 1080
```

要求：

* Sidebar 不过宽；
* Radio Map 足够大；
* KPI 第一屏可见；
* 不需要大量滚动才能看到结果。

---

# 54. Loading Skeleton

Overview：

使用 Skeleton。

Experiment Table：

使用 Table loading。

Radio Map：

使用 Spin/Skeleton。

不要让页面加载时大面积跳动。

---

# 55. Empty State

第一次运行平台时可能：

```text
0 Experiments
```

显示：

```text
暂无实验

选择一个仿真场景，
开始第一次 Sionna RT 实验。

[ 前往场景中心 ]
```

不要显示空白表格。

---

# 56. Failed Experiment Detail

即使 Experiment failed：

Detail 页面仍然必须可以打开。

显示：

```text
实验失败
Experiment Failed
```

并保留：

```text
Scenario
Backend
Timeline
Error
Existing Artifacts
```

这对未来证据链非常重要。

---

# 57. Visual Style

整体：

```text
Clean
Technical
Scientific
Professional
```

不要：

```text
赛博朋克

霓虹蓝满屏

大量发光效果

黑客终端风

过度渐变

巨大动画
```

科研验收平台应可信，而不是游戏 UI。

---

# 58. Accent

允许少量：

```text
5G / Network / Signal
```

视觉元素。

但不要下载大量装饰图片。

优先：

```text
数据
图表
Radio Map
状态
```

作为视觉主体。

---

# 59. Logo

Day 3 不需要正式 Logo。

可以使用简单：

```text
5G
```

Icon + 平台名称。

不要浪费时间设计品牌。

---

# 60. ECharts 使用范围

Day 3 只做一个有意义的小图即可：

```text
Recent Experiment Runtime
最近实验运行耗时
```

例如最近 10 次：

```text
Experiment
    ↓
Total Runtime
```

如果实验不足：

自然显示已有数据。

不要生成假历史数据填图。

---

# 61. 图表语言

图表默认英文：

```text
Runtime (s)
Experiment
```

页面标题仍中文
