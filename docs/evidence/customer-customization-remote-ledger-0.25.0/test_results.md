# Test results

## Full suite

Command: `.\.venv\Scripts\python.exe -m pytest`

Result:

1. 160 passed.
2. 3 skipped.
3. 5 dependency deprecation warnings.
4. Total coverage 85.36%.
5. Exit code 0.

## Regression found and corrected

The first full run found concurrent execution of one scoped ingestion. A manual caller and the queue worker could both observe `queued` before either committed `running`. The ingestion now uses a conditional database update to claim the record atomically. The two focused behavior tests passed, then the complete suite was rerun from its start and passed.

The focused command alone exits on the repository wide coverage threshold. Its two selected tests passed before the expected coverage threshold result.
