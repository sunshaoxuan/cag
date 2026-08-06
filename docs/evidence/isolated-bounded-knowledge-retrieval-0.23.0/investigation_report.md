# CAG 0.23.0 customer knowledge retrieval investigation

Date: 2026-08-06

## Objective

Repair the OneOps customer knowledge scan failures recorded in
`D:\nginx\docs\investigations\customer-knowledge-scan-20260806\investigation_report.md`.
The acceptance target is a responsive API, bounded and correctly ranked customer
retrieval, durable cancellation, structured customer ledger extraction and
authoritative citations.

## Root causes

| Finding | Production evidence | Resolution |
| --- | --- | --- |
| API and queue consumers shared one process | Search saturation caused health and Task requests to time out | Windows and Compose runtimes now use separate API and worker processes |
| Retrieval materialized broad corpus rows and generated hundreds of text predicates | The original 9330 Task failed with PostgreSQL statement timeout and the API restarted | Every channel has a fixed candidate limit, capped terms, statement timeout and indexed database filtering |
| A bare Code matched unrelated document content | Initial 0.23.0 acceptance returned other institutions containing the number 9330 | Exact customer directory paths receive first priority and fast search skips broader text search when an exact path exists |
| Official name still exceeded the fast deadline | Production acceptance returned HTTP 504 after 3 seconds | Exact path query is isolated and indexed before any text candidate query |
| Customer extraction performed one broad semantic query | First production extraction failed at the balanced retrieval stage | Extraction resolves an authoritative customer root and searches each requested section only inside that root |
| Redis notifier was absent in the API role | Readiness reported `redis_connected=false` after process isolation | API and worker both start Redis notifier lifecycle; API publishes wake messages without local consumers |
| Cancel and completion raced | A leased extraction completed after Cancel API accepted the request | One second cancellation checks and timestamp ordered Queue finish make the earlier terminal decision authoritative |
| Cancelled scheduled ingestion was immediately recreated | Source `c4837509-0c4c-4689-bb34-e30a1138da05` remained overdue | Cancellation releases the source lease and advances `next_sync_at` by the configured interval |
| SQLite cutover target revision was stale | A clean PostgreSQL cutover test rejected revision `20260806_0021` | Cutover gate now requires the current Alembic head |

## Production results

* Query `9330`: HTTP 200 in 165.3 ms. Top path begins with `お_9330_岡山市立総合医療センター`.
* Query `岡山市立総合医療センター`: HTTP 200 in 115.2 ms with the same customer root.
* Concurrent live requests stayed responsive. Maximum observed latency was 62.6 ms during direct search and 128.7 ms during extraction.
* Extraction Task `a109cff6-8c7f-467d-b8d8-da4699693ea2` completed with two citation gated VPN candidates, 51 authoritative citations and zero validation errors.
* Cancellation Task `6206ece4-284f-4d27-89dc-a6469f3f5080` reached cancelled in 1098.4 ms after cancellation was requested during running state. No final result was delivered.
* Cancelled scheduled ingestion `aec33c29-74da-4217-a5a4-e9df0957e4e6` preserved Source status `approved` and active Generation `8c8c3326-c329-4828-8c04-ff41dd1d9e01`.

## Conclusion

All five findings in the OneOps investigation have direct implementation and
runtime evidence. The retrieval path now selects the correct customer directory,
the API stays responsive, stage evidence is durable, extraction owns its schema
and citations, and cancellation has deterministic terminal semantics.
