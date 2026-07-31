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

待完成提交、推送、Alembic 升级、Gateway 重启和前端镜像切换后补充。
