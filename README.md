# Codex/ChatGPT Agent Gateway

Agent Gateway 让网站、内部平台和自动化系统通过自然语言 Prompt 调用本机已经使用 ChatGPT 订阅登录的 Codex。Gateway 负责项目隔离、任务路由、结构化事件、审批、审计和结果保存。

## 当前版本

当前版本为 `0.11.0`。Gateway 默认监听全部 IPv4 网络接口。5173 端口提供统一的 CAG 可视化管理台，包含 API 测试、调用监控、企业知识、长期记忆和能力治理。企业知识来源保留为持久注册表，可按计划重复扫描，只重新向量化变化内容，并保存每轮同步历史、租约、重试和来源状态。编辑已配置来源时可以按需读取 Windows 凭据库中的密码或令牌，并在当前管理页面显示或复制。管理台通过同源反向代理连接本机订阅认证的 Codex Gateway。外部系统可以通过任务 API 和持续会话 API 调用 CAG。每次任务返回 Trace ID，支持幂等提交，并将知识、Harness、Agent、命令、审批、验证和学习动作写入统一审计 SSE。

CAG 会持久化并通过 SSE 如实转发允许公开的 Agent 消息、计划、命令输出和推理摘要反馈。前端可以独立选择关键、标准或完整反馈，并限制画面显示条数；这些显示设置不会删减后端事件历史。

已实现：

* FastAPI、SQLAlchemy、Alembic 和 Fake Agent Runtime。
* YAML 项目注册表及 Project 查询 API。
* 每个任务独占的 Git 克隆工作区。
* 创建任务、查询任务和 8 类顺序 SSE 事件。
* React 任务控制台与最终报告页面。
* 本机 Codex app-server 适配器。
* ChatGPT 账户类型强制校验。
* app-server 通知到 Gateway 事件与最终报告的转换。
* Conversation 创建、查询和历史 Task API。
* CAG 持有的会话级 SSE、连续序号、心跳和断线续传。
* Conversation 到 Codex thread 的持久映射和多轮恢复。
* 复用同一 CAG Conversation 的连续对话页面。
* `self-improvement-candidate` 任务专属候选输出目录。
* 本机 Ollama、pgvector、混合检索和经过批准的最小知识上下文注入。
* 客户私有知识、产品共享知识和记忆候选治理。
* 内容哈希、来源指纹和路径约束驱动的幂等向量索引。
* 本机目录、认证 UNC、Git、GitLab 和 SVN 的受管知识来源。
* PDF、Office、代码、脚本和配置文件的统一清洗与抽取。
* 采集、清洗、索引和来源记忆保存的可续传 SSE。
* Skill、Tool、Validator 和 Harness Profile 注册表。
* 回放评测、影子运行、金丝雀、Gateway 范围启用和自动回滚。
* 安装回执、Gardener 记录和标准控制矩阵。
* Docker Compose 中的前端、Gateway、PostgreSQL 和 Redis。
* 不消耗 Codex 或 OpenAI 配额的自动化与浏览器测试。

后续生产强化包括身份授权、不可变审计、外部 MCP 集成和分布式队列。

完整状态见 [需求矩阵](docs/requirements-matrix.md)。

企业知识架构、来源治理和本机模型边界见
[企业知识设计](docs/enterprise-knowledge.md)。

## 运行时边界

本项目使用本机 Codex 登录状态。用户先通过 `codex login` 完成 ChatGPT 登录，Gateway 再调用本地 Codex 进程。`OPENAI_API_KEY` 不属于本项目的默认运行架构。

目标运行时：

1. `codex app-server` 提供线程、审批和流式事件的深度集成。
2. `codex exec --json` 提供机器可读的兼容执行路径。
3. `FakeAgentRuntime` 用于测试和无配额验证。

当前本机调查记录见 [本地 Codex 运行时 ADR](docs/adr/0001-local-codex-runtime.md)。

## 启动本机订阅运行时

先安装后端开发依赖并确认本机 Codex 已通过 ChatGPT 登录，然后运行：

```powershell
.\scripts\run-local-codex-gateway.ps1
```

该脚本检查 `codex login status`，设置 `codex-app-server` 运行时并启动 Gateway。它不会读取 Codex 凭据文件，也不会要求 API Key。

## 调用端接入

调用端先创建一个 Conversation，随后所有消息复用其物理 ID：

```powershell
$conversation = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/conversations `
  -ContentType "application/json" `
  -Body '{"project_id":"cag","title":"持续工程会话"}'
```

前端或调用端保持一条由 CAG 提供的 SSE 连接：

```text
GET /api/v1/conversations/{conversation_id}/events
```

每轮消息创建一个 Task，并传入同一个 `conversation_id`。CAG 在内部首次启动 Codex thread，后续恢复该 thread。调用端不直接连接 Codex app-server。

完整请求和续传规则见 [API 文档](docs/api.md)。

## 受控自增强

调用端可显式选择 `self-improvement-candidate`。CAG 会为该任务创建独立候选目录，只把该目录加入本轮 Codex 文件系统能力范围。Agent 可写入候选 Skill、Validator 和 `TASK_LEARNING_RECEIPT.md`。候选保持 `proposed` 状态，正式安装需要独立评测和人工批准。

自增强闭环和回滚规则见 [自增强设计](docs/self-improvement.md)。

## 本地启动

进入后端目录并安装开发依赖：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

启动服务：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --reload
```

服务监听 `0.0.0.0:8000`。本机通过 `http://127.0.0.1:8000` 访问，其他机器通过 `http://<CAG主机IP>:8000` 访问。OpenAPI 路径为 `/docs`。项目配置默认从 `projects/*.yaml` 加载，任务工作区默认写入 `workspaces/{project_physical_id}/{task_id}`。

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

本机管理台地址为 `http://127.0.0.1:5173`，局域网地址为 `http://<CAG主机IP>:5173`。管理台的 `/api` 请求和 SSE 由前端 Nginx 同源转发到本机 Gateway。默认 Compose Gateway 使用 Fake Runtime，适合无配额的确定性测试。本机订阅运行时通过上面的主机脚本启动。

## 测试

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-fail-under=90
cd ..\frontend
pnpm test
pnpm build
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
