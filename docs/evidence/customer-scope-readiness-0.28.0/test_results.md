# Test results

| Verification | Result | Evidence |
| --- | --- | --- |
| Knowledge and full backend | Passed | 177 collected, 174 passed, 3 skipped, 85.06 percent coverage |
| Frontend | Passed | 3 files and 17 tests passed |
| Frontend production build | Passed | TypeScript and Vite build completed |
| Host API runtime | Passed | `/health/ready` reports 0.28.0, PostgreSQL, Redis and native vector search ready |
| Docker frontend | Passed | Container rebuilt and healthy on port 5173 |
| Production Scope Repair | Passed | Ingestion `8896eeee-0e2a-4804-bd40-1a0f732a1867`, 470 files, 469 unchanged, 3,010 vectors reused |
| Production terminal extraction | Passed | `4cd21c2e-e62f-40cb-8560-4342f29bc794`, 470 terminal, 269 analyzed, 201 excluded, zero failed, coverage 1.0 |
| Hash and reference closure | Passed | 470 of 470 raw hashes, 269 Document and Processing Version pairs, zero orphan queries |
| Shortcut provenance | Passed | Eight hashed observations and 22 indexed flattened targets with durable provenance |
| OneOps Gateway | Passed | 228 tests passed |
| OneOps Builder | Passed | 14 tests passed |
| OneOps Portal | Passed | 27 files and 187 tests passed; production build passed |
| OneOps Browser title | Passed | Formal HTTPS title is `OneOps | 導入・保守・支援ワークセンター` |
| OneOps DOM, Console and screenshot | `evidence_missing` | In-app Browser communication timed out twice; static Bundle and Health checks passed |
