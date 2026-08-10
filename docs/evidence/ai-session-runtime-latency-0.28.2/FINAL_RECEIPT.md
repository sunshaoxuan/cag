# 最終回执

状態: 実装済み、専用テストと全 backend テスト合格、実行時受入は未完了

## 成果

Scheduler の active ingestion 空回り、claim 後の作成競合及び Task/Conversation SSE 初期 Session の長時間保持を修正した。API とデータ契約に変更はない。

## 現在の完了条件

専用 PostgreSQL claim/create 競合テストは 1 passed、全 backend テストは 182 passed、4 skipped、coverage 85.10% だった。主タスクでの CAG リリース、OneOps 経由 Browser、Console、Screenshot、PostgreSQL activity の確認が残っているため、正式リリース完了とは判定しない。

## 回滚

本サブタスクのコード、テスト、文書差分だけを取り消す。0.28.2 の restart policy と Supervisor 既存差分は回滚対象に含めない。
