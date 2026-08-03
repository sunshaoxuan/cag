# 0.22.6 发布回执

本版本修复代码事实浏览器搜索表单的按钮垂直对齐问题。变更已通过前端组件测试、生产构建、后端完整测试、Docker 前端重建，以及桌面和窄屏浏览器验证。

前端容器已刷新到 0.22.6。Gateway 主进程仍运行 0.22.5，因为知识队列有一个 Worker 正在处理任务，重启被延后以保护活动任务。源码和发布文件已完成 0.22.6 验证。

验证截图：

* `docs/evidence/screenshots/code-knowledge-search-action-0.22.6-desktop.png`
* `docs/evidence/screenshots/code-knowledge-search-action-0.22.6-mobile.png`
