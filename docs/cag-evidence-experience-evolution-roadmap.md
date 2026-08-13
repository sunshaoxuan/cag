# CAG 证据与经验系统演进路线图

## 1. 文档状态

状态：初步规划，等待逐阶段实施和验收。

基线版本：CAG 0.28.5。

规划日期：2026-08-13。

本路线图把 CAG 从以文件分块检索为中心的企业知识平面，演进为 Codex 可导航、可验证、可恢复、可持续学习的企业证据与经验系统。本文只声明目标、阶段和验收门。没有完成实现与验证的条目一律保持 `Planned`。

## 2. 初衷和最终目标

CAG 的长期职责是向 Codex 提供最短、可靠且可追溯的已知路径，并在真实任务完成后沉淀经过验证的经验。系统必须同时保有四种能力：

1. 完整发现来源中的物理文件和逻辑对象。
2. 把所有可安全抽取的文本转化为持久、可复验的证据对象。
3. 把证据、经验、任务和验证结果连接成有类型、带范围、带时间的关系网格。
4. 将已批准且适用的经验提供给后续 Codex 任务，并根据实际结果修订、替代或废弃经验。

目标闭环如下：

```text
易失来源
  -> 来源观察和原始 Hash
  -> 内容寻址的原始或清洗对象
  -> Document、Version、Chunk 和结构事实
  -> 经验候选及证据链
  -> 审批、适用范围和有效期
  -> Codex 任务匹配和使用
  -> 测试、运行结果和用户纠正
  -> 经验保持、修订、替代或废弃
```

## 3. 当前生产基线

2026-08-13 对正式 PostgreSQL 进行只读盘点，数据库约 11 GB：

| 对象 | 数量或规模 |
|---|---:|
| KnowledgeSource | 5 |
| KnowledgeSourceEntry | 113,908 |
| KnowledgeDocument | 22,552 |
| KnowledgeChunk | 183,091 |
| KnowledgeEmbeddingCache | 623,429 |
| CodeDocumentLink | 58,165 |
| MemoryCandidate | 143 |
| KnowledgeUsage | 65 |
| KnowledgeChunk 表和索引 | 约 6.4 GB |
| Chunk HNSW 索引 | 约 3.2 GB |
| Chunk 加密正文 | 约 818 MB |
| Chunk 搜索投影 | 约 592 MB |

主要生产来源 `UPDS顧客別情報` 当时的 Source Entry 状态为：

| 状态 | 数量 |
|---|---:|
| observed | 69,367 |
| metadata_only | 43,910 |
| indexed | 460 |
| rejected | 132 |
| removed | 14 |

该状态快照发生在一个定时 Ingestion 运行期间。`observed` 可能表示等待当前运行继续处理、历史运行未闭合或只完成发现阶段，不能直接等同于格式失败。后续转换必须冻结每轮 Manifest 并结合 Ingestion、Processing Version 和最终状态判断。

历史拒绝审计的主要累计原因包括：

| 处置 | 原因 | 累计记录数 |
|---|---|---:|
| skipped | unsupported_extension | 304,427 |
| skipped | metadata_only_policy | 10,699 |
| rejected | empty_text | 3,749 |
| skipped | file_too_large | 1,858 |
| rejected | office_archive_invalid | 1,563 |
| skipped | temporary_office_file | 950 |
| skipped | database_dump_policy | 306 |
| rejected | spreadsheet_cell_limit_exceeded | 183 |
| rejected | pdf_unreadable | 161 |
| rejected | encoding_unsupported | 82 |
| rejected | file_read_error | 54 |
| rejected | raw_hash_read_error | 23 |

现有提取器主要支持现代 Office、PDF、ODT、XLSX/XLSM、已列入白名单的文本和代码。旧 Office、邮件、RTF、图片 OCR、无扩展文本、许多脚本与配置类型仍缺少统一内容探测和受控提取路径。

## 4. 不可破坏的工程约束

1. PostgreSQL 继续保存业务真相、物理 UUID、外键、权限、版本、审批和审计。
2. Code 和名称只承担业务识别、显示和搜索。强引用保存物理 UUID。
3. 原始路径是可变化的来源观察，不能作为知识内容的唯一副本。
4. 原始字节、清洗对象、Document、Chunk、经验和任务之间必须双向可追溯。
5. 当前 Active Generation 在替代代完整通过前持续提供服务。
6. 重建采用新代写入和原子激活，不能原地破坏现有可用知识。
7. 所有对象、节点和关系写入必须幂等并具有内容或关系指纹。
8. 权限、Tenant、Customer、Product、有效期和状态先于语义排序执行硬过滤。
9. 模型生成的语义关系只形成候选。事实支持、冲突、替代和验证关系需要确定性证据或治理批准。
10. 二进制文件、备份、可执行物和不可信归档不能被执行。
11. 不可提取对象仍保留路径、类型、大小、原始 Hash、状态和稳定原因。
12. 每个阶段都需要生产规模测试、故障恢复、回滚和最终验收证据。

## 5. 目标数据平面

### 5.1 来源观察平面

保存 Local、UNC、Git、SVN、快捷方式、网页或其他连接器观察到的位置、Revision、权限状态、首次和最后观察时间。路径消失后保留历史位置和最后可用状态。

### 5.2 对象证据平面

通过 S3 兼容接口保存内容寻址对象：

* 允许留存时保存原始文件快照。
* 必须保存完整清洗对象。
* 保存 OCR 页面、结构化表格、规范文本和派生 Manifest。
* 对象键由 SHA 256 生成，数据库保存 Bucket、Key、Version、ETag、内容 Hash、加密和保留策略。
* RustFS 是首选验证对象存储。通过生产耐久性门以前，关键对象保留第二独立副本。

### 5.3 检索证据平面

PostgreSQL 保存 Document、Document Version、Processing Version、Chunk、代码符号、关系、路径语义、权限和当前状态。pgvector 保存语义表示。检索返回资源句柄、证据位置和版本，不把截断 Chunk 当作完整知识实体。

### 5.4 经验平面

经验是经过验证、带适用条件、带证据、能够失效的断言。至少支持：

* 事实经验。
* 操作经验。
* 定位经验。
* 失败模式。
* 决策经验。

每条经验保存 Tenant、Customer、Product、环境、版本、有效期、证据、置信度、验证方式、审批状态和替代链。

### 5.5 作业和反馈平面

保存问题、Task、检索候选、注入经验、引用证据、最终报告、测试、运行结果和用户纠正。它负责证明某条经验在什么上下文中是否有效。

### 5.6 关系网格

关系是带类型和上下文的边。第一批关系类型包括：

* `observed_as`
* `transformed_from`
* `partitioned_into`
* `supports`
* `contradicts`
* `derived_from`
* `applies_to`
* `supersedes`
* `used_in`
* `validated_by`
* `failed_in`
* `similar_to`

语义相似、证据强度、范围匹配、时效、验证结果和使用成功率分别保存，不能压缩为一个全局正负分数。

## 6. 全格式文本抽取策略

### 6.1 处理判定

处理入口从扩展名白名单升级为以下顺序：

1. 读取魔数和 MIME。
2. 检测文本概率、编码和二进制特征。
3. 结合扩展名、实际内容和容器结构确定处理器。
4. 在受限资源、无网络、只读输入和禁止执行的沙箱中抽取。
5. 输出规范文本、结构化位置、处理器版本、质量指标和稳定失败码。

扩展名继续作为线索和策略输入，不能成为唯一判定依据。

### 6.2 第一优先级格式

优先补齐现有数据中数量大且业务价值明确的格式：

* 旧 Office：`.doc`、`.xls`、`.ppt`。
* 邮件：`.eml`、`.msg`，附件作为独立子 Artifact。
* 富文本和帮助：`.rtf`、`.hlp`、`.chm`、`.oxps`。
* 图片 OCR：`.png`、`.jpg`、`.jpeg`、`.tif`、`.tiff`、`.bmp`、`.gif`。
* 文本型脚本和配置：`.bat`、`.vbs`、`.jsp`、`.org`、`.config`、`.resx`、`.csproj`、`.policy`、`.ctl`、`.cnf`、`.ovpn`、`.rdp`、无扩展文本及语言后缀资源。
* 报表定义和模板：`.rpt`、`.jrxml`、`.jasper` 中可安全解析的文本或结构元数据。

### 6.3 容器和归档

ZIP、7z、JAR、WAR、LZH 等容器默认先生成成员清单。满足以下条件时进入安全解包：

* 路径规范化通过，禁止路径穿越和设备文件。
* 压缩比、成员数、递归深度和总展开大小在限制内。
* 每个成员继承来源、权限和父 Artifact 关系。
* 可执行成员只保存元数据和 Hash。
* 可抽取成员继续走普通内容探测。

数据库备份和 Dump 默认保存对象、Hash、产品或格式探测结果和元数据。只有存在经过批准的只读解析器时才抽取架构和文本，禁止启动数据库或执行其中内容。

### 6.4 明确排除内容抽取的对象

以下对象默认只进入来源和对象清单：

* EXE、DLL、SO、CLASS、APP、MSI、OCX 和内核模块。
* PDB、LIB、编译缓存和纯机器码。
* 私钥、证书容器和凭据文件的正文。
* 无法通过资源限制安全展开的归档。
* 合同、隐私或权限政策禁止复制的原始文件。

如果二进制中存在可安全解析的签名、版本、导入表或字符串，只能由单独批准的元数据分析器产生结构化证据，不能把任意字符串扫描结果直接作为可信正文。

## 7. 现有知识转换和重建策略

### 7.1 冻结转换清单

为每个 Source Entry 生成不可变的 `ConversionManifestItem`，记录当前 Source Entry、Raw Hash、Document、Processing Version、Chunk、对象状态和目标动作。动作只能是：

* `reuse`：现有 Document、Chunk、向量和处理指纹完整可用。
* `backfill_object`：现有清洗结果可信，只补建清洗对象和关系。
* `reclean`：新处理器可改善结果，重新清洗并建立新 Processing Version。
* `reindex`：清洗对象可复用，重建 Chunk、embedding 或关系。
* `path_only`：没有正文，路径本身有知识价值。
* `safe_unpack`：受控枚举和抽取容器成员。
* `metadata_only`：不可或不应抽取正文。
* `blocked`：来源不可读或证据不足，需要人工处理。

### 7.2 转换优先级

1. 已 indexed 且来源仍可读的数据先补建对象副本和双向关系。
2. 已 indexed 且来源已失联的数据从现存加密 Chunk 和版本记录重建清洗对象，标记为 `recovered_from_index`，不能伪装成完整原文件。
3. observed 项按冻结 Manifest 继续处理，不能依赖活动 Ingestion 的中间状态下结论。
4. rejected 项按新处理器和稳定原因重试。
5. unsupported 项进行 MIME 和内容探测，能抽取文本的进入新处理链。
6. metadata-only 项根据新策略重新分类，二进制和策略排除继续保留元数据。
7. removed 项保留历史对象和关系，不进入当前检索。

### 7.3 新代构建与切换

每个 Source 构建独立的新 Generation：

1. 读取冻结 Manifest。
2. 按文件工作项执行对象保存、清洗、质量验证和索引。
3. 计算覆盖率、对象闭合率、引用闭合率和失败分布。
4. 对新旧检索执行影子对比。
5. 新代全部质量门通过后原子激活。
6. 旧代进入历史状态并保留回滚期。

不得在重建中删除现有 Active Chunk 或提前改写当前路径。

## 8. 图存储选型计划

### 8.1 当前决定

PostgreSQL 继续作为关系真相。第一阶段以有类型邻接表、组合索引、pgvector 候选和限定一至三跳查询实现关系网格。图查询能力通过统一 `GraphProjectionStore` 接口隔离。

### 8.2 基准候选

按相同数据和查询集比较：

1. PostgreSQL 邻接表和递归 CTE。
2. PostgreSQL 加 Apache AGE。
3. 独立图数据库候选。

独立图数据库只保存可重建投影。PostgreSQL Outbox 提供节点和关系变更，图投影 Worker 保存水位、校验和与重放状态。

### 8.3 基准规模

* 100 万节点，500 万边。
* 500 万节点，5000 万边。
* 2000 万节点，2 亿边。

每档测试范围过滤的一跳、两跳支持证据、三跳任务路径、冲突定位、最短可信路径、源文件变化影响分析、批量失效和并发写入。

### 8.4 切换门

基础目标：直接关系 P95 小于 100 ms，一跳小于 200 ms，两跳小于 500 ms，三跳候选生成小于 1 秒。连续两档数据下超过目标两倍、查询计划不稳定、图写入干扰业务事务或图算法成为常态时，引入独立图数据库。

## 9. RustFS 和对象存储计划

应用只依赖 S3 兼容的 `ArtifactObjectStore`，不暴露 RustFS 专用 API。对象写入采用先上传、校验 Hash、提交数据库引用的协议。孤立对象由对账任务识别，不能被普通检索使用。

RustFS 验收必须覆盖：

* PUT、GET、HEAD、LIST、multipart 和版本化兼容性。
* 并发幂等写、重复 Hash 去重和读取一致性。
* TLS、凭据轮换、最小权限和审计。
* 单盘损坏、节点退出、网络分区、断电和自愈。
* 备份、恢复、升级、降级和对象 Hash 全量抽样校验。
* 100 KB、10 MB、100 MB 和大对象负载。
* 至少七天持续写入、读取和恢复演练。

RustFS 达到稳定版本且分布式能力通过本地验收以前，关键证据保留第二独立副本。对象存储不可用时，现有 Active Generation 继续可检索；需要打开完整对象的任务返回明确的 `artifact_unavailable`，不能用概念节点伪装成证据可用。

## 10. 经验使用闭环

1. Task 完成后从最终报告、Citation、测试和运行结果中生成经验候选。
2. Validator 检查证据闭合、范围、有效期、秘密、隐私和独立验证。
3. 批准的经验建立 embedding 和有类型关系。
4. 新 Task 先解析范围和意图，再检索适用经验。
5. Codex 接收精简 Experience Packet 和可打开的 Artifact URI。
6. Task 记录候选、注入、实际引用、冲突、忽略和最终结果。
7. 相同来源的重复引用不算独立验证。
8. 新版本、来源 Hash 改变、失败或用户纠正触发重新评估。
9. 新经验通过 `supersedes` 替代旧经验，旧经验继续支持历史查询。

## 11. 分阶段实施计划

### 阶段 0：基线冻结与指标契约

目标：得到可重复的生产基线和逐文件闭环清单。

交付：

* Source、Entry、Document、Version、Chunk、失败和对象覆盖报表。
* 状态语义修订，区分 discovered、queued、processing、indexed、metadata-only、rejected 和 blocked。
* 文件格式和 MIME 分布报表。
* 检索、两跳关系和对象读取 SLO。
* 迁移 Manifest schema 和 dry-run 工具。

验收：每个 Source Entry 恰好有一个终态或活动工作项；所有聚合计数能够反查物理 ID；不再使用 `observed` 同时表达多个生命周期阶段。

### 阶段 1：对象证据基础

目标：建立内容寻址对象模型和 RustFS 兼容适配器。

交付：Artifact、ArtifactLocation、Transformation、ObjectReplica、完整性对账、S3 适配器和第二副本策略。

验收：已选样本的原始或清洗对象可通过 Hash 读取；断开原路径后仍能从对象存储打开清洗证据；数据库和对象引用零孤儿；恢复演练通过。

### 阶段 2：通用内容探测和提取器框架

目标：所有可安全抽取文本的文件进入清洗流程。

交付：MIME 和魔数探测、文本概率探测、沙箱 Worker、资源限制、处理器注册表、稳定错误码、旧 Office、邮件、RTF、图片 OCR 和文本型配置处理器。

验收：格式语料库逐类通过；二进制永不执行；归档炸弹和路径穿越被拒绝；每个失败都有处理器、版本、原因和可重试性。

### 阶段 3：现有知识转换与新代重建

目标：把现有索引转化为对象闭合的新知识代，并补处理历史遗漏。

交付：Conversion Manifest、对象回填、重清洗、重索引、影子检索、原子激活和回滚工具。

验收：所有当前 Source Entry 进入转换终态；所有 indexed Chunk 能反查 Clean Artifact；所有 Artifact 能反查 Source Observation；旧代在新代完整验收前保持可用；切换后检索回归不下降。

### 阶段 4：证据、经验和作业关系网格

目标：建立统一节点和有类型关系层。

交付：NodeRef、TypedRelation、RelationEvidence、Applicability、Outbox、图投影接口、冲突和影响分析。

验收：证据到经验到任务再回到结果的正反链路全通；权限和范围过滤零泄漏；关系写入幂等；来源变化能列出受影响经验。

### 阶段 5：经验检索和 Codex 注入

目标：批准经验实际参与后续任务。

交付：经验 embedding、混合召回、Experience Packet、Task 注入、使用回执、再验证和替代状态机。

验收：匹配任务能检索批准经验；未批准、过期、冲突和跨客户经验不会进入上下文；最终报告记录实际使用；回放集完成质量、延迟和引用对比。

### 阶段 6：图引擎基准与选择

目标：根据规模和查询事实选择 PostgreSQL、AGE 或独立图数据库。

交付：三档数据生成器、统一查询集、并发测试、恢复测试、成本和运维报告、最终 ADR。

验收：选型满足 SLO、权限、备份、恢复、重建和故障降级；独立图数据库只能作为可重建投影。

### 阶段 7：持续学习和治理上线

目标：形成稳定的自增益闭环。

交付：冲突面板、经验有效期、复验队列、对象完整性巡检、图投影巡检、质量趋势、回滚和 Gardener。

验收：重复来源不会产生虚假独立验证；用户纠正能触发经验修订；对象或图故障不会破坏业务真相；定期恢复演练通过。

## 12. 质量指标

最终验收不能使用 Chunk 数量替代业务效果。持续监控至少包括：

* Source Entry 终态闭合率。
* 可抽取文本覆盖率。
* Raw Hash 覆盖率。
* Clean Artifact 覆盖率。
* Chunk 到对象和来源的双向引用闭合率。
* 图片和扫描 PDF OCR 覆盖率。
* 稳定失败原因覆盖率。
* 当前资料召回率和历史资料误召回率。
* Citation 覆盖率和引用正确率。
* 经验适用范围正确率。
* 跨 Tenant 和 Customer 泄漏率。
* 经验实际使用率、成功率和纠正率。
* 对象完整性、第二副本和恢复成功率。
* 一到三跳图查询 P50、P95 和 P99。
* 同类任务第二次完成所节省的时间。

硬门包括：权限泄漏为零，当前资料中历史误召回为零，强引用孤儿为零，已声明成功处理的文件无未解释失败，Active Generation 切换具备完整回滚证据。

## 13. 风险和控制

| 风险 | 控制 |
|---|---|
| 错误经验自我强化 | 独立证据计数、候选审批、任务上下文反馈和冲突保留 |
| 原路径丢失 | 内容寻址对象、第二副本和定期恢复演练 |
| 对象存储未成熟 | S3 抽象、RustFS 兼容门、第二故障域副本 |
| 图数据库双写不一致 | PostgreSQL 真相、Outbox、投影水位和可重建图 |
| 重建破坏现有检索 | 新 Generation、影子验证、原子激活和旧代回滚 |
| 格式扩展带来攻击面 | 无网络沙箱、只读输入、资源上限、禁止执行和稳定审计 |
| OCR 或转换错误 | 原始对象、页面位置、质量分数和人工抽样复验 |
| 存储快速膨胀 | 内容去重、生命周期策略、对象分层和基于政策的原始快照保留 |

## 14. 下一实施目标

下一版本应只实施阶段 0，不同时引入对象存储、图数据库和全部提取器。阶段 0 的完成条件是获得一份生产可复跑的 `Conversion Manifest`、正确的状态模型、格式能力矩阵和基准测试数据集。该结果将决定阶段 1 和阶段 2 的具体版本拆分及容量预算。

## 15. 当前技术资料

本路线图的时效性产品判断在 2026-08-13 依据以下官方资料形成，实施每个阶段前必须重新核对：

* RustFS Documentation: https://docs.rustfs.com/
* RustFS Architecture: https://docs.rustfs.com/concepts/architecture
* RustFS official repository and release status: https://github.com/rustfs/rustfs
* MinIO official repository and Community Edition distribution status: https://github.com/minio/minio
* Apache AGE official repository and PostgreSQL compatibility: https://github.com/apache/age
* PostgreSQL recursive query documentation: https://www.postgresql.org/docs/current/queries-with.html
