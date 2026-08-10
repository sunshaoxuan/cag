# AI セッション実行時遅延 0.28.3 調査報告

## 目的

OneOps の AI セッション読み込み及び削除の応答遅延に対する CAG 側の修正について、長時間 Streaming 応答の Database Session 寿命、企業知識画面の Ingestion SSE 寿命及び本番 Runtime の状態を確認した。

## 対象

* CAG バージョン: `0.28.3`
* 実装 Commit: `e18fd222378f13462b6398ec6cc7bff1e5d2ad47`
* Branch: `master`
* Runtime: `8000`、`8001`、`8002` の3系統及び Frontend `5173`
* 実施日: 2026-08-10 から 2026-08-11 JST

## 調査結果

| 主張 | 証拠 | 確信度 | 制約 |
|---|---|---|---|
| 全5本の `StreamingResponse` Route は Request Scope の `get_session` に依存しない | `backend/tests/test_sse_session_lifetime.py` の全 Route Validator、Backend 全量試験 186件合格 | 高 | 将来 Route 追加時も Validator の維持が必要 |
| Knowledge Ingestion SSE の存在確認と各 Poll は独立した短命 Session を使用する | `backend/app/api/knowledge.py`、Session lifetime Test | 高 | 長時間運用時の接続総数は継続監視対象 |
| Rejection CSV は500件単位の Keyset Pagination を使い、各 Batch の Session を閉じてから出力する | `backend/app/api/knowledge.py`、同一 `created_at` 501件と ID Tie Breaker の Test | 高 | 低速 Client の実回線速度は今回の測定対象外 |
| `/audit` では Ingestion SSE を接続せず、Audit SSE だけを接続する | `/audit` の DOM、8000番 Port の接続1本、`/knowledge` 遷移時の接続置換、Frontend lifecycle Test | 高 | TCP 情報だけでは Endpoint を識別できないため、DOM と遷移時の置換を組み合わせて判定 |
| `/knowledge` では実行中 Ingestion の SSE を接続する | 実行中 Ingestion が処理中であることを示す DOM、接続元 Port が `53002` から `54984` へ置換、Frontend lifecycle Test | 高 | Source 名及び業務 Path は証拠から除外 |
| Ingestion SSE 接続中も PostgreSQL に `idle in transaction` は発生しない | `pg_stat_activity` は `idle in transaction=0`、State は `active=1`、`idle=22` | 高 | 2026-08-10 の受入観測値 |
| `/memory` へ離脱すると Ingestion SSE は閉じる | 離脱後の8000番 Port `Established=0`、Frontend lifecycle Test | 高 | Browser Extension 自身の通信は対象外 |
| CAG Application の Console に Warning 又は Error はない | Browser Console 確認 | 高 | Immersive Translate Extension の `dynamic-i18n version mismatch` は Application 外部の Error |
| 0.28.3 は3系統で Ready となり、Frontend も現行 Asset を配信する | 8000、8001、8002 の Ready 応答、`index-CMfzSW2Z.js` の Version 確認 | 高 | 正式 Git Tag は主タスクの最終 Release Gate で作成予定 |
| Scheduler の高頻度空転は停止した | 20秒で `knowledge_sources` 更新差分0件、API 3 Process の CPU 増分0.062秒、PostgreSQL CPU 1.53% | 高 | 実行中 Ingestion 1件と Lease 1件は状態を変更せず維持 |
| PostgreSQL と Redis は Process 異常終了後に自動復旧する | Compose と現行 Container の `unless-stopped`、同一 Image の隔離 Crash Test | 高 | 現行 Container は停止せず、無 Port、無 Volume の一時 Container で確認 |

## Runtime 観測

### API と依存サービス

8000、8001、8002 は全て `ready / 0.28.3` を返した。8000 の Readiness では PostgreSQL、Redis、Native Vector Search が正常で、pgvector は `0.8.2` だった。

Frontend `5173` は `/assets/index-CMfzSW2Z.js` を配信し、Asset 内の公開 Version は `0.28.3` と一致した。

### SSE ライフサイクル

`/audit` 表示中、画面には Audit Event Stream が表示され、8000番 Port の Established 接続は1本だった。接続元 Port は `53002`、作成時刻は `23:44:47` だった。

`/knowledge` へ遷移すると、画面上の実行中 Ingestion は処理中となり、8000番 Port の接続は接続元 Port `54984`、作成時刻 `23:50:19` の接続へ置換された。Audit SSE と Ingestion SSE は別 Endpoint である。画面 DOM、接続の置換及び Frontend Test を合わせて、企業知識画面以外では Ingestion SSE を接続しないことを確認した。

Ingestion SSE の接続中に PostgreSQL を観測し、`idle in transaction=0`、`active=1`、`idle=22` を確認した。`/memory` へ離脱した後、8000番 Port の Established 接続は0本になった。

### Scheduler と依存サービス自動復旧

2026-08-11 JST に20秒の差分観測を実施した。`knowledge_sources` の更新増分は0件、CAG API 3 Process の CPU 増分は合計0.062秒、PostgreSQL CPU は1.53%だった。実行中 Ingestion 1件と Lease 1件は観測期間中も維持し、状態を変更しなかった。

現行 PostgreSQL と Redis の RestartPolicy は `unless-stopped`、Health は `healthy` だった。現行 Container を停止せず、同じ Image を使用した無 Port、無 Volume の隔離 Container を起動した。12秒の安定稼働後に Service 子 Process を異常終了させ、PostgreSQL と Redis の両方で `RestartCount=1`、PostgreSQL `pg_isready` 成功、Redis `PONG` を確認した。一時 Container は試験後に全て削除した。

最初に実施した `docker kill` は Docker の人工停止として扱われ、`unless-stopped` の自動復旧対象にならなかった。次の試行では PID namespace の初期 Process を内部から終了できなかった。この2試行は復旧証拠から除外し、各一時 Container を削除した。

## Browser と情報保護

安全な Screenshot `browser-enterprise-knowledge-0.28.3.png` は、公開 Header、企業知識の Title、`v0.28.3` 及び登録済み Source 数だけを含む。Source 名、UNC Path、Secret、Credential、Ingestion ID、業務内容は記録していない。

既存の実行中 Ingestion は状態確認だけを行い、更新、停止、削除及び再作成を実施していない。

## 結論

CAG 0.28.3 の全 Streaming Route は長時間応答中に Request Scope の Database Session を保持しない。企業知識の Ingestion SSE は対象画面の Lifecycle に限定され、離脱時に閉じる。実環境の Ingestion SSE 接続中も PostgreSQL の `idle in transaction` は0件だった。Scheduler の20秒差分は Source 更新0件で、PostgreSQL と Redis の隔離 Crash Test は自動復旧に合格した。3系統の API、Frontend Asset、Application Console 及び安全な Screenshot の受入結果も全て合格した。
