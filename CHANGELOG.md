# Changelog

本文档记录 Agent Gateway 的可发布版本。版本遵循 Semantic Versioning。

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
