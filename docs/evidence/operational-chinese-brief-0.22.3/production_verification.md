# 0.22.3 生产验证

日期：2026-07-31

## 发布

* release commit：`53ff2f3`
* branch：`master`
* remote：`origin/master`
* Gateway version：`0.22.3`
* readiness：`ready`
* listener：`0.0.0.0:8000`
* backend：PostgreSQL
* vector database：pgvector `0.8.2`
* frontend：HTTP 200，容器状态 `healthy`
* supervisor：`Running`
* auto start：启用
* restart count：999

发布前 operations 队列存在一个活动 lease，对应
`OI-10CE919F81` 第 3 次自动重试。发布等待该任务自然完成，最终队列记录为
9 项完成、1 项失败，没有 queued 或 leased 项。

## 活动问题

### OI-6B26534BF5

* plan revision：4
* Review revision：4
* 两项 artifact 的 `structured_output_valid` 均为 `true`
* `administrator_language`：`zh-CN`
* 检查 89 个管理员叙述字段，缺少中文字段为 0
* 新工作区：`op-ec0a212a-t2-s178`
* workspace HEAD：`fe8f7ec`
* workspace VERSION：`0.22.2`

### OI-10CE919F81

* 第一次真实重新规划发生可恢复分块错误：
  `Separator is not found, and chunk exceed the limit`
* 第 3 次队列尝试完成 plan 与独立 Review
* plan revision：4
* Review revision：4
* 两项 artifact 的 `structured_output_valid` 均为 `true`
* `administrator_language`：`zh-CN`
* 检查 93 个管理员叙述字段，缺少中文字段为 0
* `required_human_input` 包含中文操作说明

两个活动问题的最终状态均为 `plan_revision_required`。这是独立 Review 对
证据与方案完整性的判断，语言门禁没有触发失败回退。

## 浏览器

访问 `http://127.0.0.1:5173/operations`：

* 页面标题显示 `One Agent Gateway v0.22.3`
* 两个活动问题均可打开中文审核决策摘要
* 技术路径、错误码和原始错误保留原文
* 浏览器控制台错误和警告数量为 0
* 截图：
  `screenshots/operations-runtime-failure-0.22.3.png`

## 回滚

恢复 `53ff2f3` 之前的应用提交并重新构建前端，然后重启受监督 Gateway。
本版本没有数据库迁移。问题 artifact、事件和中文决策摘要继续作为审计
证据保留。
