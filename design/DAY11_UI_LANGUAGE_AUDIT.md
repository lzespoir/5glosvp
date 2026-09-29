# Day 11 UI Language Audit

## Scope

审计 Benchmark、Comparison、Runtime、Algorithm 页面。用户可见说明默认中文优先；英文只保留协议字段、算法 ID、版本号、哈希、运行状态枚举和外部论文原名。

## Completed

- Benchmark Center 主标题、协议上下文、表格列、错误提示改为中文优先。
- Benchmark 与用户发起的 Comparison 分离，增加“发起对比分析”入口。
- 新增 Comparison 页面：选择运行记录 → 选择意图 → 兼容性预览 → 用户确认创建。
- 明确不自动生成 winner、ranking、gain 或 A>B 结论；不兼容记录只允许并列查看。
- 请求等待超时文案不再暗示科学运行已经失败。

## Deliberate technical labels

`run_id`、`algorithm_id`、`package_hash`、`channel_hash`、`protocol_id`、`UNVERIFIED/PENDING/VERIFIED/FAILED` and lifecycle state values remain machine-readable for evidence and API interoperability.

## Remaining follow-up

Benchmark Detail and legacy Algorithm Onboarding contain technical provenance labels and bilingual protocol identifiers. They are not translated when translation would hide an exact evidence field; a later language pass may add Chinese descriptions beside those identifiers without changing the values.
