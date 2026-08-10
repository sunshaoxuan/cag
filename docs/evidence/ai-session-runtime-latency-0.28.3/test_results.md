# テスト結果

実行日: 2026-08-10 JST

バージョン: `0.28.3`

## 自動試験

| 確認項目 | 結果 | 判定 |
|---|---|---|
| Backend Pytest | 186件合格、4件 Skip | 合格 |
| Backend Coverage | 85.11%、必須値85%以上 | 合格 |
| Frontend Vitest | 22件合格 | 合格 |
| Frontend TypeScript と本番 Build | Build 成功 | 合格 |
| PowerShell Supervisor Test | 11件合格 | 合格 |
| Docker Compose 構文 | `docker compose config --quiet` 成功 | 合格 |
| Version 整合性 Focus Test | 1件合格 | 合格 |
| 証拠文書日本語検査 | 8文書、簡体字 Marker 0件 | 合格 |

## 専用 Regression

Backend 全量試験には次の契約を含む。

* `StreamingResponse` を返す5本の Route 全てが Request Scope の `get_session` に依存しない。
* Conversation、Task、Audit、Knowledge Ingestion の各 SSE は検証又は Poll の Session を Streaming Chunk 出力前に閉じる。
* Rejection CSV は500件単位で Session を閉じ、同一 `created_at` の501件を ID Tie Breaker で欠落なく出力する。

Frontend 全量試験には次の契約を含む。

* 企業知識画面以外では実行中 Ingestion の SSE を接続しない。
* `/knowledge` の StrictMode 初回表示では Knowledge Status、Source、Memory Candidate を各1回だけ取得する。
* `/memory` 初回表示では Memory Candidate だけを取得する。
* 企業知識画面を離れた後に遅延完了した Source GET 又は Ingestion POST から SSE を再接続しない。
* 企業知識画面から離脱した時点で Ingestion EventSource を閉じる。

## Runtime と Browser

| 確認項目 | 実測結果 | 判定 |
|---|---|---|
| API 3系統 | 8000、8001、8002 は `ready / 0.28.3` | 合格 |
| 8000 依存 Readiness | PostgreSQL、Redis、Native Vector Search 正常、pgvector `0.8.2` | 合格 |
| Frontend Asset | `index-CMfzSW2Z.js` が配信され、`0.28.3` を含む | 合格 |
| `/audit` | Audit DOM を表示、8000番 Port は Established 1本 | 合格 |
| `/knowledge` | 実行中 Ingestion が処理中、接続元 Port が `53002` から `54984` へ置換 | 合格 |
| PostgreSQL | Ingestion SSE 中 `idle in transaction=0`、`active=1`、`idle=22` | 合格 |
| `/memory` 離脱 | 8000番 Port Established 0本 | 合格 |
| Application Console | Warning 0件、Error 0件 | 合格 |
| Browser Screenshot | `browser-enterprise-knowledge-0.28.3.png`、SHA-256 `4BD1FCD1B05C7600AFF62393B23D2A34B6FD14C99A7D1A630CA25ED8294CF9E1` | 合格 |
| 実行中 Ingestion の保護 | 状態変更を実施せず観測完了 | 合格 |
| Scheduler 20秒差分 | Source 更新0件、API 3 Process CPU 増分0.062秒、PostgreSQL CPU 1.53% | 合格 |
| PostgreSQL と Redis の自動復旧 | 隔離 Crash Test で各 `RestartCount=1`、再 Ready。現行 Container は無停止 | 合格 |

Immersive Translate Extension の `dynamic-i18n version mismatch` は Browser Extension 由来であり、CAG Application の Console 結果から分離した。

## 情報保護確認

安全な Screenshot 及び本証拠文書に Source 名、UNC Path、Secret、Credential、Ingestion ID、業務内容を含めていない。
