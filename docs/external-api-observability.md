# 外部 API 调用与全链路审计

## 定位

CAG 的主入口是 HTTP API。React 网页使用同一组 API，承担调用测试、运行监控和治理操作。外部业务系统无需打开网页，也无需持有 OpenAI API Key。Codex 运行时继续使用本机 ChatGPT 订阅认证。

当前本机启动脚本监听 `0.0.0.0:8000`，Docker Compose 也将 8000 端口发布到全部主机接口。同一台机器使用 `http://127.0.0.1:8000`，跨机器调用使用 `http://<CAG主机IP>:8000`。当前版本尚未实现调用者认证、项目授权、HTTPS 和分布式限流，网络边界需要由部署环境控制。

## 单次外部调用

```bash
curl -i -X POST "http://127.0.0.1:8000/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -H "X-CAG-Client-ID: erp-integration" \
  -H "X-Request-ID: erp-request-20260727-001" \
  -H "Idempotency-Key: erp-order-1001" \
  -d '{
    "project_id": "cag",
    "prompt": "检查当前项目并给出测试结果",
    "knowledge_mode": "assist",
    "harness_profile": "balanced",
    "learning_mode": "capture"
  }'
```

`X-CAG-Source` 可以显式设置为调用来源。省略时使用 `external_api`。网页测试台固定使用 `test_console`。

响应状态为 HTTP 202。响应头包含：

* `X-CAG-Trace-ID`
* `X-CAG-Idempotent-Replay`
* `Location`

响应正文包含：

```json
{
  "id": "TASK_UUID",
  "trace_id": "TASK_UUID",
  "trigger_source": "external_api",
  "client_id": "erp-integration",
  "client_request_id": "erp-request-20260727-001",
  "request_hash": "SHA256",
  "events_url": "/api/v1/tasks/TASK_UUID/events",
  "audit_url": "/api/v1/audit/tasks/TASK_UUID",
  "status": "queued"
}
```

Trace ID 与 Task 物理 ID 相同，所有查询、事件、审批和审计记录使用同一个稳定标识。

## 幂等规则

`client_id + Idempotency-Key` 唯一标识一次外部调用。

* 重复提交相同请求时返回原 Task，`X-CAG-Idempotent-Replay` 为 `true`。
* 相同幂等键对应不同请求正文时返回 HTTP 409。
* 未提供幂等键时，每次请求都会创建新 Task。

## 单个任务监听

```bash
curl -N \
  "http://127.0.0.1:8000/api/v1/tasks/TASK_UUID/events?after_sequence=0&follow=true"
```

该流只包含一个 Task 的事实事件，序号为 Task 内部序号。断线后使用 `after_sequence` 继续。

## 全局 API 审计监听器

```bash
curl -N \
  "http://127.0.0.1:8000/api/v1/audit/events?after_sequence=0&follow=true"
```

每条 SSE 使用事件名 `audit.event`。正文保留原始动作类型：

```json
{
  "event_id": "EVENT_UUID",
  "trace_id": "TASK_UUID",
  "sequence": 128,
  "task_sequence": 7,
  "type": "command.completed",
  "trigger_source": "external_api",
  "client_id": "erp-integration",
  "client_request_id": "erp-request-20260727-001",
  "project_code": "cag",
  "data": {}
}
```

`sequence` 是 Gateway 全局审计序号，`task_sequence` 是当前 Task 内部序号。全局序号在事件写入数据库时分配，覆盖：

* API 接收和任务状态
* 工作区准备
* 企业知识检索与上下文注入
* Harness 和子 Agent 调度
* Codex 消息与计划
* Tool、Command 和文件动作
* 审批请求与结果
* 测试和验证
* 记忆提取、学习、评测、提升和回滚
* 任务完成、失败和取消

支持查询过滤：

* `trigger_source`
* `client_id`
* `task_id`
* `after_sequence`
* `follow`

客户端可以使用 `Last-Event-ID` 或 `after_sequence` 恢复监听。

## 审计查询

```text
GET /api/v1/audit/tasks
GET /api/v1/audit/tasks/{task_id}
GET /api/v1/audit/events
```

调用列表支持 `trigger_source`、`client_id`、`status` 和 `limit` 过滤。详情返回请求来源、请求哈希、调用元数据、事件数量、最后事件、最终报告和错误。

## 连续对话

外部系统需要多轮上下文时：

1. 调用 `POST /api/v1/conversations` 创建 Conversation。
2. 每轮调用 `POST /api/v1/tasks` 并传入相同 `conversation_id`。
3. 监听 `/api/v1/conversations/{conversation_id}/events`。

CAG 维护 Conversation SSE 和 Codex thread。外部系统不连接 Codex app-server。

## 数据与安全边界

审计记录保存调用来源、客户端 ID、请求 ID、请求正文哈希、允许的请求元数据和所有事实事件。请求头只采集允许字段，不采集认证凭据。Prompt 已存在于 Task 记录中，生产环境需要通过授权控制其查询权限。

本版本完成可用的本机外部 API 和审计链路。跨机器生产发布仍以身份认证、项目授权、HTTPS 和分布式限流为准入条件。
