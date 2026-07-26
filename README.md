# Codex/ChatGPT Agent Gateway

Agent Gateway 让网站、内部平台和自动化系统通过自然语言 Prompt 调用本机已经使用 ChatGPT 订阅登录的 Codex。Gateway 负责项目隔离、任务路由、结构化事件、审批、审计和结果保存。

## 当前版本

当前版本为 `0.1.0`，对应规格中的 Phase 1。

已实现：

* FastAPI 服务骨架。
* SQLAlchemy 数据模型和 Alembic 迁移。
* Fake Agent Runtime。
* 创建任务、查询任务和 SSE 事件读取。
* Docker Compose 中的 Gateway、PostgreSQL 和 Redis。
* 不消耗 Codex 或 OpenAI 配额的测试。

规划中：

* Phase 2 工作区、项目配置加载、完整事件流和前端页面。
* Phase 3 本地 Codex app-server 运行时。
* Phase 4 Skill、Runtime Profile 和工具策略。
* Phase 5 审批、Git diff 和 Artifact。
* Phase 6 MCP 与外部系统工具。
* Phase 7 Skill 改进提案和评测闭环。

完整状态见 [需求矩阵](docs/requirements-matrix.md)。

## 运行时边界

本项目使用本机 Codex 登录状态。用户先通过 `codex login` 完成 ChatGPT 登录，Gateway 再调用本地 Codex 进程。`OPENAI_API_KEY` 不属于本项目的默认运行架构。

目标运行时：

1. `codex app-server` 提供线程、审批和流式事件的深度集成。
2. `codex exec --json` 提供机器可读的兼容执行路径。
3. `FakeAgentRuntime` 用于测试和无配额验证。

当前本机调查记录见 [本地 Codex 运行时 ADR](docs/adr/0001-local-codex-runtime.md)。

## 本地启动

进入后端目录并安装开发依赖：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

启动服务：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

服务默认地址为 `http://127.0.0.1:8000`，OpenAPI 地址为 `http://127.0.0.1:8000/docs`。

## Docker Compose

复制示例配置：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

检查健康状态：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

## 测试

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

测试默认使用临时 SQLite 数据库和 Fake Runtime，不连接生产系统。

## 文档

* [系统架构](docs/architecture.md)
* [API](docs/api.md)
* [安全](docs/security.md)
* [部署](docs/deployment.md)
* [版本策略](docs/versioning.md)
* [需求矩阵](docs/requirements-matrix.md)
* [ADR](docs/adr)
