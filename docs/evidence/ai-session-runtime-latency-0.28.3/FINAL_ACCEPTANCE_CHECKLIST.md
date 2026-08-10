# 最終受入一覧

基準日: 2026-08-10 JST

対象 Version: `0.28.3`

| 原要求 | 成果物 | 検証証拠 | 状態 |
|---|---|---|---|
| 長時間 Streaming 応答が Request Session を保持しない | 全5本の Streaming Route の短命 Session 境界 | Route Validator、Session lifetime Test、Backend 186件合格 | 合格 |
| Ingestion SSE の各 Poll が Transaction を残さない | 反復ごとの独立 Session | Ingestion SSE Test、Runtime `idle in transaction=0` | 合格 |
| 低速 Rejection CSV が Cursor と Session を長時間保持しない | 500件 Keyset Pagination | 501件同一時刻、ID Tie Breaker、Batch close Test | 合格 |
| Ingestion SSE を企業知識画面だけで使用する | Page Lifecycle に連動する EventSource | `/audit`、`/knowledge` の DOM と接続置換、Frontend Test | 合格 |
| 企業知識画面から離脱すると SSE を閉じる | EventSource close と Page Generation | `/memory` 離脱後 Established 0本、Frontend Test | 合格 |
| 遅延 GET 又は POST が離脱後に SSE を再接続しない | Page Generation Guard | Frontend 専用 Test | 合格 |
| StrictMode 初回表示で重複取得しない | Refresh Promise の Generation 共有 | Frontend 専用 Test、Frontend 22件合格 | 合格 |
| 3系統の Runtime と依存サービスが現行 Version で稼働する | 8000、8001、8002 と 5173 | Ready `0.28.3`、依存正常、`index-CMfzSW2Z.js` | 合格 |
| Application Console に Warning 又は Error がない | Browser Console 受入 | Application Warning 0件、Error 0件 | 合格 |
| UI を安全な Screenshot で確認する | `browser-enterprise-knowledge-0.28.3.png` | 公開 Title、Version、Source 数だけを含む | 合格 |
| 実行中 Ingestion を保護する | 読取だけの Runtime 受入 | 更新、停止、削除、再作成を未実施 | 合格 |
| Scheduler の高頻度空転を止める | Scheduler 排他と idle 判定 | 20秒で Source 更新0件、API CPU 増分0.062秒、PostgreSQL CPU 1.53% | 合格 |
| PostgreSQL と Redis が異常終了後に復旧する | `unless-stopped` | 同一 Image の隔離 Crash Test で各 `RestartCount=1`、再 Ready | 合格 |
| Source 名、Path、Secret を証拠へ保存しない | Sanitized Evidence | Screenshot と全6文書の内容確認 | 合格 |
| 0.28.2 の歴史証拠を維持する | 既存 Evidence Directory | `ai-session-runtime-latency-0.28.2` を変更対象外として確認 | 合格 |
| 関連する全量試験を通過する | Backend、Frontend、Build、PowerShell、Compose | 186件、22件、Build、11件、Compose | 合格 |

## 最終判定

本一覧の全項目は合格した。CAG 0.28.3 の実行時受入証拠は当初目的と一致する。正式 Git Tag の作成及び `HEAD == origin/master == Tag` の確認は主タスクの Release Gate で実施する。
