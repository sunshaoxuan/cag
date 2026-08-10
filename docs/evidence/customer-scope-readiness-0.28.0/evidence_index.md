# Evidence index

| Claim | Evidence | Confidence | Limitation |
| --- | --- | --- | --- |
| Historical paths produced current candidates in the baseline | Baseline extraction `a8b3a50a-7cb6-421e-972e-3d1a21a63cc0` and OneBridge investigation log | High | Point in time baseline |
| All failed TXT inputs were readable | Direct extractor verification with 37 matching raw SHA 256 values | High | Restricted to the reported 37 files |
| Shortcut parsing follows the Shell Link structure | Microsoft MS-SHLLINK and CommonNetworkRelativeLink specifications, LnkParse3 1.6 | High | Target reachability depends on worker identity |
| Physical directory coverage stops repeated traversal | `backend/app/knowledge/connectors.py` and `backend/tests/test_knowledge.py` | High | Junction traversal remains disabled by collection policy |
| Scope Repair executes before Manifest creation | Final extraction `4cd21c2e-e62f-40cb-8560-4342f29bc794` has started and completed events before `manifest.completed` | High | Point in time production run |
| Current TXT readiness is repaired | Production Manifest has 34 current TXT entries, all `ready`, and zero `NOT_INGESTED` | High | Nine additional TXT entries are intentionally historical |
| Shortcut provenance is durable | Eight `.lnk` entries have raw hashes and typed observations; 22 indexed target files retain `shortcut_target_flattened` after repeated repair | High | Targets outside the approved root remain observations only |
| Raw provenance is complete | Final Scope has 470 files and 470 raw hashes | High | One damaged historical XLSX has no cleaned content hash |
| Document and Chunk references are closed | 269 analyzed rows have Document Version and Processing Version; orphan and broken reference queries return zero; PostgreSQL foreign keys are present | High | Applies to the final production database snapshot |
| Long UNC path and large PDF are usable | 261 character SQL and 17 MB PDF are both indexed and analyzed with raw and cleaned hashes | High | Files above 100 MB remain metadata-only with raw hash |
| Terminal extraction is complete | 470 terminal rows, 269 analyzed, 201 excluded, zero failures, coverage 1.0, 620 model activity events | High | Candidate review remains a business action |
| OneOps static release is deployed | HTTPS Health 0.16.4 and deployed Bundle includes all three processing-detail labels | High | Browser DOM, Console and screenshot are `evidence_missing` due repeated timeout |
