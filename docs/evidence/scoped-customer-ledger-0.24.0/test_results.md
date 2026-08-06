# 测试结果

更新日：2026-08-06

| 测试 | 结果 |
| --- | --- |
| CAG pytest | 151 passed，3 skipped |
| Coverage | 85.02%，门槛 85% |
| Alembic Round Trip | 合格 |
| PostgreSQL Head | `20260806_0025 (head)` |
| Idempotency | 同 Key 同 Body 重放，同 Key 异 Body 返回 409 |
| Scope | 一意、未发现、多候选、Code 边界测试合格 |
| Evidence | Document、Document Version、Chunk、URI、位置、Excerpt 合格 |
| Conflict | 物理 Conflict ID 和双方 Candidate ID 合格 |
| 时间适用性 | UTC 规范化、过去与当前 Block 选择、排除理由合格 |
| Processor | Active、Superseded、失败保留旧 Active 合格 |
| 永久历史 | 原资料变化和消失后旧 Document、Chunk、Version 保留 |
| 正式 Health | API ready，Redis connected，PostgreSQL 与 pgvector ready |
| 正式筑波大学 Scan | `REVIEW_REQUIRED`，`EXTRACTION_PARTIAL`，Manifest 296 |
| 正式再分析 | 38 analyzed，69 failed，189 excluded，Coverage 0.35514，Conflict ID 2 件 |
| 问题中心重处理 | 显式 Reopen 和失败评估创建新 Queue Item，竞态回归合格 |
| Browser | 系统管理、扫描概要、Evidence、Conflict 和 Applied 状态合格 |
| Console | OneOps 应用 Warning 和 Error 为 0 |

首次正式扫描因 30 秒全局期限失败。第二次因单文件模型 ReadTimeout 被错误提升为 Task 失败。修复独立 900 秒 Task 期限、15 秒文件期限和文件级失败收敛后，第三次从起点重跑并完成聚合。
