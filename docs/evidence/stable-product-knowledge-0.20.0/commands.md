# Commands

| Command | Purpose |
|---|---|
| `python -m pytest tests/test_knowledge.py tests/test_migrations.py` | Focused knowledge and migration validation |
| `python -m pytest` | Complete backend regression and coverage gate |
| `pnpm test -- --run` | Frontend component regression |
| `pnpm build` | TypeScript and production bundle |
| `alembic upgrade head` | Isolated PostgreSQL migration |
| Browser console and screenshot inspection | Management UI acceptance |
| `git diff --check` | Release diff validation |
