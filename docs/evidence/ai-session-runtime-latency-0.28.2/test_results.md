# テスト結果

## 専用テスト

実行日: 2026-08-10

結果: 8 passed、9.32 秒

検証対象:

* queued と running ingestion が Scheduler claim から除外される。
* claim 後の競合で既存 ingestion を再利用した反復は idle になる。
* Scheduled Ingestion 作成は Source 行 Lock 後に active ingestion を再確認する。
* Scheduler の既存 lease、retry、例外継続契約を維持する。
* Task と Conversation SSE の初期検証 Session はストリーム返却前に閉じる。
* 不明 Conversation と Task の 404 契約を維持する。

## 全量テスト

実行日: 2026-08-10

コマンド:

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest
```

最終結果:

* 186 collected
* 182 passed
* 4 skipped
* 5 warnings
* coverage 85.10%
* 所要時間 197.76 秒

skip は環境依存の PostgreSQL integration 3 件と process isolation 1 件だった。

## PostgreSQL 並行試験

専用 Test Database で Scheduler claim 後に Transaction A が Source 行 Lock を保持し、Transaction B の Scheduled 作成が Lock 待機へ入ったことを `pg_stat_activity` で確認した。Transaction A が Scoped Ingestion を作成して Commit した後、Transaction B は同じ Ingestion ID と `created=False` を返した。結果は 1 passed で、active Ingestion は 1 件だった。Test Database は試験直後に削除した。

## 実行時検証

既存 Runtime の再起動、CPU、`pg_stat_activity` 及び OneOps 経由の操作は主タスクで実施する。
