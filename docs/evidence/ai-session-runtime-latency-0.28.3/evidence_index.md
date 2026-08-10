# 証拠索引

| 証拠 | 確認内容 | 状態 | 制約 |
|---|---|---|---|
| `backend/app/api/knowledge.py` | Ingestion SSE の短命 Session、Rejection CSV の500件 Keyset Pagination | 確認済み | Runtime Secret は記録対象外 |
| `backend/tests/test_sse_session_lifetime.py` | 全5本の Streaming Route Validator、Session close、501件同一時刻の ID Tie Breaker | 186件の Backend 全量試験内で合格 | 将来の Streaming Route 追加時も Validator 更新が必要 |
| `frontend/src/App.tsx` | 企業知識画面だけで Ingestion SSE を接続し、離脱時に close | 確認済み | Browser の通信観測と併用 |
| `frontend/src/App.test.tsx` | 非知識画面、StrictMode、遅延 GET、遅延 POST、離脱 close | 22件の Frontend 全量試験内で合格 | Mock EventSource による Component Test |
| 8000、8001、8002 `/health/ready` | 3系統の `ready / 0.28.3` | 合格 | 2026-08-10 JST の観測値 |
| 8000 Readiness Detail | PostgreSQL、Redis、Native Vector Search、pgvector `0.8.2` | 合格 | 8001、8002 は Ready 応答で確認 |
| Frontend `5173` | `/assets/index-CMfzSW2Z.js` と公開 Version `0.28.3` | 合格 | Asset Hash の比較は主タスク側で管理 |
| Browser `/audit` | Audit DOM、Established 1本、接続元 Port `53002`、作成時刻 `23:44:47` | 合格 | TCP 単体では Endpoint を識別しない |
| Browser `/knowledge` | 実行中 Ingestion が処理中、接続元 Port `54984`、作成時刻 `23:50:19` へ置換 | 合格 | Source 名と Path は非記録 |
| PostgreSQL `pg_stat_activity` | Ingestion SSE 中 `idle in transaction=0`、`active=1`、`idle=22` | 合格 | 一時点の Runtime 観測 |
| Browser `/memory` | 離脱後の8000番 Port Established 接続0本 | 合格 | Browser Extension 通信は対象外 |
| Browser Console | CAG Application の Warning と Error は0件 | 合格 | Extension の `dynamic-i18n version mismatch` を Application Error から除外 |
| `browser-enterprise-knowledge-0.28.3.png` | 公開 Header、Title、Version、登録済み Source 数。SHA-256 `4BD1FCD1B05C7600AFF62393B23D2A34B6FD14C99A7D1A630CA25ED8294CF9E1` | 合格 | Source 名、UNC Path、Secret を含まない |
| 既存の実行中 Ingestion | 状態を変更せず受入観測を実施 | 保護済み | ID と業務内容は非記録 |
| Scheduler 20秒差分 | `knowledge_sources` 更新0件、API 3 Process CPU 増分0.062秒、PostgreSQL CPU 1.53% | 合格 | 実行中 Ingestion 1件と Lease 1件を維持 |
| Compose と現行 Container | PostgreSQL と Redis の RestartPolicy `unless-stopped`、Health `healthy` | 合格 | 現行 Container の異常終了試験は未実施 |
| 同一 Image の隔離 Crash Test | PostgreSQL と Redis は各 `RestartCount=1`、再 Ready | 合格 | 無 Port、無 Volume。一時 Container は削除済み |

## 関連文書

* `investigation_report.md`
* `commands.md`
* `test_results.md`
* `FINAL_ACCEPTANCE_CHECKLIST.md`
* `FINAL_RECEIPT.md`
