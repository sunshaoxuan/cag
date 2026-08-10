# 最終受入記録

バージョン: `0.28.3`

日付: 2026-08-10 JST

ブランチ: `master`

実装 Commit: `e18fd222378f13462b6398ec6cc7bff1e5d2ad47`

状態: 実装、自動試験、本番 Runtime、Browser、Console、Screenshot の受入合格。正式 Git Tag は主タスクの Release Gate 待ち。

## 成果

* Knowledge Ingestion SSE の存在確認及び各 Poll は独立した短命 Database Session を使用する。
* Rejection CSV は500件単位の Keyset Pagination を使用し、Session を閉じてから各 Batch を出力する。
* 全5本の Streaming Route は Request Scope の `get_session` に依存しない。
* Frontend は企業知識画面だけで実行中 Ingestion の SSE を接続し、離脱時に閉じる。
* Page Generation Guard は離脱後に完了した Source GET 又は Ingestion POST による SSE 再接続を防ぐ。
* StrictMode 初回表示の Knowledge 関連取得は一組に統合される。

## 自動試験

* Backend: 186件合格、4件 Skip、Coverage 85.11%
* Frontend: 22件合格
* Frontend 本番 Build: 合格
* PowerShell: 11件合格
* Docker Compose: 合格
* Version 整合性 Focus Test: 1件合格
* 証拠文書日本語検査: 8文書、簡体字 Marker 0件

## 本番 Runtime 受入

* 8000、8001、8002 は全て `ready / 0.28.3` を返した。
* 8000 は PostgreSQL、Redis、Native Vector Search が正常で、pgvector は `0.8.2` だった。
* 5173 は `index-CMfzSW2Z.js` を配信し、公開 Version は `0.28.3` だった。
* `/audit` から `/knowledge` への遷移で Audit SSE と Ingestion SSE の接続置換を確認した。
* Ingestion SSE 接続中の PostgreSQL は `idle in transaction=0` だった。
* `/memory` 離脱後の8000番 Port Established 接続は0本だった。
* CAG Application の Console Warning と Error は0件だった。
* 安全な Screenshot は `browser-enterprise-knowledge-0.28.3.png` に保存した。
* Scheduler の20秒差分は Source 更新0件、API 3 Process CPU 増分0.062秒、PostgreSQL CPU 1.53%だった。
* PostgreSQL と Redis は同一 Image の隔離 Crash Test で各 `RestartCount=1` となり、再 Ready を確認した。現行 Container は停止していない。

## データ保護

既存の実行中 Ingestion は読取だけで確認し、状態を変更していない。証拠には Source 名、UNC Path、Secret、Credential、Ingestion ID 及び業務内容を保存していない。

## Release Gate

Runtime 受入まで合格した。主タスクで Annotated Tag `v0.28.3` を作成して Push し、`HEAD == origin/master == Tag` を確認した時点で正式 Release Gate が閉じる。

## Rollback

正式 Release 後に重大な Runtime 障害が確認された場合は、承認済みの直前 Release Commit を再配信する。PostgreSQL、Redis 及び Workspace Volume は保持する。Rollback 後は3系統の Readiness、Database Session State、Frontend Asset、Browser、Console を本一覧の先頭から再検証する。
