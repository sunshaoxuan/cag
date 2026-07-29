# Version 0.17.0 test results

| Validation | Result |
|---|---|
| Backend full suite | 107 passed, 2 skipped |
| Backend coverage | 85.48 percent, required 85 percent reached |
| Frontend component tests | 12 passed |
| Frontend production build | Passed |
| PowerShell launcher tests | 7 passed |
| Compose configuration | Passed |
| Real PostgreSQL pgvector integration | 2 passed |
| Redis cross-instance notification | Receiver connected, sender connected, wake received |
| Browser page inspection | Version 0.17.0 and queue runtime cards confirmed |
| Browser copy interaction | Button changed from 复制 to 已复制 |
| Browser console | 0 warnings, 0 errors |
| Live 0.12.0 safety check | PID 17348 ready on 0.0.0.0:8000 |

The PostgreSQL integration databases were recreated before the final run so
each run used its own temporary encryption key and clean encrypted fixtures.
