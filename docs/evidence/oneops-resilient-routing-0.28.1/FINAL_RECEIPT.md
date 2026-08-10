# 0.28.1 发布回执

## 当前状态

代码、Migration、API 文档、架构文档、需求矩阵、版本和全量自动测试已完成。Commit、Push、Tag、主实例和备用实例运行验证仍在进行。

## 验收清单

| 项目 | 状态 |
| --- | --- |
| 相同 Conversation 请求只创建一个物理记录 | 聚焦测试通过 |
| 不同请求复用 Key 返回 409 | 聚焦测试通过 |
| 并发插入回读原记录 | 聚焦测试通过 |
| OneOps Routing v3 Contract | 聚焦测试通过 |
| 全量 Backend Coverage | 177 passed、3 skipped、85.08% |
| Frontend Test 与 Build | 通过 |
| PostgreSQL 正式 Migration | 未执行 |
| 双 API Instance Health | 未执行 |
| Commit、Push、Tag | 未执行 |

全部项目合格前不判定正式发布完成。
