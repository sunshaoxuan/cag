# 0.22.4 发布回执

状态：验证完成，等待生产切换

## 交付

* 后端状态机和 reopen 控制
* 问题事件分页 API
* 前端选择竞态保护
* 问题级表单和操作反馈
* `validation_completed` 数据迁移
* 在线 API 文档和调用范例
* 自动化测试与浏览器证据

## 回滚

* 应用回滚到 0.22.3。
* Alembic 降级到 `20260731_0018` 时，`validation_completed` 发布验证记录恢复为 `rejected`。
* 问题 occurrence、artifact 和 event 历史不删除。
