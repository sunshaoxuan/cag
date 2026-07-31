# 0.22.4 发布回执

状态：已发布并完成生产验证

## 交付

* 后端状态机和 reopen 控制
* 问题事件分页 API
* 前端选择竞态保护
* 问题级表单和操作反馈
* `validation_completed` 数据迁移
* 在线 API 文档和调用范例
* 自动化测试与浏览器证据

## 发布

* release commit：`97cbc68`
* `origin/master`：已推送
* Gateway：`0.22.4`，ready
* listener：`0.0.0.0:8000`
* 管理前端：HTTP 200
* 数据迁移：Alembic `20260731_0019`
* 发布时队列：无 queued、无 leased
* 生产浏览器：选择稳定、分页时间线和 API 文档通过，控制台无错误或警告

## 回滚

* 应用回滚到 0.22.3。
* Alembic 降级到 `20260731_0018` 时，`validation_completed` 发布验证记录恢复为 `rejected`。
* 问题 occurrence、artifact 和 event 历史不删除。
