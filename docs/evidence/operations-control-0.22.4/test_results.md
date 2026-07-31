# 0.22.4 测试结果

日期：2026-07-31

## 后端

命令：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

结果：

* 119 passed
* 2 skipped
* 85.78% coverage
* 5 个 Python 3.12 SQLite datetime adapter 弃用警告

覆盖内容包括状态动作、rejected 重新提交、重复 reopen 拒绝、事件序号分页、迁移升级和降级、队列失败原子状态。

## 前端

命令：

```powershell
node node_modules/vitest/vitest.mjs run
node node_modules/vite/bin/vite.js build
```

结果：

* 3 个测试文件通过
* 16 个组件测试通过
* TypeScript 和 Vite 生产构建通过
* 生产 JavaScript 约 445.97 kB，gzip 约 131.72 kB

## 浏览器

隔离端口：

* Gateway：127.0.0.1:8010
* 管理前端：127.0.0.1:5180

结果：

* 标题显示 One Agent Gateway v0.22.4。
* rejected 问题只显示后端允许的 reopen 操作。
* 无管理员凭据时，错误在当前操作区显示。
* 有效凭据重新提交后保留问题 ID 并进入新一轮处理。
* 时间线展开后加载当前 19 条事件。
* API 文档显示分页时间线和 reopen 范例。
* 问题中心和 API 文档控制台均无 warning 或 error。
