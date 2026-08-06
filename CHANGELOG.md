# Changelog

本文档记录 One Agent Gateway 的可发布版本。版本遵循 Semantic Versioning。

## 0.24.0

* Add scoped customer ledger extraction schema v1 with Catalog scope
  resolution, exhaustive file manifests, file level extraction checkpoints,
  coverage, conflicts, unresolved fields and stable error codes.
* Persist independent Source, Document, Processing, Knowledge Block and
  Applicability physical versions. Changed or absent source files retain their
  historical documents, chunks, evidence and audit relationships.
* Select business facts at `analysis_context.as_of` while Processor activation
  remains an independent version axis. A failed processing refresh preserves
  the previous Active version.
* Add idempotent scope repair ingestion and separate scope repair from
  extraction reanalysis.
* Give exhaustive customer extraction its own 900 second deadline so file level
  model work is independent from the 30 second deep-search contract.
* Bound each customer document model call to 15 seconds and report timeout as a
  document failure so the exhaustive Manifest reaches a terminal aggregate.
* Register complete v1 object schemas for contracts, services, VPNs,
  environments, remote access and repositories.
* Deduplicate extracted code symbols by their persisted document identity so
  repeated parser facts cannot roll back a long knowledge refresh.
* Persist redacted-input embedding checkpoints per batch so interrupted large
  source refreshes resume without repeating completed GPU work or retaining all
  vectors in process memory.
* Bound PostgreSQL lexical retrieval to indexable identifiers and terms so CJK
  bigrams cannot force a full knowledge scan past the statement timeout.
* Include a governed Source subpath in semantic path embeddings while keeping
  canonical document paths and resource URIs stable.
* Keep natural-language English terms in semantic retrieval and reserve the
  bounded lexical channel for the full query, codes, protocol identifiers and
  sufficiently specific CJK terms.
* Close file provenance with raw byte SHA 256 values, required physical
  SourceEntry foreign keys on documents and Citation source entry IDs.
* Add a resumable, bounded-concurrency provenance backfill command so legacy
  sources can receive original-byte hashes without repeating OCR, cleaning or
  embedding work. Files whose size or modification time changed are left for
  normal ingestion instead of being linked to stale knowledge.
* Freeze the original knowledge document schema in Alembic revision 0005 so a
  clean PostgreSQL installation can replay through revision 0024.
* Create a fresh operational triage queue item after an explicit reopen or a
  failed evaluation so a finishing leased item cannot consume the new cycle.

发布日期：2026-08-06

### Added

* 扫描 PDF 在文本层为空时使用 Tesseract 日英 OCR，并保存页码、语言及提取器版本。
* 客户台账 Extraction v1 新增远程访问和代码仓库字段，协议与仓库类型必须出现在权威 Citation 中。
* 知识源保存全局处理器指纹，未变化文件在正文提取、OCR 和 embedding 之前直接复用物理文档与向量。
* Knowledge Retrieval Health 新增 freshness、最后成功时间、最后尝试时间和连续失败数。

### Changed

* Qwen3 Embedding 输入同时包含规范路径和脱敏正文，查询指令覆盖日文、中文及英文语义等价表达。
* 客户 Scope 直接从受治理 Catalog 定位，身份解析使用 Code、正式名、略称和别名，强引用使用 Scope 物理 ID。
* Scope 下所有 Catalog 文件进入 Manifest，抽取按文件顺序执行，并记录每个文件的处理状态和失败原因。
* 内容相同的不同物理路径分别保留；不支持、空文本及提取失败文件生成受限的路径存在证据。

### Security

* 日文密码、用户、账号、连接目标、主机及 IP 字段在搜索投影、向量和模型上下文之前脱敏。
* 路径证据只证明资产存在，不能作为正文事实 Citation。

### Validation

* 滋贺大学五页扫描维护合同通过真实日英 OCR 生成 5544 个字符，并识别客户、契约及维护语义。
* 远程连接 Fixture 只生成具备 SSH Citation 的候选；缺少 SVN Citation 时返回 repository learning gap。

## 0.23.0

发布日期：2026-08-06

### Added

* 新增客户台账异步 Knowledge Extraction API，以 CAG 所有的结构化 Schema 返回契约、Service、VPN 和 Environment 候选。
* 候选使用独立物理 ID，并保存 Chunk、Source、Generation、Resource URI 和内容 Hash Citation。
* Migration 0021 新增 PostgreSQL pg_trgm 以及 Knowledge Text、Document Path、Code Symbol 的 GIN Index。
* Retrieval Stage Event 记录 Profile、候选件数、经过时间、Source、Generation、失败 Stage 和 Rerank Fallback。

### Changed

* API 与 durable queue worker 改为独立操作系统 Process，由宿主 Launcher 共同监督。
* API 与 worker Process 都连接 Redis wake-up channel；API 只发布唤醒消息，不运行队列消费者。
* Supervisor 使用 `/health/live` 决定 Process 重启，并保留 `/health/ready` 作为依赖状态证据。
* Knowledge Search 使用固定上限的 PostgreSQL 候选、pgvector Top K、pg_trgm Index 和 Statement Timeout。
* `fast` Profile 跳过 Ollama Embedding，优先检索 Code、正式名、略称和 Path。
* 客户台账抽取先确定包含 Code 或正式名的权威客户目录，再按 Section 在该目录内检索，目录身份缺失时返回 Learning Gap。

### Fixed

* 删除每次检索对全部 Chunk、Symbol、Relation 和 Document Link 的应用内读取和排序。
* Authority Citation 中不存在的 Chunk、空 Values、不正 Confidence 和未要求 Section 不再进入有效候选。
* Lease 恢复先处理 Cancel Request，取消完成的 Task 不再重新进入 Queue。
* Queue finish 按时间顺序处理 Cancel 与 Completion 竞态，Cancel 先发生时清除未交付结果并进入 cancelled；活动任务默认每秒检查取消请求。
* 取消 scheduled ingestion 时推进 Source 的下一次同步时间并释放调度租约，避免调度器立即创建同一 Source 的重复任务。
* SQLite cutover 的目标 Schema Gate 更新为本版本 Alembic Head `20260806_0021`，避免全新环境在迁移后被陈旧 Revision 拒绝。
* Knowledge Retrieval 饱和时，API Health、Task、Queue 和 Cancel 接口继续由独立 API Process 响应。

## 0.22.8

发布日期：2026-08-05

### Added

* XLSX 使用 openpyxl 只读语义解析，保留工作表顺序、名称、显示状态、单元格坐标、规范化值、公式和已有缓存值。
* 文件资产 API 和知识页面显示实际提取器、提取器版本和处理时间。
* 知识页面文件资产支持路径搜索、清除和每页 100 条的前后翻页。
* 工作簿默认最多处理 250000 个有效单元格，提取文本受既有文件大小策略约束。

### Fixed

* 同一学习批次重复报告相同路径时执行幂等合并，避免拒绝审计唯一约束导致整轮学习失败。
* 同一路径的处理失败结论优先于跳过结论，拒绝数和跳过数按唯一最终路径计算。
* `~$` Office 临时文件以 `temporary_office_file` 登记并跳过正文提取。
* XLSX 使用独立处理器变体指纹，只重新处理 Excel，其他未变化文档继续复用既有向量。

### Validation

* 目标工作簿只读验证识别 14 个工作表、1001 个有效单元格、47 个公式和 47 个缓存值。
* 多工作表、日文、公式缓存、隐藏工作表、合并单元格、资源限制、恶意 XML、临时文件、重复拒绝和 Worker 隔离测试通过。
* 前端组件测试和生产构建通过；完整后端、隔离运行、浏览器和 UPDS 全量学习结果记录在版本证据中。

## 0.22.7

发布日期：2026-08-05

### Added

* 本地 Codex 运行时同时支持 ChatGPT 登录和 Codex API Key 登录。
* app-server API Key 会话在 account/read 返回空 account 且 `requiresOpenaiAuth=false` 时被识别为 `apiKey`。

### Changed

* 受监督启动脚本接受 `Logged in using ChatGPT` 和 `Logged in using an API key` 两种登录状态。
* `AGENT_GATEWAY_CODEX_REQUIRE_CHATGPT_AUTH=false` 表示允许两种本地 Codex 登录方式，仍不读取或保存 API Key。
* API Key 登录状态会在启动前被识别，并通过环境配置传递给 app-server 运行时。

### Validation

* 新增 ChatGPT、API Key、API Key 空 account 响应和 ChatGPT-only 门禁测试。
* 完成后端完整测试、前端测试、生产构建、PowerShell 解析和本机 app-server account/read 验证。

## 0.22.6

发布日期：2026-08-04

### Fixed

* 代码事实浏览器的“检索事实”按钮高度与项目、搜索和类型控件统一，避免按钮因网格底部对齐产生下沉错位。

### Validation

* 完成前端单元测试、生产构建和桌面及窄屏浏览器截图验证。

## 0.22.5

发布日期：2026-08-03

### Added

* 问题详情顶部新增常驻管理员决策区，发生次数只作为影响信息，不再影响入口可见性。
* 方案待修订和分诊失败问题同时提供“要求修订并重新 Review”和“不允许修改并结束”。
* 等待外部处理的问题可登记人工结果，也可由管理员明确结束当前处理并禁止本轮修改。

### Changed

* 独立 Review 通过的问题使用“批准 Agent 自增益”明确进入受控改进流程。
* 管理员拒绝扩展到等待审批、方案待修订、分诊失败和等待外部处理状态，操作者、原因和事件继续完整审计。
* 原先位于长篇方案之后的分散操作表单合并到顶部决策区。

### Validation

* 新增 100 次重复问题的管理员入口组件测试，以及方案待修订拒绝、分诊失败拒绝动作和外部处理动作契约测试。
* 执行完整后端测试、前端组件测试、生产构建和真实浏览器验证。

## 0.22.4

发布日期：2026-07-31

### Fixed

* 问题中心由后端状态机统一返回当前可执行动作，页面不再根据状态自行推断审批、拒绝、实施和重新处理入口。
* `reopen` 仅接受已关闭、已拒绝、验证完成、已移交、分诊失败和方案待修订状态，并清理上一轮审批、实施、评估和决策投影。
* 问题详情选择增加请求序号保护，较早发出的慢响应不能覆盖管理员最新选择。
* 管理员意见、实施说明和时间线状态按问题隔离，切换问题时不会沿用上一问题的输入。
* 状态变更错误和成功结果在当前操作区就地显示。
* 队列最终失败与问题失败摘要在同一后端处理步骤提交，消除 `triage_failed` 已可见而中文失败摘要尚未写入的短暂不一致。
* 发布验证记录使用 `validation_completed`，历史生产验证记录不再显示为管理员拒绝。

### Changed

* 问题详情不再内嵌全部运行事件。
* 新增分页时间线接口 `GET /api/v1/operations/issues/{issue_id}/events`，默认返回最近 100 条，支持 `before_sequence` 继续读取。
* 问题响应新增 `event_count` 和 `planned_actions`；`allowed_actions` 只表示当前状态允许执行的管理动作。

### Validation

* 新增 rejected 重新提交、认证错误就地反馈、慢响应选择保护、事件分页和重复 reopen 拒绝测试。
* 执行完整后端测试、前端组件测试、生产构建、Alembic 升级验证和浏览器检查。

## 0.22.3

发布日期：2026-07-31

### Fixed

* 问题分诊运行时在方案完成前失败时，后端生成完整的中文失败摘要、根因说明、改进目标、管理员操作和审批阻断项。
* 原始技术错误继续保留在根因和折叠审计证据中，失败记录不会沿用上一版英文管理员说明。
* 分诊失败统一进入 `triage_failed`，实施方式重置为待判断，审批保持关闭。

### Validation

* 新增问题处理运行时输出超过传输限制的回归测试。
* 执行完整后端测试、前端组件测试、生产构建和浏览器验证。

## 0.22.2

发布日期：2026-07-31

### Fixed

* 中文审核门禁允许改进范围保留纯文件路径、命令和代码标识，改进内容与原因继续要求使用简体中文。
* 每次规划使用包含事件序号的新只读工作区，重新规划和评估失败后的下一轮会从当前默认分支重新克隆，避免复用旧版本源码。

### Validation

* 后端覆盖纯技术改进范围与中文说明组合，以及同一问题连续三轮规划使用三个不同工作区。
* 执行完整后端测试、前端组件测试、生产构建和真实问题复跑。

## 0.22.1

发布日期：2026-07-31

### Changed

* 问题中心的归纳、影响、根因、改进目标、实施方式说明、改进点、阻断项、验收计划和回滚计划统一要求使用简体中文。
* 代码标识、命令、路径、API 名称、错误码和必要的错误原文保持原样，避免翻译破坏技术证据。
* 规划与独立 Review 增加 `administrator_language: zh-CN` 契约和主要审核字段中文校验。
* 模型输出未通过中文校验时，问题进入方案待修订，主视图生成中文失败归纳，原始输出保留在折叠证据中。
* 需要管理员处理的实施说明和边界回退说明改为中文。

### Validation

* 后端覆盖正常中文规划、中文 Review、英文归纳拒绝、畸形输出回退和审批门禁。
* 前端继续验证中文决策摘要和生产版本标题。

## 0.22.0

发布日期：2026-07-31

### Added

* 问题中心新增实施方式归类，区分 Agent 自增益、人工代码补强、外部操作、混合处理、职责外和待判断。
* 新增结构化审核决策摘要，集中展示问题归纳、运行影响、根因判断、改进目标、建议改进点、阻断项、验收计划和回滚计划。
* 新增 `plan_revision_required` 状态。存在阻断项、Review 要求修订或结构化输出无效时进入方案修订流程。

### Changed

* AI 规划与独立 Review 使用严格 JSON Schema。无法解析、字段缺失和结论矛盾统一按需要修订处理。
* 审批 API 增加独立 Review 通过、零阻断项和 `approval_ready` 三项服务端门禁。
* 问题中心将完整方案、Review、运行事件和时间线保留为默认折叠的审计证据，主视图优先呈现可决策信息。
* 问题事件序号改为问题记录上的原子递增计数，避免并发写入产生重复序号。

### Migration

* Alembic `20260731_0018` 增加实施方式、决策摘要、Review 结论、阻断项数量和原子事件序号。
* 迁移会识别历史 Review 中明确的修订或禁止批准结论，将对应待审批问题转为方案待修订。

### Validation

* 后端覆盖结构化通过、明确修订、畸形 Review、审批门禁和并发问题事件。
* 前端覆盖审核摘要、实施方式、折叠证据、审批交互和生产构建。

## 0.21.1

发布日期：2026-07-31

### Security

* 问题中心的批准、拒绝、人工或批量实施登记、人工评估和重新打开接口要求 `X-CAG-Admin-Token` 与 `X-CAG-Admin-Identity`。
* 服务端以令牌认证后的身份写入审批与操作审计，不再信任请求体声明的管理员名称。
* 管理画面新增会话级管理员授权区域，令牌只保存在浏览器 `sessionStorage`。

### Changed

* 自运维 AI 调查不再持久化 `*.delta` 逐字增量事件。最终消息、命令、测试、方案、Review 和状态事件继续完整保留。
* 生产验证发现的 4,464 条累计文本增量膨胀被纳入回归测试，避免问题详情和 PostgreSQL 事件表随模型输出快速增长。

### Validation

* 新增无效管理员令牌返回 HTTP 401、服务端审计身份和增量事件过滤测试。
* 重新执行后端全量、前端单元与构建、受管服务、生产 API 和浏览器验证。

## 0.21.0

发布日期：2026-07-31

### Added

* 新增自运维问题处理中心，统一接收 Task、知识学习、API、监督器和外部连接器失败。
* 新增问题、发生记录、版本化方案与 Review、实施和评估证据、处理时间线数据模型。
* 新增 `operations` PostgreSQL 持久队列与独立 Worker，继续使用 Redis 即时唤醒、租约、心跳、有限重试和启动恢复。
* 新增 AI 责任边界判断、改进规划、独立 Review、管理员审批、受控改进分支、再评估和关闭闭环。
* 新增问题中心管理画面、总览、筛选、审批、人工改进登记、重新处理和完整证据时间线。
* 新增问题中心 API、在线调用范例和监督器离线 JSONL 故障缓冲。

### Changed

* 受管 Gateway 的未处理 API 异常会写入问题中心。
* 交互任务和知识学习队列在最终失败后自动上报问题中心；改进任务失败回到原问题进入下一轮。
* 管理员批准内部问题后，CAG 创建 `codex/improvement/<issue-code>` 隔离分支任务。任务只提交本地分支，不自动推送或合并。
* 外部依赖和凭据问题保留 AI 方案与 Review，等待管理员登记修复证据后进入独立再评估。
* Windows 监督器在 Gateway 不可用时把启动和健康失败写入本地 JSONL 缓冲，服务恢复后幂等提交。

### Migration

* Alembic `20260731_0017` 新增问题中心表，并扩展 `queue_items` 以支持 `issue_id` 资源。
* 新增 `AGENT_GATEWAY_QUEUE_OPERATIONS_WORKERS`，默认启用一个问题处理 Worker。

### Validation

* 后端测试覆盖问题去重、敏感信息清理、AI 方案与 Review、审批、外部修复、隔离分支实施、再评估和关闭。
* 前端测试覆盖问题总览、方案、Review、时间线和审批交互。
* PowerShell 验证覆盖监督器离线问题缓冲和恢复提交。

## 0.20.0

发布日期：2026-07-30

### Added

* 企业知识来源新增真实检索健康状态，显示可访问分块、总分块、待升级文档和活动知识代。
* 知识文档记录产生它的学习批次，现有文档在迁移时回填最近一次成功批次。
* 新增产品版本滚动和失败刷新回归测试。

### Changed

* 产品共享知识按稳定 Product 物理 ID 检索，同一产品的 Gateway 或前端版本变化不再隔离既有向量。
* 处理器指纹继续独立决定重新处理。内容未变化但路由、解析器、分块策略、模型或向量维度变化时进入新处理分支。
* 已存在成功知识代的来源开始刷新时继续提供旧索引；新知识在文档、向量、代码符号和关系全部提交后生效。
* 刷新失败时保留来源批准状态和旧知识代，并通过健康状态显示降级原因。
* 项目版本同步在知识检索和代码知识接口调用前提交，保证独立知识会话能够读取新的产品版本记录。

### Migration

* Alembic `20260730_0016` 增加知识文档学习批次外键和索引，并回填现有文档。
* SQLite 到 PostgreSQL 自动切换收据的目标版本同步为 `20260730_0016`。
* 现有向量无需重新生成即可恢复同产品跨版本召回。

### Validation

* 产品版本切换后的旧 SQL 精确召回通过。
* 模拟新一轮向量化失败后，旧知识继续召回通过。
* 后端知识、迁移、前端组件和生产构建验证通过。

## 0.19.0

发布日期：2026-07-30

### Added

* API 测试台新增灰色中间回答区域，按 Agent 运行和消息项聚合，默认折叠并可由使用者展开。
* 最终报告新增 GitHub 风格 Markdown 渲染，支持标题、列表、链接、代码、引用和表格。

### Changed

* Agent SSE 增量继续完整进入审计事件流，聊天主回答仅在 Task 进入终态后读取 `final_report.summary`。
* 调查、执行和独立复核消息不再覆盖最终回答，执行期间保持明确的处理中状态。

### Validation

* 前端组件测试覆盖中间回答折叠、消息增量聚合和最终 Markdown 结构。
* TypeScript 与 Vite 生产构建通过。

## 0.18.0

发布日期：2026-07-30

### Added

* 新增持久化 `KnowledgeSourceEntry` 文件资产清单，记录每个来源条目的相对路径、类型、64 位文件大小、处理模式、状态、原因、最近发现与成功处理凭据。
* 新增来源文件资产查询 API 和企业知识管理画面，可按路径、处理模式和在库状态检查本轮发现、仅登记、路径知识、文档及代码条目。
* 新增处理策略指纹。解析器、路由策略、嵌入模型或向量维度发生变化时，未改动的文件也可获得重新处理机会。

### Changed

* ZIP、DUMP、备份、二进制和超限大文件进入仅登记模式，保留文件存在性及路径元数据，不读取内容，也不创建内容向量。
* 零字节文件进入路径知识模式，文件名和相对路径可参与检索。
* 源代码强制进入结构化代码分析分支，保存代码符号、关系和文档链接。0.18.0 首次运行会重新处理缺少策略指纹的旧代码文件。
* 文件大小字段升级为 PostgreSQL `BIGINT`，避免大文件审计记录触发 32 位整数溢出。
* 学习失败画面默认显示简短原因，原始完整异常继续保存在运行记录中，并可按需展开。

### Validation

* 文件路由、资产 API、64 位文件大小、零字节路径知识、旧代码回填和未变化文档向量复用测试通过。
* Alembic `20260730_0015` 在隔离 PostgreSQL 与 pgvector 数据库中升级通过。
* 前端组件、生产构建、隔离管理画面、浏览器控制台和截图验证通过。
* 正式受管服务在迁移前完成 PostgreSQL 压缩备份，随后应用 `20260730_0015` 并在 43.8 秒内恢复为 `0.0.0.0:8000`。原有 21,772 个知识文档和 170,807 个向量分块完整保留。
* 正式 5173 管理画面、在线 API 文档、局域网访问、Ollama 两个模型、队列工作器和自动学习进度通过运行验证。

## 0.17.1

发布日期：2026-07-30

### Added

* 新增长期运行监督脚本，每 15 秒检查监听地址和 `/health/ready`。
* 连续四次健康检查失败时重启已确认的 Gateway 进程，监听退出时延迟重新启动。
* 监督日志按 10 MiB 循环，保留五个历史文件。

### Changed

* Windows 计划任务增加系统启动和当前用户登录触发器。
* 计划任务监督器异常退出后每分钟重试，最多 999 次，允许电池供电并取消执行时限。
* 计划任务仍使用当前交互用户身份，以保持本机 ChatGPT 订阅认证可用。

### Validation

* 受控停止空闲 Gateway 后，监督器在 45.7 秒内完成全链路恢复，监听地址继续为 `0.0.0.0:8000`。

## 0.17.0

发布日期：2026-07-29

### Added

* 新增以 PostgreSQL 为任务事实库的持久队列，交互任务与知识学习使用独立队列和工作器池。
* 新增 Redis Pub/Sub 跨进程唤醒。Redis 不可用时保留 PostgreSQL 轮询和租约恢复能力。
* 新增队列状态、队列明细和取消 API，支持工作器心跳、租约到期重排、有限重试和重启恢复。
* 新增 `/api-docs` 在线文档画面，提供运行状态、请求约定、SSE 接续规则以及 PowerShell、curl 和 JavaScript 调用范例。
* 新增受保护的启动时 SQLite 整体切换。源库任务全部终止后，启动脚本自动执行一致性快照、事务替换、逐表物理 ID 和向量校验并写入数据库迁移回执。

### Changed

* 同一 Conversation 的多个任务可以连续提交，并按创建顺序串行领取。不同 Conversation 可以由多个交互工作器并行处理。
* 知识来源的手动和定时学习都进入 knowledge 队列，继续通过原 SSE 地址反馈流程。
* 已存在的任务工作区可在租约恢复时安全复用。
* 本机 Redis 端口发布到 `127.0.0.1:6379`，只供本机 Gateway 使用。
* 受管启动在迁移和 Redis 就绪后无依赖重建 5173 管理台，使首次切换直接显示 0.17.0 画面。

### Cutover boundary

* 0.17.0 的发布、测试和画面验证不停止当前 8000 端口上的 0.12.0 学习进程。
* 当前学习完成后，下一次受管启动才执行自动迁移和新版本切换。活动学习或 Agent 任务会关闭迁移执行，源 SQLite 始终保留为只读回退证据。

## 0.16.0

发布日期：2026-07-29

### Added

* Conversation 每轮在启动或恢复 Codex app-server turn 之前执行已批准知识检索。
* 注入 Codex 的知识片段增加来源名称、来源类型、规范路径、commit 和 `resource_uri`。
* 本地目录和 UNC 来源生成 `file:` URI，GitLab 和可识别 Git Web 来源生成 revision 固定链接，其他仓库保留仓库 URI、revision 和文件路径。
* Task 最终报告和 MemoryCandidate evidence 保存与 SSE 相同的结构化知识引用。

### Changed

* Codex developer instructions 明确要求先分析已学习知识，必要时通过资源 URI 定位原始材料，并在回答中引用相关资源。
* 知识搜索 API 和 `knowledge.context.injected` SSE 返回可追溯资源链接。
* 长期记忆提取使用本轮最终报告和知识引用共同生成候选，形成来源、分析、回答和记忆的闭环。

### Runtime boundary

* 0.16.0 不重启仍在执行旧版长时间学习任务的 8000 进程。
* 发布验证使用隔离测试数据库、Fake Runtime 和独立前端端口，不消耗 Codex 订阅额度。

## 0.15.0

发布日期：2026-07-29

### Changed

* 正式运行时数据库统一为 PostgreSQL 16 加 pgvector，Windows 启动脚本取消 SQLite 自动回退。
* PostgreSQL 启动就绪检查同时验证 `vector` 扩展，并在健康响应中公开数据库类型、原生向量检索状态和 pgvector 版本。
* 向量召回使用 PostgreSQL `<=>` 余弦距离算子和 HNSW 索引完成前二十项排序，SQLite 余弦计算仅保留在隔离单元测试中。
* PostgreSQL 容器将 5432 端口发布到本机回环地址，供本机 ChatGPT 订阅运行时使用。

### Added

* 新增 SQLite 到 PostgreSQL pgvector 的一次性整体迁移工具和 PowerShell 入口。
* 迁移会在源库仍有排队或运行中的学习任务时关闭执行。
* 迁移默认执行只读预检，写入必须显式指定 `Apply`。
* 迁移回执保存来源 SHA 256、完整性检查、逐表行数、物理 ID 摘要、向量数量、向量维度和 HNSW 索引状态。
* 新增真实 PostgreSQL pgvector 集成测试，覆盖原生向量检索和 SQLite 整体迁移。

### Cutover boundary

* 当前长时间学习任务继续使用原 SQLite 运行库直到自然结束。
* 任务结束后执行整体迁移、核对回执，再把 8000 服务切换到 PostgreSQL。0.15.0 发布过程不重启当前学习进程。
* 可接续并行作业和全路径语义学习继续按 ADR 0015 实现。

## 0.14.0

发布日期：2026-07-29

### Added

* 每个被拒绝或跳过的知识文件写入独立审计记录，保存相对路径、处理结果、扩展名、文件大小、原因码、提取器、异常类型、脱敏错误和时间。
* 新增采集拒绝审计分页查询、条件过滤、UTF-8 CSV 导出和 gzip JSONL 归档下载 API。
* 每轮采集生成带记录数和架构版本的压缩归档，并保存归档文件名、SHA 256 和生成时间。
* 新增数据库明细与压缩归档的独立保留期限，默认分别为 90 天和 365 天。
* 企业知识运行历史增加拒绝数、跳过数、中文原因摘要、逐文件表格、CSV 导出和压缩归档入口。
* 产品正式名称更新为 One Agent Gateway，管理台标题后显示当前发布版本的小号标识。
* 企业知识页面新增来源管理总览、名称与位置搜索、状态筛选、按需打开的创建编辑表单和持续可见的学习运行中心。

### Security

* 审计记录只保存相对来源路径。异常正文会移除来源根路径、换行并限制长度。
* 归档下载使用固定受管目录、规范化路径校验、`no-store` 和 `nosniff` 响应头。

### Validated

* 编码无法识别、空内容、不支持类型、文件超限和加密 PDF 的逐文件审计测试通过。
* 查询过滤、分页、CSV、gzip 归档、物理 ID、外键和 Alembic 升降级测试通过。
* 后端全量测试、前端测试、生产构建和浏览器管理画面验证通过。

### Planned boundary

* ADR 0015 记录逐路径语义知识、持久文件作业、并行租约、逐文件原子提交、暂停接续和 SQLite 到 PostgreSQL 加 pgvector 的受控迁移。0.14.0 不声明这些能力已经实现。

## 0.13.0

发布日期：2026-07-28

### Added

* 新增代码符号、代码关系和代码文档关联实体，全部使用独立 UUID 物理 ID、外键和内容指纹。
* Python 使用标准 AST 提取类、函数、方法和调用。Docker 正式环境预取 Tree-sitter 语法包，Windows 原生 DLL 被策略拦截时使用语言感知降级解析器并记录诊断。
* 代码按符号边界分块，分块保存起止行、符号名、符号类型、解析器和文件编码。
* 文本抽取支持 UTF-8、UTF-16、CP932 和 Shift-JIS，保存检测到的编码。
* 混合召回增加日文二元与三元词片、代码符号精确通道、调用关系扩展、代码文档关联和 `deep` 本地重排。
* 深度重排要求完整、无重复的候选 UUID，模型评分只形成受限 RRF 通道。缺失候选或非法 ID 时保留确定性排序。
* 新增代码知识摘要、符号列表和符号详情 API。
* 新增独立 `/code-knowledge` 页面，展示符号、关系、待解析目标、文档关联及证据。
* 采集 SSE 增加代码分析完成和代码图谱持久化事件。

### Idempotency

* 未变化代码继续保留原符号和向量。
* 变化或删除代码随文档级联更新，关系和文档关联按来源确定性重建。
* 关系和文档关联使用 SHA 256 指纹唯一约束，重复采集不会产生重复事实。

### Validated

* CP932 日文文件、Python AST、语言降级解析、结构化分块、调用解析、文档关联和日文检索测试通过。
* 代码知识 API、深度重排入口、租户与产品过滤、重复采集和 Alembic 升降级测试通过。
* 后端全量测试、前端测试和生产构建通过。

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
