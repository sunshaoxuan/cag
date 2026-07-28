# Changelog

本文档记录 Agent Gateway 的可发布版本。版本遵循 Semantic Versioning。

## 0.12.0

发布日期：2026-07-28

### Added

* 文件夹和网络共享来源改用广度优先目录队列，每次只打开并关闭一个目录。
* 新增 `knowledge.collection.progress` 事实事件，持续反馈当前相对目录、阶段、已扫描目录、待扫描目录、已发现文件和已处理文件。
* 企业知识页面自动连接正在运行的定时采集，并以可读文本显示目录扫描进度。
* 采集事件画面支持显示最近 50、100 或 200 条，前端内存最多保留 200 条并独立统计接收总数，后端继续保存完整事件。

### Fixed

* 活动采集再次触发时复用原任务和 SSE，避免同一来源并发启动多个扫描线程。
* `ingest()` 增加队列状态门，已经运行或结束的采集不会再次执行。
* 大型共享目录扫描期间持续反馈目录和文件计数。
* 加密或不可解密 PDF 作为单文件拒绝项继续处理，避免一个文件终止整个来源。

### Validated

* 广度优先目录顺序、目录进度数据、文件计数和防重入测试通过。
* 后端全量测试、前端测试和生产构建通过。
* 真实 Windows 网络共享逐目录进度、浏览器显示、控制台和截图验证通过。

## 0.11.0

发布日期：2026-07-28

### Added

* 新增知识来源凭据按需揭示 API，从 Windows 凭据库读取已保存的用户名和密码或令牌。
* 编辑已配置来源时自动加载凭据，密码框支持显示、隐藏和复制。
* 凭据响应增加 `no-store`、`private`、`no-cache` 和 `nosniff` 保护头。

### Security

* 来源列表、普通详情、运行历史、SSE 和日志继续排除凭据正文。
* 凭据只在用户进入编辑流程时通过独立 POST 动作读取。
* 凭据揭示接口属于受信管理边界，生产开放仍以调用方认证和项目授权为准入条件。

### Validated

* 后端凭据读取、未配置凭据和响应缓存头测试通过。
* 前端凭据加载、显示、隐藏、复制、TypeScript 和生产构建通过。
* 真实 Windows 凭据库、浏览器复制、控制台和截图验证通过。

## 0.10.0

发布日期：2026-07-28

### Added

* 新增持久知识同步调度器，来源可配置为手动同步或按间隔自动同步。
* 新增数据库租约、重启恢复、指数退避重试、下次同步时间、最近内容变化时间和连续失败计数。
* 新增每轮同步触发方式、开始时间、变化文件数和删除文件数的持久历史。
* 企业知识页面新增同步策略、调度状态、来源健康状态和最近五十轮运行历史。

### Idempotency

* 每轮自动同步读取来源完整快照，内容哈希和规范路径共同判定变化。
* 未变化文档继续复用原文档、分块和向量，变化文件局部重建，删除文件同步移除。
* 行级数据库租约阻止多个 Gateway Worker 同时处理同一个到期来源。

### Validated

* 调度租约、失败重试、文件增加、文件变化、文件删除和运行历史测试通过。
* Alembic 升级、降级、完整后端测试、前端测试和生产构建通过。
* 本机 Ollama 周期同步、真实管理页面、浏览器控制台和截图验证通过。

## 0.9.1

发布日期：2026-07-28

### Fixed

* 修复长期记忆治理面板缺少内边距导致标题、治理标签和空状态贴近外框的问题。
* 统一长期记忆页与知识、能力治理页的 30 像素内容边距，并为记忆空状态增加独立边框和居中布局。

### Validated

* 前端组件测试、TypeScript、生产构建和真实 5173 页面验证通过。
* 浏览器控制台警告和错误检查、桌面截图验证通过。

## 0.9.0

发布日期：2026-07-28

### Added

* 新增本机文件夹、Windows 网络共享、Git、GitLab 和 SVN 知识来源登记。
* 新增连接验证、位置编辑、启用停用、删除、凭据轮换和分支、版本、子目录配置。位置身份变化时自动废弃旧索引。
* Git 和 SVN 资源形成版本寻址的受管快照，GitLab 项目仓库和 Wiki Git 仓库共用安全 Git 连接器。
* 新增 PDF、DOCX、PPTX、XLSX、ODT、CSV、代码、脚本和配置文本抽取。
* 新增采集、清洗、向量索引和来源记忆保存的完整 SSE 事件。
* 新增独立长期记忆页面，知识来源和记忆候选不再挤在同一页面。

### Security

* 来源密码和访问令牌写入 Windows Credential Manager，数据库只保存不透明凭据引用。
* Git 凭据通过子进程环境头传递，SVN 密码通过标准输入传递并禁用认证缓存。
* UNC 认证使用 Windows WNet API，连接器命令使用参数数组并经过命令策略。

### Idempotency

* 规范化来源键阻止同一项目重复登记相同来源。
* 清洗内容哈希跳过来源快照中的重复文件。
* 重复采集复用未变化文档、分块和向量，并分别报告重复文件、未变化文件和复用向量。

### Validated

* 后端单元、API、真实本机 Git、真实本机 SVN、Alembic 升降级和覆盖率门通过。
* 前端组件、同源 API、TypeScript 和生产构建通过。
* 本机 Ollama 完成十个架构文档、十一个向量分块的真实索引，第二轮写入零个分块并复用十一个向量。
* 浏览器完成来源登记、连接验证、两轮采集、完整 SSE、独立记忆页面、控制台和截图验证。

## 0.8.2

发布日期：2026-07-28

### Changed

* 将 5173 端口明确为统一 CAG 可视化管理台，同时提供 API 测试、调用监控、企业知识和能力治理。
* 前端 API 与 SSE 默认使用同源 `/api` 路径。
* 前端 Nginx 将 `/api` 转发到本机 ChatGPT 订阅运行时 Gateway。
* 局域网浏览器不再请求访问者电脑的 `127.0.0.1:8000`。
* HTML 入口禁止缓存，带内容哈希的静态资源使用长期缓存。

### Validated

* 同源 API 地址解析、前端组件、生产构建和 Compose 配置通过自动化验证。
* 通过 CAG 主机局域网 IP 打开管理台后，项目、调用轨迹、知识来源和能力数据通过真实 API 加载。
* API 监控 SSE、浏览器控制台和管理台截图通过验证。

## 0.8.1

发布日期：2026-07-28

### Fixed

* 本机 ChatGPT 订阅运行时的 Gateway 默认监听地址从 `127.0.0.1` 修正为 `0.0.0.0`。
* 后台任务管理按端口识别监听进程，并验证监听地址覆盖全部网络接口。
* 启动后台任务时自动替换原有的回环地址监听。
* 将根工作区忽略规则限定到仓库根目录，确保 Workspace Manager 模块进入版本管理。

### Validated

* PowerShell 脚本回归测试覆盖默认监听地址和后台任务监听判定。
* 实际后台 Gateway 监听地址、健康状态和版本通过本机运行验证。

## 0.8.0

发布日期：2026-07-27

### Added

* 外部系统继续使用 `POST /api/v1/tasks` 提交任务，并获得 Trace ID、事件地址和审计地址。
* 支持 `X-CAG-Client-ID`、`X-Request-ID`、`X-CAG-Source` 和 `Idempotency-Key` 调用头。
* 相同客户端和幂等键复用原任务，相同幂等键对应不同请求正文时返回 HTTP 409。
* 为全部 TaskEvent 分配 Gateway 全局审计序号。
* 新增 `/api/v1/audit/tasks` 调用轨迹查询。
* 新增 `/api/v1/audit/tasks/{task_id}` 审计详情。
* 新增 `/api/v1/audit/events` 全局审计 SSE，支持断线续传与来源、客户端、任务过滤。
* 新增 API 调用监控页面，持续显示外部 API 和网页测试台触发的全部事实动作。
* 网页任务入口标记为 `test_console`，与默认 `external_api` 来源分别审计。

### Validated

* 62 个后端测试通过，覆盖率 88.69%。
* 8 个前端测试、TypeScript 和生产构建通过。
* Alembic 升降级、Docker Compose、外部 API 调用、全局 SSE、浏览器控制台和截图通过验证。

## 0.7.2

发布日期：2026-07-27

### Changed

* 将总览、对话工作台、企业知识和能力治理拆分为四个独立路由页面。
* 总览仅保留产品定位、运行能力和三个功能域入口。
* 连续对话、Harness 参数、审批和完整 SSE 事件流保留在同一个操作上下文。
* 页面切换使用浏览器历史记录，支持前进、后退和直接访问。
* 路由切换时恢复页面顶部，避免继承上一页滚动位置。

### Validated

* 7 个前端组件与路由测试、TypeScript 和生产构建通过。
* 四个路由的直接访问、页面隔离、浏览器控制台和截图通过验证。

## 0.7.1

发布日期：2026-07-27

### Changed

* 使用 One人事公开网站的视觉语言重构现有控制台。
* 新增悬浮白色导航、高对比橙色主操作、青绿色数据与运行状态语义。
* 首屏改为 CAG 一体化任务链，连续对话提前为首要工作区。
* 企业知识、能力治理、对话、审批和事件流统一为模块化卡片体系。
* 保留现有 API、SSE、审批、Harness、知识索引和自学习交互契约。
* 增加桌面及窄屏响应式规则、键盘焦点和减少动效支持。

### Validated

* 前端组件测试和生产构建通过。
* 本机 5173 页面、锚点导航、真实数据、浏览器控制台和截图通过验证。

## 0.7.0

发布日期：2026-07-27

### Added

* Skill、Tool、Validator、Harness Profile 和 Memory 统一能力注册表。
* 学习信号的成功三次、失败两次候选触发规则。
* `proposed → validated → benchmarked → shadow → canary → active` 提升状态机。
* 20 个隔离回放、两个项目覆盖、质量收益、成功率、延迟、安全和架构固定质量门。
* 连续十次影子运行、连续五次金丝雀运行及 Gateway 范围自动启用。
* 连续失败、质量下降和手工触发回滚，以及外部 installation receipt。
* Doc、Skill、Tool 和 Memory Gardener 执行记录。
* NeurIPS RAG、ISO、NIST AI RMF 和 OWASP 控制映射 API。
* 自学习状态、能力注册表和标准控制矩阵前端。

### Validated

* 58 个后端测试通过，覆盖率 88.65%。
* 20 案例回放、影子、金丝雀、安装回执、敏感内容拒绝和自动回滚通过。
* 6 个前端测试及生产构建通过。
* 真实平衡 Harness 完成，验证三 Agent 并行调查、持久化审批、三路独立复核和 2,490 条统一 SSE 事实事件。
* Agent 超时写入明确的秒数错误，并由回归测试覆盖。

## 0.6.0

发布日期：2026-07-27

### Added

* `single`、`fast`、`balanced` 和 `deep` Agent Harness Profile。
* 并行只读调查、唯一写入 Executor、独立 Review 和 Validator 运行。
* HarnessRun、AgentRun、TaskGraphNode、AgentArtifact、ReviewFinding、VerificationRun、QualityScore 和 LearningSignal 记录。
* Command Policy Engine 和持久化 ApprovalRequest 生命周期。
* Harness、子 Agent、审批、复核和质量公共接口。
* 汇入单一 Task SSE 的子 Agent 事实事件。
* 前端 Harness Profile、学习模式和实时子 Agent 状态。
* pgvector 向量库约束、来源指纹和文件内容哈希驱动的幂等增量索引。
* 未变化文件复用原有文档、分块和向量，变化文件独立重建，删除文件清理索引。

### Validated

* 47 个后端测试通过，覆盖率 87.72%。
* 并发 Agent、单写者、Artifact、策略判定、审批和事件顺序使用 Fake Runtime 验证。
* 5 个前端测试及生产构建通过。

## 0.5.0

发布日期：2026-07-27

### Added

* Ollama 企业知识适配器，使用 `qwen3-embedding:8b` 和 `qwen3:14b`。
* 客户、产品、产品版本、来源、文档、分块、记忆候选、引用和质量记录。
* AES GCM 知识正文加密及 Windows Credential Manager 密钥入口。
* 代码和文档增量采集、Secret Scanner、Prompt Injection 标记和 1024 维向量索引。
* 向量与关键词 Reciprocal Rank Fusion 检索、租户过滤和批准来源上下文注入。
* 知识来源、索引 SSE、检索及记忆批准、拒绝、提升、废弃 API。
* 企业知识治理前端及任务知识模式。

### Validated

* Fake Ollama 单元和 API 测试不消耗模型或 Codex 配额。
* 知识关闭时旧 Task 与 Conversation SSE 契约保持不变。
* 本机模型、GPU 和 1024 维向量能力已经实测。

## 0.4.0

发布日期：2026-07-27

### Added

* Conversation 创建、查询、历史 Task 查询和会话级 SSE 接口。
* CAG Conversation 到持久 Codex thread 的一对一映射。
* 首轮 `thread/start` 和后续轮次 `thread/resume`。
* 会话级连续事件序号、SSE 心跳和 `Last-Event-ID` 断线续传。
* 复用单一 Conversation SSE 连接的连续对话页面。
* `self-improvement-candidate` 受控运行配置及任务专属候选目录。
* Project 允许的 Runtime Profile 服务端校验。

### Validated

* 真实本机 ChatGPT 订阅登录态完成连续两轮对话。
* 第二轮在新的独立 Git 工作区中恢复同一个 Codex thread。
* 第二轮准确返回第一轮保存的随机标记。
* CAG 会话 SSE 的事件序号从 1 连续到 16，第二轮记录 `resumed`。
* 自增强配置只授予任务专属候选目录写入能力，正式安装仍需人工批准。

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
