# Evidence index

| Evidence | Purpose |
|---|---|
| `backend/app/knowledge/service.py` | Credential lookup by source physical UUID |
| `backend/app/api/knowledge.py` | Explicit reveal endpoint and cache prevention headers |
| `backend/tests/test_knowledge.py` | Exact secret reveal, headers and cleared-credential behavior |
| `frontend/src/App.tsx` | Edit loading, masking, display and copy behavior |
| `frontend/src/App.test.tsx` | Component-level exact-value and clipboard verification |
| `docs/adr/0011-managed-source-credential-reveal.md` | Decision and security boundary |
| `docs/evidence/screenshots/credential-reveal-0.11.0.jpg` | Live browser acceptance with the secret masked |
| `test_results.md` | Automated and live validation results |
| `FINAL_RECEIPT.md` | Release acceptance and rollback receipt |
