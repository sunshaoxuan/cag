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

在生产页面 `http://127.0.0.1:5173` 验证：

* 页面显示 `One Agent Gateway v0.22.5`
* `OI-10CE919F81` 显示“已发生 100 次”
* `OI-6B26534BF5` 显示“已发生 2 次”
* 两个问题都显示“要求修订并重新 Review”和“不允许修改并结束”
* 管理员决策区位于问题事实与 AI 审核摘要之前
* API 在线文档包含“禁止本轮修改并结束问题”和 `/reject` 范例
* 问题中心与 API 文档页面的浏览器控制台均无 warning 或 error
* 生产截图保存为 `screenshots/operations-administrator-decision.png`
