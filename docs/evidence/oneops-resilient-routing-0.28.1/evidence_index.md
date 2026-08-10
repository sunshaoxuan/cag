# 证据索引

| 结论 | 证据 | 状态 |
| --- | --- | --- |
| Conversation 幂等 Replay | `backend/tests/test_conversations_api.py` | 通过 |
| Request Hash 冲突返回 409 | `backend/tests/test_conversations_api.py` | 通过 |
| 并发唯一约束可回读原 Conversation | `backend/tests/test_conversations_api.py` | 通过 |
| Migration 0026 可升级和降级 | `backend/tests/test_migrations.py` | 通过 |
| OneOps Routing v3 可保存并执行 | `backend/tests/test_tasks_api.py` | 通过 |
| CAG 后端全量与覆盖率 | `test_results.md` | 177 passed、3 skipped、85.08% |
