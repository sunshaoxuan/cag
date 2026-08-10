# 現行リリース試験結果

日付: 2026-08-10

バージョン: 0.28.2

## 自動試験

| 確認項目 | 結果 |
|---|---|
| Backend Pytest | 182 件合格、4 件は環境条件により Skip |
| Backend Coverage | 85.10 percent、必須値 85 percent 以上 |
| PostgreSQL Scheduler claim/create 競合 Test | Lock Wait を確認する専用 Test Database で 1 件合格、試験後に Database 削除済み |
| Frontend Vitest | 3 Files、17 件合格 |
| Frontend TypeScript 及び本番 Build | 合格 |
| PowerShell 監督試験 | 11 件合格 |
| Docker Compose 構文 | `docker compose config --quiet` 合格 |
| バージョン整合性 | VERSION、Backend、Frontend、README、API 文書、要件表及び Changelog の一致を確認 |

## 障害再現と修復証拠

Docker Runtime 再起動後、CAG PostgreSQL と Redis の RestartPolicy が `no` のままであったため、Gateway API の liveness だけが正常に残りました。Conversation、Task 及び Event の取得は PostgreSQL 接続を長時間待機し、OneOps に 500 又は 503 を返しました。

PostgreSQL と Redis を既存 Volume のまま復旧した後、CAG 8001 及び 8002 は以下の結果に回復しました。

| 確認項目 | 結果 |
|---|---|
| `/health/ready` | 両系統とも HTTP 200、PostgreSQL、pgvector 0.8.2、Redis 正常 |
| Conversation 取得 | 両系統とも HTTP 200、約 0.05 秒 |
| Task 取得 | 両系統とも HTTP 200、約 0.05 秒 |
| OneOps 経由の同一 Session | Conversation、Event とも HTTP 200 へ回復 |

## 本番適用前ゲート

Code、構成、文書及び自動試験は合格しました。Compose 再調整、3 系統の Supervisor 再登録、本番 Ready、OneOps 経由の Smoke Test 及び Browser 験収はリリース後に追記します。
