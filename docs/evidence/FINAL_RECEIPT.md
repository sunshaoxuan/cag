# 現行リリース回収

バージョン: 0.28.2

日付: 2026-08-10

ブランチ: `master`

状態: 本番適用前検証合格

## 実装内容

* PostgreSQL と Redis の Compose Service に `unless-stopped` RestartPolicy を設定しました。
* Windows Supervisor は Gateway liveness と依存 readiness を分離して監視します。
* Gateway プロセス障害は有界回数後に再起動し、PostgreSQL、pgvector 又は Redis 障害は別の運用障害として記録します。
* Knowledge Scheduler は active Ingestion を claim 対象から除外し、Source 行 Lock 内で Scheduled 作成を再確認します。
* Task と Conversation SSE の初期確認 Transaction は StreamingResponse 返却前に終了します。
* 公開バージョンの整合性検査対象を README、API 文書、要件表及び Changelog へ拡張しました。

## 本番適用前の検証

* Backend は 182 件合格、4 件 Skip、Coverage 85.10 percent です。
* 専用 PostgreSQL 並行 Test は 1 件合格し、Test Database は試験後に削除しました。
* Frontend は 17 件合格し、TypeScript 及び本番 Build も合格しました。
* PowerShell 監督試験は 11 件合格しました。
* Docker Compose 構文と Git Diff 整合性は合格しました。

## 本番適用ゲート

正式完了の前に以下を実施します。

1. `origin/master` へ Commit と Push を行います。
2. PostgreSQL と Redis を Compose 再調整し、RestartPolicy、Volume 及び Health を確認します。
3. 8000、8001 及び 8002 の Supervisor 任務を再登録します。
4. 3 系統の 0.28.2 Ready と OneOps 経由の Session 取得を確認します。
5. 5173 管理画面、Console 及び Screenshot を確認します。

## Rollback

0.28.1 の Commit を再配信し、PostgreSQL と Redis の RestartPolicy を元に戻します。`manage-local-codex-gateway-task.ps1 stop` で対象 Supervisor を停止し、必要に応じて以前の Task Action を再登録します。既存 PostgreSQL、Redis 及び Workspace Volume は削除しません。
