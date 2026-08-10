# 验证命令

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest

cd D:\workspace\cag\frontend
D:\nginx\runtime\node\pnpm.cmd test
D:\nginx\runtime\node\pnpm.cmd build

cd D:\workspace\cag
git diff --check
```
