# コマンド記録

実行日: 2026-08-10 から 2026-08-11 JST

## Repository と Version

```powershell
cd D:\workspace\cag
git status --short --branch
git rev-parse HEAD
git rev-parse origin/master
Get-Content -Raw VERSION
```

確認値は `HEAD == origin/master == e18fd222378f13462b6398ec6cc7bff1e5d2ad47`、Version は `0.28.3` だった。

## 自動試験

```powershell
cd D:\workspace\cag\backend
.\.venv\Scripts\python.exe -m pytest

cd D:\workspace\cag\frontend
D:\nginx\runtime\node\pnpm.cmd test
D:\nginx\runtime\node\pnpm.cmd build

cd D:\workspace\cag
Invoke-Pester -Path .\scripts\tests\LocalCodexGateway.Tests.ps1 -PassThru
docker compose config --quiet
```

結果は Backend 186件合格、4件 Skip、Coverage 85.11%、Frontend 22件合格、Build 合格、PowerShell 11件合格、Compose 合格だった。

## Runtime Readiness

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://127.0.0.1:8001/health/ready
Invoke-RestMethod http://127.0.0.1:8002/health/ready
Invoke-WebRequest http://127.0.0.1:5173/
Invoke-WebRequest http://127.0.0.1:5173/assets/index-CMfzSW2Z.js
```

3系統は `ready / 0.28.3` だった。8000 は PostgreSQL、Redis、Native Vector Search が正常で、pgvector は `0.8.2` だった。5173 は `index-CMfzSW2Z.js` を配信し、Version `0.28.3` を含んでいた。

## SSE 接続観測

Browser で次の順序を実行した。

1. `/audit` を開き、Audit Event Stream の DOM を確認した。
2. 8000番 Port の Established 接続を確認した。
3. `/knowledge` へ遷移し、実行中 Ingestion が処理中であることを確認した。
4. 8000番 Port の接続が置換されたことを確認した。
5. PostgreSQL の Session State を確認した。
6. `/memory` へ遷移し、8000番 Port の Established 接続が0本になったことを確認した。
7. CAG Application の Console Warning と Error を確認した。

接続確認に使用した読取コマンドは次の形で実行した。

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Established |
    Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,CreationTime,OwningProcess
```

PostgreSQL では認証情報を出力せず、次の Query 結果だけを記録した。

```sql
SELECT state, count(*)
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY state
ORDER BY state;

SELECT count(*)
FROM pg_stat_activity
WHERE datname = current_database()
  AND state = 'idle in transaction';
```

Ingestion SSE 接続中の結果は `active=1`、`idle=22`、`idle in transaction=0` だった。

## Scheduler 差分観測

```powershell
docker stats --no-stream
docker exec cag-postgres-1 psql -U agent_gateway -d agent_gateway -At -F '|' -c "SELECT n_tup_upd, n_dead_tup FROM pg_stat_user_tables WHERE relname='knowledge_sources';"
Get-Process -Id ((Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8000,8001,8002 }).OwningProcess | Sort-Object -Unique)
```

同じ Query と Process CPU を20秒間隔で取得した。`knowledge_sources` 更新差分0件、API 3 Process CPU 増分0.062秒、PostgreSQL CPU 1.53%、実行中 Ingestion 1件、Lease 1件だった。

## RestartPolicy 隔離試験

```powershell
docker inspect cag-postgres-1 cag-redis-1
docker compose config --format json
docker run -d --restart unless-stopped --entrypoint sh pgvector/pgvector:0.8.2-pg16 -c '/usr/local/bin/docker-entrypoint.sh postgres & child=$!; echo $child >/tmp/service.pid; wait $child; exit $?'
docker run -d --restart unless-stopped --entrypoint sh redis:7-alpine -c '/usr/local/bin/docker-entrypoint.sh redis-server --appendonly yes & child=$!; echo $child >/tmp/service.pid; wait $child; exit $?'
docker exec <temporary-container> sh -c 'kill -9 $(cat /tmp/service.pid)'
docker inspect <temporary-container> --format '{{.RestartCount}}'
docker rm -f <temporary-container>
```

現行 PostgreSQL と Redis は RestartPolicy `unless-stopped`、Health `healthy` だった。現行 Container には異常終了を注入していない。同じ Image の無 Port、無 Volume の一時 Container を12秒以上安定稼働させ、Service 子 Process を異常終了させた。両 Container は `RestartCount=1` となり、PostgreSQL `pg_isready` と Redis `PONG` が再度成功した。一時 Container は全て削除した。

最初の `docker kill` による試行は Docker の人工停止として扱われて RestartPolicy を発動しなかった。次の PID 1 終了試行は PID namespace の制約により Container を終了できなかった。両試行は正式証拠から除外し、一時 Container は削除した。

## 文書検査

```powershell
cd D:\workspace\cag
git diff --check
git status --short --branch
Get-FileHash -Algorithm SHA256 -LiteralPath .\docs\evidence\ai-session-runtime-latency-0.28.3\browser-enterprise-knowledge-0.28.3.png
```

Version 文書検査は `VERSION`、Backend、Frontend、README、API 文書、要件表及び Changelog が全て `0.28.3` で一致することを確認する。Screenshot の SHA-256 は `4BD1FCD1B05C7600AFF62393B23D2A34B6FD14C99A7D1A630CA25ED8294CF9E1` だった。

Version Test の最初の個別実行は Test 自体が1件合格した後、全量実行用の Coverage 85%条件が個別実行にも適用されて終了 Code 1となった。この実行は証拠から除外した。`-o addopts=` で全量用 Option を解除して同じ Version Test を再実行し、1件合格、終了 Code 0を確認した。全量 Coverage 85.11%は先に完了した Backend 186件の実行結果を使用する。

0.28.3 証拠6文書と現行証拠2文書は日本語を含み、簡体字 Marker は0件だった。`git diff --check` と Screenshot Hash 検査も合格した。

## 情報保護

Command Output から Source 名、UNC Path、Secret、Credential、Ingestion ID 及び業務データを除外した。Runtime の実行中 Ingestion に対する更新、停止、削除及び再作成コマンドは実行していない。
