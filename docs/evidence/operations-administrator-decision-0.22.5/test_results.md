# 0.22.5 测试结果

日期：2026-08-03

## 后端

命令：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

结果：

* 119 passed
* 2 skipped
* 85.65% coverage
* 5 个 Python 3.12 SQLite datetime adapter 弃用警告
* 问题中心定向用例 10 项功能通过；单文件运行产生的全仓覆盖率门禁失败由完整测试消除

## 前端

命令：

```powershell
cd frontend
node node_modules/vitest/vitest.mjs run
node node_modules/vite/bin/vite.js build
```

结果：

* 3 个测试文件通过
* 17 个组件测试通过
* 问题中心定向组件测试 4 项通过
* 生产构建通过
* JavaScript 447.80 kB，gzip 132.24 kB
* CSS 46.18 kB，gzip 10.00 kB

## 浏览器

等待生产发布后验证问题顶部决策区、100 次发生计数、两个管理员动作、API 文档和控制台。
