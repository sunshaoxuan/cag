# CAG 0.28.0 customer Scope readiness investigation

## Question

The OneBridge customer extraction treated historical folders as current
evidence, excluded Windows Shell Links without inspection and reported readable
TXT files as `NOT_INGESTED`. The release must also stop shortcut cycles at a
physical directory boundary.

## Reproduced baseline

Extraction `a8b3a50a-7cb6-421e-972e-3d1a21a63cc0` froze a 442 entry Manifest.
It ended with 91 ready entries, 82 analyzed entries, 171 failures and 189
exclusions. Eighteen entries were below `old` or `旧_*`. Eight `.lnk` entries
were excluded without a raw hash. Thirty seven TXT entries were reported as
`NOT_INGESTED` while the source wide ingestion was still collecting.

Direct extractor verification read all 37 TXT files and reproduced all 37 raw
SHA 256 values. Thirty files used CP932, seven used UTF 8 and one was empty.
Windows read only inspection resolved two shortcut targets, found two missing
mapped drives and four missing paths.

## Root cause

The extraction request contained `prepare_required_versions`, but version
0.27.0 froze the Manifest before executing that policy. `.lnk` remained an
unsupported extension, and current candidate selection had no historical path
policy.

## Implemented behavior

Version 0.28.0 performs a Scope Repair before Manifest creation. It publishes
`scope.ingestion.started` and `scope.ingestion.completed`, retains the parent
extraction lease and protects newer observations from older concurrent full
ingestion finalization.

Normalized `old`, `旧`, `旧_*`, `旧-*`, `back`, `backup`, `bak` and
`バックアップ` directory segments are retained as provenance and excluded
from current candidates with `historical_path`.

Every `.lnk` receives a raw SHA 256. LnkParse3 1.6 reads local and network LinkInfo
with CP932 support. Allowed targets are flattened below the logical shortcut
name. A visited physical directory identity and coverage roots stop a repeated
directory, an already covered ancestor, an already covered descendant and a
back link at directory entry.

Every readable file receives raw SHA 256 before processing policy. Supported
files up to 100 MB enter Cleaning. Windows UNC files beyond the legacy path
limit use an extended-length path only at the I/O boundary. Manifest selection
matches the SourceEntry current relative path, so historical Documents cannot
be selected as current input. Repeated Scope Repair retains
`shortcut_target_flattened` provenance for reusable target files.

## Production verification

Final production extraction `4cd21c2e-e62f-40cb-8560-4342f29bc794` resolved
Scope `f0193db4-bb74-49bc-8850-85fc4b3a526e`. Scope Repair ingestion
`8896eeee-0e2a-4804-bd40-1a0f732a1867` found 470 files, reused 3,010 vectors
and completed without an ingestion error. All 470 current files have raw SHA
256. Of those, 469 have cleaned or path content hash; the remaining file is a
damaged XLSX inside `old` and is excluded as historical.

The terminal Manifest has 470 rows and 470 terminal child rows: 269 analyzed,
19 historical exclusions, two temporary Office files and 180 unsupported
extensions. Failure count is zero and coverage is 1.0. Current TXT is 34 ready
and analyzed; nine TXT entries are historical. Eight shortcuts have raw hashes
and typed observations. Twenty two indexed flattened target files retain
`shortcut_target_flattened`, raw hash and content hash after repeated learning.
The current 17 MB PDF and the 261 character SQL path are both indexed and
analyzed. The task emitted 620 model activity events and released its Source
lease after aggregation.

The OneOps production title is discoverable in the in-app Browser. DOM,
Console and screenshot calls timed out twice, so visual evidence remains
`evidence_missing`; Health and deployed Bundle evidence are recorded
separately.
