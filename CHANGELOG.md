# Changelog

本文档记录 Agent Gateway 的可发布版本。版本遵循 Semantic Versioning。

## 0.3.0

发布日期：2026-07-27

### Added

* 本机 Codex app-server JSONL 客户端。
* `initialize`、`account/read`、`thread/start` 和 `turn/start` 生命周期。
* ChatGPT 账户类型强制校验。
* Plan、Agent 消息、命令、文件变化、警告和完成事件映射。
* Phase 5 前的审批自动拒绝安全行为。
* 本机订阅运行时启动脚本和 Fake app-server 协议测试。

### Validated

* 本机 `account/read` 返回 ChatGPT 账户类型。
* 真实只读 Codex turn 返回预期文本。
* Gateway HTTP 任务经独立 Git 工作区和 app-server 完成。
* `OPENAI_API_KEY` 仍不属于运行架构。

## 0.2.0

发布日期：2026-07-27

### Added

* YAML 项目注册表和 Project 查询 API。
* Project 与 Task 工作区字段的数据库迁移。
* 每个任务独占的 Git 克隆工作区及提交版本记录。
* `workspace.preparing` 与 `workspace.ready` 事件。
* React 任务控制台、事件时间线与最终报告页面。
* 前端容器和统一 Docker Compose 启动。
* 工作区隔离、项目 API、前端组件和浏览器验收测试。

### Runtime decision

* 真实运行时继续限定为本机已通过 ChatGPT 订阅登录的 Codex。
* Phase 2 使用 Fake Agent Runtime 完成无配额的确定性验收。
* Phase 3 将接入本机 `codex app-server`，不引入 `OPENAI_API_KEY`。

## 0.1.0

发布日期：2026-07-27

### Added

* Phase 1 FastAPI 后端骨架。
* Project、Conversation、Task、TaskEvent 数据模型及首个 Alembic 迁移。
* Fake Agent Runtime 与异步任务执行服务。
* 创建任务、查询任务和 SSE 事件接口。
* 健康检查、Docker Compose、本地与容器运行配置。
* 单元测试、API 集成测试和事件顺序测试。
* 架构、API、安全、部署、版本和 ADR 文档。

### Runtime decision

真实运行时将复用本机通过 ChatGPT 登录的 Codex。目标集成接口为 `codex app-server`，兼容执行接口为 `codex exec --json`。Gateway 不要求 OpenAI Platform API Key。
