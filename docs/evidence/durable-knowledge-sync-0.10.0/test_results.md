# Test results

| Check | Result |
|---|---|
| Scheduler and knowledge API tests | Passed, 14 tests |
| Alembic targeted migration test | Passed, 1 test |
| Complete backend suite | Passed, 70 tests |
| Backend coverage | Passed, 86.83 percent |
| Frontend component and API tests | Passed, 11 tests |
| Frontend TypeScript and production build | Passed |
| Git whitespace validation | Passed |
| Live Alembic upgrade | Passed, `20260728_0010` head |
| Compose configuration and image build | Passed |
| Host Gateway readiness | Passed, version 0.10.0 on `0.0.0.0:8000` |
| Real local Ollama first scheduled run | Passed, one changed file and one new vector chunk |
| Real local Ollama idempotent scheduled run | Passed, zero chunks written, one unchanged file and one vector reused |
| Persisted source schedule | Passed, 15 minute interval with next due time |
| Browser route and source history | Passed on `http://127.0.0.1:5173/knowledge` |
| Browser console warnings and errors | Passed, zero entries |
| Browser screenshot | Passed, `docs/evidence/screenshots/durable-knowledge-sources-0.10.0.jpg` |
