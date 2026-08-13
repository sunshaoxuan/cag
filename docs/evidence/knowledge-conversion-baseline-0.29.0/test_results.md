# Test results

| Verification | Result |
|---|---|
| Focused conversion, migration and version tests | PASS, final run 5 passed |
| Focused post-repair status, health and version tests | PASS, 5 passed |
| Complete backend suite | PASS, final run 196 passed, 4 skipped, 85.37% coverage |
| Frontend components | PASS, 3 files and 23 tests |
| Frontend TypeScript and production build | PASS |
| Alembic upgrade and downgrade round trip | PASS in migration tests |
| Formal PostgreSQL migration | PASS, `20260813_0028` |
| Production largest-Source dry run | PASS, 115,668 items in about 24 seconds |
| Knowledge table preservation | PASS, all compared counts unchanged |
| Manifest foreign-key closure | PASS, zero Source Entry and Document orphans |
| Repeatable-read atomicity and failed-run closure | PASS, successful Manifest is one transaction and injected failure leaves zero items |
| Formal HTTP read APIs | PASS |
| Formal HTTP POST dry run | PASS |
| Browser DOM | PASS, One Agent Gateway and v0.29.0 visible |
| Browser Console | PASS, zero warning or error entries |
| Browser screenshot | PASS, `browser-home-0.29.0.png` |

The first complete backend run had one stale version assertion in
`test_health.py`: it expected 0.28.5 after the release version changed to
0.29.0. The assertion was updated, keyset first-page handling was hardened and
the complete suite was rerun from the beginning. The final complete result is
the passing 196-test run above. A later review added repeatable-read atomicity
and failed-run closure, so backend, frontend, migration, production and Browser
acceptance were run again from their respective starting points.
