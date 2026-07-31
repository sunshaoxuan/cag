# 证据索引

| 结论 | 证据 | 可信度 | 限制 |
|---|---|---|---|
| 0.22.0 真实摘要为英文 | `operational-decision-brief-0.22.0` 生产截图和问题 API | 高 | 历史证据保留原文 |
| 新结构要求 `zh-CN` | `backend/app/operations/schemas.py` | 高 | 语言代码本身不能证明正文为中文 |
| 主要正文执行中文校验 | `backend/app/operations/service.py` | 高 | 技术标识允许保留原文 |
| 英文正文会关闭审批 | `backend/tests/test_operations.py` | 高 | 使用隔离 FakeAgentRuntime |
| 页面支持中文摘要 | `frontend/src/OperationsCenterPage.tsx` 与组件测试 | 高 | 生产内容需发布后重新规划验证 |
