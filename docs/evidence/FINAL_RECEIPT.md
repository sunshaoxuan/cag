# 現行リリース受入記録

バージョン: `0.28.3`

日付: 2026-08-10 JST

ブランチ: `master`

実装 Commit: `e18fd222378f13462b6398ec6cc7bff1e5d2ad47`

状態: コード、自動試験、本番 Runtime、Browser、Console、Screenshot の受入合格。正式 Annotated Tag は主タスクの Release Gate 待ち。

## 実装内容

* Knowledge Ingestion SSE の存在確認及び各 Poll は独立した短命 Database Session を使用する。
* Rejection CSV は500件単位の Keyset Pagination を使用し、Session を閉じてから Row を出力する。
* 全5本の Streaming Route は Request Scope の `get_session` に依存しない。
* Frontend は企業知識画面だけで実行中 Ingestion の SSE を接続し、離脱時に閉じる。
* Page Generation Guard は離脱後に完了した Source GET 又は Ingestion POST による SSE 再接続を防ぐ。
* StrictMode 初回表示の Knowledge 関連取得は一組に統合される。
* 0.28.2 で導入した PostgreSQL と Redis の RestartPolicy、Scheduler 排他及び Conversation と Task SSE の短命 Session 境界を維持する。

## 自動試験

* Backend は186件合格、4件 Skip、Coverage 85.11%だった。
* Frontend は22件合格し、TypeScript 及び本番 Build も合格した。
* PowerShell 監督試験は11件合格した。
* Docker Compose 構文及び Version 整合性は合格した。
* Version 整合性 Focus Test 1件と証拠文書8件の日本語検査は合格した。

## 本番 Runtime 受入

* 8000、8001、8002 は全て `ready / 0.28.3` を返した。
* 8000 は PostgreSQL、Redis、Native Vector Search が正常で、pgvector は `0.8.2` だった。
* 5173 は `/assets/index-CMfzSW2Z.js` を配信し、公開 Version は `0.28.3` だった。
* 既存の実行中 Ingestion は状態を変更せず観測した。
* Scheduler の20秒差分は Source 更新0件、API 3 Process CPU 増分0.062秒、PostgreSQL CPU 1.53%だった。
* PostgreSQL と Redis は同一 Image の隔離 Crash Test で各 `RestartCount=1` となり、再 Ready を確認した。現行 Container は停止していない。

## Browser、Network、Database、Console

* `/audit` で Audit Event Stream の DOM を確認した。
* `/knowledge` への遷移で実行中 Ingestion が処理中となり、8000番 Port の接続が接続元 Port `53002` から `54984` へ置換された。
* Ingestion SSE 接続中の PostgreSQL は `idle in transaction=0`、`active=1`、`idle=22` だった。
* `/memory` へ離脱した後の8000番 Port Established 接続は0本だった。
* CAG Application の Console Warning と Error は0件だった。
* Immersive Translate Extension の `dynamic-i18n version mismatch` は Application 外部の Error として分離した。
* 安全な Screenshot は `ai-session-runtime-latency-0.28.3/browser-enterprise-knowledge-0.28.3.png` に保存した。

## 証拠

0.28.3 の詳細な調査、コマンド、試験、最終受入及び回収は `docs/evidence/ai-session-runtime-latency-0.28.3` に保存した。0.28.2 の Directory は歴史証拠として維持している。証拠には Source 名、UNC Path、Secret、Credential、Ingestion ID 及び業務内容を含めていない。

## Release Gate

Runtime 受入まで合格した。主タスクで Annotated Tag `v0.28.3` を作成して Push し、`HEAD == origin/master == Tag` を確認した時点で正式 Release Gate が閉じる。

## Rollback

正式 Release 後に重大な Runtime 障害が確認された場合は、承認済みの直前 Release Commit を再配信する。PostgreSQL、Redis 及び Workspace Volume は保持する。Rollback 後は3系統の Readiness、Database Session State、Frontend Asset、Browser、Console を最終受入一覧の先頭から再検証する。
