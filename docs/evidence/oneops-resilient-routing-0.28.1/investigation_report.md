# OneOps Resilient Routing 0.28.1 调查与实现报告

## 目标

保证 OneOps 在共享同一 CAG PostgreSQL 和 Redis Queue 的多个 API Instance 之间重试 Conversation 创建时，不会创建重复 Conversation，并接受 OneOps Task Routing v3 契约。

## 实现

1. Conversation 保存 `client_id`、`idempotency_key` 和规范化请求的 SHA-256 `request_hash`。
2. 同一 Client、Key 和请求返回原 Conversation，并设置 `X-CAG-Idempotent-Replay: true`。
3. 同一 Client 和 Key 对应不同请求时返回 HTTP 409。
4. 并发插入触发唯一约束时回读已提交 Conversation，并按 Request Hash 判定 Replay 或冲突。
5. Task API 接受并保存 `oneops-ai-resilient-routing-v3` 的 `SIMPLE`、`GENERAL` Tier、Model、Effort 和选择原因。

## 边界

CAG 继续作为 Conversation、Task、SSE、历史、Thread Resume 和审计的正式数据源。OneOps 的 Endpoint 重试与 Circuit Breaker 不改变 CAG 的持久化边界。
