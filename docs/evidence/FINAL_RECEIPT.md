# Current release receipt

Version: 0.22.8

Date: 2026-08-05

Branch: `master`

Status: pre-deployment validation passed

## Delivered

* Bounded semantic XLSX extraction with sheets, coordinates, formulas and
  cached values.
* Idempotent rejection persistence and unique final-path counters.
* Temporary Office file routing and stable spreadsheet limit reasons.
* Durable source-entry extractor evidence.
* Knowledge page file path search, clear and 100-row pagination.
* Interactive and knowledge Worker isolation regression.

## Verified before deployment

* 129 backend tests passed and 2 environment-dependent integration tests were
  skipped with 86.06 percent coverage.
* 17 frontend tests and the production build passed.
* The target workbook produced 14 sheets, 1001 populated cells, 47 formulas,
  47 cached values and expected Java, Apache and Tomcat text.
* Isolated 8001 and 5174 runtime acceptance passed.
* Desktop and narrow screenshots passed visual inspection.
* Browser console contained zero warnings and errors.

## Pending production gate

The release becomes complete after commit and push, managed production
cutover, schema 0020 application, live browser verification and a successful
full UPDS ingestion with target workbook retrieval evidence.

## Rollback

Restore the 0.22.7 application commit and rebuild the frontend. Downgrade
Alembic to 20260731_0019. The downgrade removes only nullable source-entry
extractor evidence. Existing documents, vectors, ingestion history and active
knowledge generation remain stored.
