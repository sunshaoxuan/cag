# 执行命令

1. `D:\workspace\cag\backend\.venv\Scripts\python.exe -m pytest`
2. `D:\workspace\cag\backend\.venv\Scripts\python.exe -m alembic current`
3. `Invoke-RestMethod http://127.0.0.1:8000/health/live`
4. `Invoke-RestMethod http://127.0.0.1:8000/health/ready`
5. `Invoke-RestMethod http://127.0.0.1:8000/api/v1/queue/status`
6. OneOps `createCustomerKnowledgeScanService.start("2", ...)`
7. OneOps `createCustomerKnowledgeScanService.reanalyze("2", parentScanId, ...)`
8. `git diff --check`

命令输出中不记录凭据、Token、联系人或秘密字段原值。
