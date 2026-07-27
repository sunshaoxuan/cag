# AI and RAG standards control mapping

This matrix records engineering alignment and evidence. It is not a certification claim.

| Reference | Control objective | CAG 0.5.0 evidence | Status |
|---|---|---|---|
| NeurIPS RAG | Separate parametric Agent reasoning and non-parametric knowledge | `docs/enterprise-knowledge.md`, KnowledgeSource and KnowledgeChunk | Implemented |
| ISO/IEC 42001 | Defined AI system boundary, ownership and continual improvement | ADR 0007, requirements matrix | Partial |
| ISO/IEC 23894 | Risk identification and treatment records | RiskRecord model, security document | Partial |
| ISO/IEC 5259 | Source provenance and measurable data quality | Source commit, hash, DataQualityMetric | Partial |
| ISO/IEC 27001 | Confidentiality, integrity and availability controls | AES GCM text, keyring boundary, persistent database | Partial |
| NIST AI RMF | Govern, Map, Measure and Manage evidence | architecture, risk and quality records | Partial |
| OWASP LLM Top 10 | Prompt Injection, secret and knowledge poisoning controls | source scanner and context isolation | Partial |
