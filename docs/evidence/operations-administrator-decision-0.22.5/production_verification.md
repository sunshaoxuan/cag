# 0.22.5 生产验证

日期：2026-08-03

状态：通过

## 发布状态

* 发布提交：`8d1b2bd feat: add administrator issue decisions`
* `/health/ready`：`ready`
* 运行版本：`0.22.5`
* 后端：PostgreSQL，pgvector `0.8.2`
* Redis：已连接
* Gateway：监听 `0.0.0.0:8000`
* 前端：`5173` 返回生产页面
* `CAG Local Codex Gateway`：Running、Enabled、RestartCount `999`
* 启动触发器：系统启动和管理员登录

## 队列切换门禁

发布前确认 interactive、knowledge、operations 均无 queued、leased 或 working 项。发布后四个 worker 均为 idle，队列无等待项。

## 生产状态机

| 问题 | 发生次数 | 状态 | 服务端允许动作 |
| --- | ---: | --- | --- |
| `OI-10CE919F81` | 100 | `plan_revision_required` | `reopen,reject` |
| `OI-6B26534BF5` | 2 | `plan_revision_required` | `reopen,reject` |
| `OI-E23F303DCC` | 1 | `validation_completed` | `reopen` |

前两项验证了发生次数只影响展示的影响度和优先级，不改变管理员权限。

## 生产页面

问题中心顶部显示管理员决策区。方案待修订状态提供以下入口：

* 要求修订并重新 Review
* 不允许修改并结束

页面明确说明发生次数不改变管理员决策权限。管理员决策区在问题事实和 AI 审核摘要之前。API 在线文档包含拒绝调用范例。两个页面的浏览器控制台均为零 warning、零 error。

截图：`screenshots/operations-administrator-decision.png`
