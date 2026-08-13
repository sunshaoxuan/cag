# Test results

## Backend

`218 passed, 4 skipped`, coverage `85.11%` in 217.37 seconds after the
read-only staging hardening.

The extraction Worker module executes in spawned child processes. Parent-side
black-box corpus tests cover returned text, processor metadata, stable binary
rejection, RTF, EML, ZIP, traversal, expanded-size limits and content probing.
The Worker module is omitted from the parent process coverage denominator
because the default coverage runner does not collect spawned Windows children.

## Frontend

Three files and 23 tests passed. TypeScript and Vite production build passed.

## Runtime

Compose built Python 3.12 Linux images with extract-msg, olefile, striprtf and
xlrd. Production Live and Ready report 0.31.0. PostgreSQL Alembic reports
`20260813_0030`.
