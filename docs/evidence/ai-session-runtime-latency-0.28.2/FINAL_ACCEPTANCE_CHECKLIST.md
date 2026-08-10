# 最終受入一覧

| 原要求 | 成果物 | 証拠 | 状態 |
|---|---|---|---|
| active ingestion 中の Scheduler 空回りを止める | claim 除外と idle 判定 | 専用 Scheduler テスト | 合格 |
| claim 後の Ingestion 作成競合を直列化する | Source 行 Lock と Scheduled 再確認 | 専用 PostgreSQL 双 Transaction Test | 合格 |
| Conversation SSE の長時間 idle transaction を止める | 初期 Session の短命化 | Session lifetime テスト | 合格 |
| Task SSE の長時間 idle transaction を止める | 初期 Session の短命化 | Session lifetime テスト | 合格 |
| PostgreSQL と Redis の restart policy を確認する | 0.28.2 既存 Compose 差分 | `docker-compose.yml` | 合格 |
| 既存差分を保護する | 新規修正ファイル境界の確認 | `git diff` と `git status` | 合格 |
| 関連テストを実行する | 専用テスト、PostgreSQL 並行テスト、全 backend テスト | 専用 8 passed、PostgreSQL 1 passed、全量 182 passed、4 skipped、coverage 85.10% | 合格 |
| 実環境で会話読み込みと削除を再検証する | OneOps 経由 runtime 受入 | Browser、Console、Screenshot、DB activity | 主タスク待ち |
