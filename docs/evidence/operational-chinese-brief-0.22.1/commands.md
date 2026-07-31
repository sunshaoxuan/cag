# 验证命令

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest `
  tests/test_operations.py tests/test_version.py tests/test_health.py `
  -q --no-cov

.\.venv\Scripts\python.exe -m pytest
```

```powershell
cd D:\workspace\cag\frontend
pnpm test
pnpm build
```

发布后验证包括健康端点、监听地址、队列状态、目标问题重新规划、问题 API、
浏览器 DOM、控制台和截图。
