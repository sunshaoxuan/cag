# 0.22.5 命令记录

## 调查

```powershell
git status --short
git branch --show-current
rg -n "plan_revision_required|allowed_actions|reopen|approve|reject" backend frontend docs
Invoke-RestMethod http://127.0.0.1:8000/api/v1/operations/issues
Invoke-RestMethod http://127.0.0.1:8000/api/v1/queue/status
```

## 验证

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest

cd ..\frontend
node node_modules/vitest/vitest.mjs run
node node_modules/vite/bin/vite.js build

cd ..
git diff --check
git status --short
```

## 发布

等待所有队列 queued 和 leased 归零后，通过受监督的本地主机 Gateway 管理脚本重启 8000，并由启动流程执行前端重建。生产页面通过 5173 同源入口验证。
