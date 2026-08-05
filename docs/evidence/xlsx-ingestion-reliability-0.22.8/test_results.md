# Test results

## Completed before production

* Existing Office extraction, processing route and migration smoke passed.
* Frontend component tests passed, 17 tests across 3 files.
* Frontend production build passed.
* XML entity rejection, Worker isolation and Alembic 0020 round trip passed.
* Real target workbook parser check passed with 14 sheets, 1001 populated
  cells, 47 formulas, 47 cached values and Java, Apache and Tomcat content.
* Complete backend suite passed with 129 tests, 2 environment-dependent skips
  and 86.06 percent coverage.
* Isolated 8001 and 5174 runtime passed file search, clear, processor columns,
  desktop and 720-pixel viewport checks with zero browser console issues.

## Pending final acceptance

* Production cutover and full UPDS ingestion.
