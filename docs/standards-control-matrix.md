# AI and RAG standards control mapping

This matrix records engineering alignment and evidence. It is not a certification claim.

| Reference | Control objective | CAG 0.22.2 evidence | Status |
|---|---|---|---|
| NeurIPS RAG | Separate parametric Agent reasoning and non-parametric knowledge | `docs/enterprise-knowledge.md`, KnowledgeSource and KnowledgeChunk | Implemented |
| ISO/IEC 42001 | Defined AI system boundary, ownership and continual improvement | OperationalIssue boundary decisions, approval, evaluation, Promotion state machine, GardenerRun, installation receipts | Implemented mapping |
| ISO/IEC 23894 | Risk identification and treatment records | OperationalIssue occurrences, severity, treatment plan, Review, evaluation, RiskRecord and rollback trigger | Implemented mapping |
| ISO/IEC 5259 | Source provenance and measurable data quality | source entry inventory, source commit, content hash, processor fingerprint, detected encoding, parser evidence, file-level rejection audit, DataQualityMetric | Implemented mapping |
| ISO/IEC 27001 | Confidentiality, integrity and availability controls | AES GCM text, keyring boundary, permission and secret gates, authenticated operations mutations | Implemented mapping |
| NIST AI RMF | Govern, Map, Measure and Manage evidence | controls API, evaluation metrics, promotion and rollback | Implemented mapping |
| OWASP LLM Top 10 | Prompt Injection, secret and knowledge poisoning controls | source scanner, capability scanner and context isolation | Implemented mapping |

The statuses describe verifiable engineering control mappings. They do not
state that the project or operator has obtained third party certification.
