# Final acceptance checklist

| Original intent | Required result | Evidence | Status |
| --- | --- | --- | --- |
| Historical folders do not create current knowledge | 19 historical entries, including backup marker, excluded and zero current candidates from them | Final production Manifest and terminal result | Passed |
| Shortcut files remain auditable | Raw hash and typed target observation for all eight links | Final SourceEntry and task checkpoints | Passed |
| Shortcut targets flatten without cycles | Allowed target content uses logical shortcut path, repeated physical coverage stops at entry and provenance survives repeated learning | Unit tests, 22 final indexed target records and production observations | Passed |
| Readable TXT files do not fail readiness | 34 current TXT entries ready, empty TXT has path only Document, zero `NOT_INGESTED` | Production Manifest | Passed |
| Scope Repair is part of the extraction | Public started and completed events before Manifest | Final TaskEvent ledger | Passed |
| Per document progress remains live | 620 model activity events and 1,095 Generic Task progress events | Final TaskEvent ledger | Passed |
| All readable files retain raw provenance | 470 of 470 current files have raw SHA 256 | Final SourceEntry query | Passed |
| Current large and long-path files are usable | 17 MB PDF and 261 character SQL are indexed and analyzed | Final Manifest and SourceEntry query | Passed |
| Document, version and chunk links are closed | All 269 analyzed rows have versions; orphan and broken reference queries are zero; foreign keys exist | Final PostgreSQL queries | Passed |
| OneOps shows every processing outcome | Failure, exclusion and observation are present in deployed Bundle under 資料処理明細 | Tests, Health and Bundle | Passed with browser evidence gap |
| Tests and builds pass | Backend, frontend and OneOps checks pass | `test_results.md` | Passed |
| Browser, Console and screenshot | Formal UI is visually and interactively verified | In-app Browser | `evidence_missing`, repeated communication timeout |
| Runtime and release are exact | CAG 0.28.0 and OneOps 0.16.4 deployed, tagged and equal to origin/master | Health and Git evidence | Passed |

Any failed item restarts this checklist from the first row after repair.
