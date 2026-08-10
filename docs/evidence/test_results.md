# 現行リリース試験結果

日付: 2026-08-10 JST

バージョン: `0.28.3`

Commit: `e18fd222378f13462b6398ec6cc7bff1e5d2ad47`

## 自動試験

| 確認項目 | 結果 |
|---|---|
| Backend Pytest | 186件合格、4件は環境条件により Skip |
| Backend Coverage | 85.11%、必須値85%以上 |
| Streaming Route Validator | 全5本が Request Scope の `get_session` に非依存 |
| Rejection CSV Pagination | 500件単位、同一 `created_at` 501件の ID Tie Breaker と Session close が合格 |
| Frontend Vitest | 22件合格 |
| Frontend TypeScript 及び本番 Build | 合格 |
| PowerShell 監督試験 | 11件合格 |
| Docker Compose 構文 | `docker compose config --quiet` 合格 |
| バージョン整合性 | VERSION、Backend、Frontend、README、API 文書、要件表及び Changelog は `0.28.3` で一致 |
| Version 整合性 Focus Test | 1件合格 |
| 証拠文書日本語検査 | 8文書、簡体字 Marker 0件 |

## 0.28.3 Regression の対象

* Conversation、Task、Audit、Knowledge Ingestion の各 SSE は検証又は Poll の Session を Chunk 出力前に閉じる。
* Rejection CSV は各500件 Batch の Session を閉じてから Row を出力する。
* 企業知識画面だけが実行中 Ingestion の EventSource を接続する。
* 企業知識画面から離れた時点で Ingestion EventSource を閉じる。
* 離脱後に完了した Source GET 又は Ingestion POST は SSE を再接続しない。
* StrictMode 初回表示の Knowledge Status、Source、Memory Candidate は各1回だけ取得する。

## 本番 Runtime

| 確認項目 | 結果 |
|---|---|
| 8000、8001、8002 `/health/ready` | 全系統 `ready / 0.28.3` |
| 8000 依存 Readiness | PostgreSQL、Redis、Native Vector Search 正常、pgvector `0.8.2` |
| Frontend `5173` | `/assets/index-CMfzSW2Z.js` を配信、Asset 内 Version `0.28.3` |
| 実行中 Ingestion | 状態を変更せず受入観測を完了 |
| Scheduler 20秒差分 | Source 更新0件、API 3 Process CPU 増分0.062秒、PostgreSQL CPU 1.53% |
| PostgreSQL と Redis の自動復旧 | 同一 Image の隔離 Crash Test で各 `RestartCount=1`、再 Ready。現行 Container は無停止 |

## Browser、Network、Database、Console

| 確認項目 | 結果 |
|---|---|
| `/audit` | Audit Event Stream の DOM を確認、8000番 Port Established 1本 |
| `/knowledge` | 実行中 Ingestion が処理中、接続元 Port `53002` から `54984` へ置換 |
| Ingestion SSE 接続中 | PostgreSQL `idle in transaction=0`、`active=1`、`idle=22` |
| `/memory` 離脱後 | 8000番 Port Established 0本 |
| CAG Application Console | Warning 0件、Error 0件 |
| Screenshot | `ai-session-runtime-latency-0.28.3/browser-enterprise-knowledge-0.28.3.png` |

Audit SSE と Ingestion SSE は別 Endpoint である。非知識画面で Ingestion SSE が接続されないことは、画面 DOM、接続の置換及び Frontend Test を組み合わせて判定した。Immersive Translate Extension の `dynamic-i18n version mismatch` は CAG Application 外部の Error として分離した。

## 情報保護

Screenshot と文書に Source 名、UNC Path、Secret、Credential、Ingestion ID 及び業務内容を含めていない。0.28.2 の Evidence Directory は歴史証拠として維持している。

## Release Gate

コード、自動試験、本番 Runtime、Browser、Network、Database、Console、Screenshot の受入は合格した。正式 Annotated Tag `v0.28.3` の作成、Push 及び `HEAD == origin/master == Tag` の確認は主タスクで実施する。
