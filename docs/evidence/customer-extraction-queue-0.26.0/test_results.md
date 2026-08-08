# Test results

## Backend

Final full run:

```text
165 collected
162 passed
3 skipped
coverage 85.40 percent
```

The final release-gate rerun on 2026-08-09 produced the same pass counts and
85.40 percent coverage. An earlier combined command reached its 120 second
orchestration limit; the separately rerun suite completed in 186.38 seconds
with exit code zero.

## Frontend

```text
3 test files passed
17 tests passed
production build passed
```

## Windows runtime scripts

```text
10 passed
0 failed
```

## Production

```text
CAG version: 0.26.0
PostgreSQL ready: true
pgvector native search: true
Redis connected: true
extraction workers: 1
target generic task: completed
target extraction: review_required
target queue item: completed
stale analyzed failure codes: 0
```
