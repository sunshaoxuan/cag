# Test results

| Test | Result |
|---|---|
| Backend pytest | 62 passed |
| Backend coverage | 88.69 percent |
| Frontend component and route tests | 8 passed |
| TypeScript and Vite build | Passed |
| Migration test | Dedicated upgrade, downgrade and re-upgrade passed |
| Live SQLite migration | `20260727_0008` |
| Real external API call | HTTP 202, completed |
| Real Task event count | 27 |
| Real global sequence range | 5458 to 5484 |
| Real idempotency replay | Same Trace, replay header true |
| Browser audit replay | Backend 5,484 events, latest 100 displayed |
| Browser console | Zero warnings and errors |
