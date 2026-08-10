# Command record

1. `git diff --check`
2. `backend\.venv\Scripts\python.exe -m pytest -o addopts= tests/test_knowledge.py -q`
3. `backend\.venv\Scripts\python.exe -m pytest`
4. `frontend: pnpm test`
5. `frontend: pnpm build`
6. `scripts\manage-local-codex-gateway-task.ps1 -Action stop`
7. `scripts\manage-local-codex-gateway-task.ps1 -Action start`
8. `docker compose up -d --no-deps --build frontend`
9. `GET http://127.0.0.1:8000/health/ready`
10. `POST http://127.0.0.1:8000/api/v1/knowledge/extractions/customer-ledger`
11. PostgreSQL read only queries for extraction, ingestion, Manifest, TXT and shortcut evidence
12. PostgreSQL orphan, foreign key, raw hash, long path, large PDF and Shortcut provenance queries
13. In-app Browser title, DOM, Console and screenshot attempts for `https://192.168.20.54/`
