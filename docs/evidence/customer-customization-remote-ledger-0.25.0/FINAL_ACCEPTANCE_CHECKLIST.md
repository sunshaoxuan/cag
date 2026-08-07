# Final acceptance checklist

| Requirement | Artifact or evidence | Status |
| --- | --- | --- |
| Analyze customization information | Version 2 contract and live `customizations` candidates | PASS |
| Analyze remote connection information | Live `vpns` and `environments` candidates | PASS |
| Preserve review truth | `review_required`, `EXTRACTION_PARTIAL`, coverage object | PASS |
| Keep object candidates independent | Object list merge tests | PASS |
| Protect credential material | Prompt scan, excerpt scan, live redaction marker | PASS |
| Avoid sample customer implementation | Production code search with no match | PASS |
| Use physical scope identity | Source physical ID and analysis scope records | PASS |
| Avoid duplicate scoped collection | Atomic claim and scoped ingestion tests | PASS |
| Complete automated verification | 160 passed, 3 skipped, Coverage 85.36% | PASS |
| Ready runtime | Health ready 200 | PASS |
| Empty active queue | Final queue query | PENDING |
| Documentation complete | ADR, requirement matrix and evidence set | PASS |
| Commit and push | `master` equals `origin/master` | PENDING |
| Release tag | `v0.25.0` on published commit | PENDING |

Any failed or pending row prevents a completion claim. After every correction this checklist is evaluated again from the first row.
