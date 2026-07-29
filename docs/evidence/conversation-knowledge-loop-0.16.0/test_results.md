# Test results

| Validation | Result |
|---|---|
| Backend full suite | 92 passed, 2 PostgreSQL opt-in tests skipped |
| Backend coverage | 85.34 percent, required threshold reached |
| Knowledge-focused suite | 27 passed |
| Codex app-server focused suite | 8 passed |
| Frontend component suite | 11 passed |
| TypeScript and Vite production build | Passed |
| Docker frontend production image | Passed |
| Browser version and Conversation page | Passed at `127.0.0.1:5174` |
| Browser console | Zero warnings and errors |

The tests used SQLite only inside the isolated test boundary, Fake Ollama and
the deterministic Codex app-server protocol fixture. No Codex subscription
quota was consumed.
