# CAG 0.24.0 investigation and design report

## Original objective

Turn customer folders into continuously improving, multilingual, citation
grounded business knowledge. Remote connection documents must produce useful
SSH, LDAP, VPN, RDP or repository knowledge while protected values remain
outside searchable and model visible text.

## Verified production findings

| Finding | Evidence | Status |
|---|---|---|
| Customer paths are inventory evidence but only indexed document paths are retrievable | PostgreSQL source entries, documents and chunks | confirmed |
| Five indexed Shiga University PDFs contain neither customer Code nor official name | PostgreSQL chunk projection query | confirmed |
| One five page maintenance PDF contains images and zero pypdf text | direct read only pypdf inspection | confirmed |
| Two current remote connection TXT files contain SSH or LDAP evidence and have zero chunks | direct extraction and PostgreSQL query | confirmed |
| Current extraction schema has no remote access or repository section | API and extraction source | confirmed |
| Japanese password labels are not detected by the current scanner | direct scanner invocation without exposing values | confirmed |
| UPDS has 137 consecutive source refresh failures | production source record | confirmed |

## Design result

ADR 0026 defines multilingual hybrid retrieval, path semantic embeddings,
inventory based customer roots, OCR, multilingual secret redaction, typed remote
access and repository extraction, incremental refresh and truthful freshness.

## Skill gap

No installed skill covered implementation of a cross repository multilingual
knowledge ingestion, OCR, secret boundary and business extraction release. The
engineering investigation skill supplied the evidence workflow. The reusable
implementation pattern remains a candidate in `D:\workspace\codex-selfimp`.
