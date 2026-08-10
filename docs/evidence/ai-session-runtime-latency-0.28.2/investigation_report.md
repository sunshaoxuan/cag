# AI セッション実行時遅延調査報告

## 対象

OneOps の AI セッション読み込みと削除で長い待機が発生した際に、CAG 側で同時に確認された PostgreSQL 接続保持と Scheduler 空回りを対象とした。

## 調査結果

| 主張 | 証拠 | 確信度 | 制約 |
|---|---|---|---|
| 同一 Source に queued または running ingestion が存在しても Scheduler の claim 対象になっていた | `backend/app/knowledge/service.py` の旧 `claim_due_source` 条件と runtime audit | 高 | 本サブタスクでは既存コンテナを操作していない |
| 既存 ingestion を返す `created=False` が Scheduler では実作業済みとして扱われていた | `backend/app/knowledge/scheduler.py` の旧 `return True` | 高 | なし |
| claim と Scheduled Ingestion 作成が別 Transaction のため、人工又は Scope Repair の作成が間へ入る余地があった | `claim_due_source`、旧 `create_ingestion`、独立差分審査 | 高 | 専用 PostgreSQL Test Database で再現防止を検証した |
| Task と Conversation SSE の初期検証 Session がストリーム終了まで保持され得た | 旧 API route の `session: Session = Depends(get_session)` と `StreamingResponse` | 高 | PostgreSQL 実測の再取得は主タスクの runtime 検収事項 |
| PostgreSQL と Redis の restart policy は 0.28.2 既存差分に含まれている | `docker-compose.yml` の両 service にある `restart: unless-stopped` | 高 | 本サブタスクでは起動試験を実施していない |

## 修正

1. Scheduler claim の SQL 条件に同一 Source の active ingestion 非存在条件を追加した。
2. claim 後の競合で既存 ingestion が返った場合、`run_once` は idle を返して通常の poll 待機へ移るようにした。
3. Ingestion 作成 Transaction で Source 行を Lock し、Scheduled 作成時は同一 Source の全 active ingestion を再確認するようにした。
4. Task と Conversation SSE の存在確認を明示的な短命 Session に変更し、`StreamingResponse` 生成前に close するようにした。

## 影響範囲

API URL、SSE payload、event sequence、heartbeat、resume contract、ingestion schema は変更していない。Scheduled Ingestion の単一実行境界だけを Source 単位で直列化した。Migration と互換処理は追加していない。

## 未実施の実行時検証

本サブタスクの制約に従い、既存 CAG コンテナの再起動、OneOps 経由の実会話読み込み、専用会話削除、PostgreSQL `pg_stat_activity` の再観測は実施していない。これらは主タスクのリリース後受入で確認する。
