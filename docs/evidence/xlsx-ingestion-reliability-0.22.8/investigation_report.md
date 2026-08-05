# XLSX ingestion reliability investigation

## Findings

The former XLSX extractor concatenated raw OOXML text nodes and did not resolve
shared-string indexes or preserve workbook structure. The inspected UPDS
workbook contains 14 worksheets, 1001 populated cells and 47 formulas.

UPDS scheduled ingestions failed while inserting the same ingestion and
relative-path pair more than once into the rejection audit table. Office lock
files beginning with `~$` also entered ZIP extraction and produced BadZipFile.

## Implemented correction

Version 0.22.8 uses bounded openpyxl semantic extraction, idempotent rejection
persistence, temporary Office file routing, durable processor evidence and
source-entry search and pagination in the Knowledge page.

## Remaining live acceptance

The complete backend suite, isolated runtime, production browser and full UPDS
learning results are recorded as they complete.
