# コマンド記録

## 調査

```powershell
Get-Content AGENTS.md -Raw
git status --short --branch
git diff --stat
rg -n "KnowledgeScheduler|claim_due_source|StreamingResponse|get_session" backend
```

## 専用テスト

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest tests/test_sse_session_lifetime.py tests/test_knowledge.py::test_scheduler_skips_sources_with_active_ingestions tests/test_knowledge.py::test_scheduler_treats_reused_active_ingestion_as_idle tests/test_knowledge.py::test_scheduler_lease_prevents_duplicate_claim_and_failure_is_retried tests/test_knowledge.py::test_scheduler_loop_survives_one_iteration_failure tests/test_conversations_api.py::test_unknown_conversation_returns_404 tests/test_tasks_api.py::test_missing_task_returns_404 --no-cov -q
```

結果は 8 passed だった。

## 全 backend テスト

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest
```

最終再実行結果は 182 passed、4 skipped、coverage 85.10% だった。

## PostgreSQL 並行試験

専用 Test Database を作成し、`test_postgresql_closes_claim_to_create_race` を実行した。結果は 1 passed だった。接続情報は記録せず、Test Database は試験直後に削除した。

## Compose と差分検査

```powershell
cd D:\workspace\cag
@'
from pathlib import Path
import yaml
compose = yaml.safe_load(Path('docker-compose.yml').read_text(encoding='utf-8'))
values = {name: compose['services'][name].get('restart') for name in ('postgres', 'redis')}
assert values == {'postgres': 'unless-stopped', 'redis': 'unless-stopped'}, values
print(values)
'@ | .\backend\.venv\Scripts\python.exe -
git diff --check
git status --short --branch
```

restart policy は両 service とも `unless-stopped`、`git diff --check` は合格だった。
