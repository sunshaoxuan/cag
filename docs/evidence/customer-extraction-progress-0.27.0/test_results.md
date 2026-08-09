# Test results

## Backend

```text
165 collected
162 passed
3 skipped
coverage 85.43 percent
```

## Frontend

```text
3 test files passed
17 tests passed
production build passed
```

## Focused contracts

1. A legacy aggregate deadline value elapses without terminating extraction.
2. Each document child publishes one terminal public progress event.
3. Analyzed, model-failed, metadata-only and excluded children are covered.
4. Running API progress counts come from persisted document states.
5. The frontend renders `task.progress` as `任务进度已更新`.
6. Consecutive unknown audit events share one in-flight Task-list refresh.

## Production acceptance

```text
CAG API 0.27.0 ready
Extraction review_required / EXTRACTION_PARTIAL
452 document terminal events
458 public Task events
Browser reload restored completed card
Console warning and error count 0
```
