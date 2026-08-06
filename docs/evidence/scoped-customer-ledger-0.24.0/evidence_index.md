# 证据索引

| ID | 结论 | 证据 | 状态 |
| --- | --- | --- | --- |
| C1 | CAG 全量测试与 Coverage | `test_results.md` | 合格 |
| C2 | Alembic 到目标 Head | `20260806_0025 (head)` | 合格 |
| C3 | 正式 Scope 一意解析 | Scope `6ea2f756-ac3e-4ae9-b154-8c6e2ace8ea3`，Prefix `つ_0408_筑波大学/` | 合格 |
| C4 | 全文件 Manifest | Task `446f445d-90b5-4f24-ad7e-84532f2195d1`，296 项 | 合格 |
| C5 | 文件级部分成功 | 37 analyzed，70 failed，189 excluded，Coverage 0.345794 | 合格 |
| C6 | OneOps 正式 Scan | Scan `e109f2ae-a3a2-4023-bb40-3fad9a95a45e` | 合格 |
| C6A | 正式再分析与 Conflict ID | Task `b411647f...`，Conflict ID 2 件 | 合格 |
| C7 | 版本与历史 | Document、Processing、Block、Applicability 模型与回归测试 | 合格 |
| C8 | Browser 与 Console | OneOps 四份业务截图，应用 Console Warning 和 Error 为 0 | 合格 |
| C9 | Candidate Apply | `f6e0805d...`，Applied Record `ORGANIZATION:2`，成功审计 `b7531332...` | 合格 |
| C10 | 问题中心重处理竞态 | Fresh Queue Item 回归测试与 151 项全量 pytest | 合格 |
