# 証拠索引

| 証拠 | 内容 | 状態 |
|---|---|---|
| `backend/app/knowledge/service.py` | active ingestion を持つ Source の claim 除外 | 実装済み |
| `backend/app/knowledge/scheduler.py` | ingestion 作成有無による実作業判定 | 実装済み |
| `backend/app/api/conversations.py` | Conversation SSE 初期 Session の短命化 | 実装済み |
| `backend/app/api/tasks.py` | Task SSE 初期 Session の短命化 | 実装済み |
| `backend/tests/test_knowledge.py` | queued、running、競合時 idle の専用テスト | 合格 |
| `backend/tests/test_sse_session_lifetime.py` | StreamingResponse 返却前 Session close の専用テスト | 合格 |
| `docker-compose.yml` | PostgreSQL と Redis の `unless-stopped` | 0.28.2 既存差分として確認済み |
| runtime と Browser | リリース後の OneOps 経由受入 | evidence_missing |
