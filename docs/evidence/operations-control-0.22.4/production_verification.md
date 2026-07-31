# 0.22.4 生产验证

日期：2026-07-31

## 隔离验证

* SQLite 数据库从空库升级到 Alembic 0019。
* 受控问题 `OI-108CE16346` 进入 waiting_approval。
* 管理员将问题设置为 rejected，接口返回 `allowed_actions: ["reopen"]`。
* 浏览器使用隔离管理员凭据重新提交同一问题。
* 问题追加 `issue.reopened` 并完成第二轮规划和 Review。
* 时间线总数从 10 增加到 19。
* 隔离进程和项目内临时目录已清理。

## 生产切换

* release commit：`97cbc68`
* branch：`master`
* remote：`origin/master`
* Gateway version：`0.22.4`
* readiness：`ready`
* listener：`0.0.0.0:8000`
* backend：PostgreSQL
* vector database：pgvector `0.8.2`
* frontend：HTTP 200
* supervisor：`Running`
* auto start：启用
* restart count：999

切换前，`OI-10CE919F81` 第 3 次分诊仍持有 operations lease。
发布等待该任务自然完成。最终问题状态为 `plan_revision_required`，
operations 队列为 10 项完成、2 项失败，没有 queued 或 leased 项，工作器
进入 idle 后才重启 Gateway。

Alembic `20260731_0019` 将 `OI-E23F303DCC` 从旧的 `rejected` 修正为
`validation_completed`，`approval_status` 为 `not_requested`。三个问题的
生产状态和动作如下：

* `OI-10CE919F81`：`plan_revision_required`，只允许 `reopen`。
* `OI-6B26534BF5`：`plan_revision_required`，只允许 `reopen`。
* `OI-E23F303DCC`：`validation_completed`，只允许 `reopen`。

详情接口不再返回 `events` 字段，改为返回 `event_count`。三个问题的
时间线总数分别为 4733、235 和 4465。每个问题的首个事件分页请求只返回
100 项，并提供 `has_more` 与 `next_before_sequence`。

## 生产浏览器

访问 `http://127.0.0.1:5173/operations`：

* 页面标题显示 `One Agent Gateway v0.22.4`。
* 总览显示 3 个问题、2 个方案待修订问题、0 个处理中问题。
* 选择 `OI-6B26534BF5` 后等待 6 秒，详情仍保持在同一物理问题。
* `OI-E23F303DCC` 显示“验证完成”和“重新提交问题处理”。
* 展开 4465 条事件的时间线后只渲染最新 100 项，并显示“加载更早事件”。
* API 文档显示“分页读取问题处理时间线”和“重新提交可恢复的问题”范例。
* 问题中心和 API 文档控制台 warning、error 均为 0。

## 回滚

恢复 0.22.3 应用提交并重建前端，随后将 Alembic 降级到
`20260731_0018`。降级会把 deployment-validation 记录恢复为旧的
`rejected` 状态，问题 occurrence、artifact 和 event 历史继续保留。
