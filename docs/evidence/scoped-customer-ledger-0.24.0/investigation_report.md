# Scope 指定客户台账抽取调查报告

更新日：2026-08-06

## 调查目标

实现 `D:\nginx\docs\CAG_SCOPED_CUSTOMER_LEDGER_EXTRACTION_REQUIREMENTS.md` 中由 CAG 负责的 Scope 解析、全文件 Manifest、逐文件抽取、证据、冲突、版本和永久历史要求。

## 关键结论

1. 原有 schema v2 依赖 Section 检索，无法证明 Scope 下文件全量覆盖。现行接口改为 schema v1，由 Source 物理 ID、组织机构 Subject 物理 ID 和 Catalog 策略解析 Scope。
2. Source Entry、Document Version、Processing Version、Knowledge Block Version 和 Applicability Revision 必须分轴保存。Processor 更新不改变业务适用期。
3. SQLite 返回的无时区时间需要先按 UTC 规范化，再与带时区 `analysis_context.as_of` 比较。
4. 全量 Scope 中单个模型超时必须收敛到 Task Document。整个 Task 继续处理后续文件，并以 Coverage 和 `EXTRACTION_PARTIAL` 报告结果。
5. 筑波大学正式 Scope 为 `つ_0408_筑波大学/`，物理 Scope ID 为 `6ea2f756-ac3e-4ae9-b154-8c6e2ace8ea3`。正式扫描的 Manifest 为 296 项。

## 实现结果

目标 API、迁移、模型、Worker、幂等、稳定错误、完整 Schema Registry、永久历史和时点适用性均已实现。第三轮正式扫描进入 `REVIEW_REQUIRED`，Coverage 为 0.345794，分析成功 37 项，文件失败 70 项，排除 189 项。失败项包含未取込、Metadata Only 和模型超时，均保留文件级原因。

OneOps Browser 已完成系统管理知识源设置、筑波大学扫描概要、Candidate Evidence、Conflict、Unresolved、Document Failure 和 Applied 状态验收。正式 Apply 的物理台账与审计均合格，应用 Console Warning 和 Error 为 0。

最终全量 pytest 首轮发现人工评估失败后的新 Triage 周期可能复用即将释放的旧 Lease。显式重处理现创建新的 Queue Item，目标回归和 151 项全量 pytest 均已通过。
