# ADR 0030: Scope readiness and shortcut flattening

## Status

Accepted for version 0.28.0.

## Context

The OneBridge extraction request required `prepare_required_versions`, while
the execution path froze its manifest directly from catalog observations. The
source-wide ingestion was still collecting files, so 37 readable TXT entries
had raw hashes without cleaned Documents and appeared as `NOT_INGESTED`.

The same scope contained 18 historical-path entries and eight Windows Shell
Links. Historical PDFs produced current ACTIVE candidates. Links were excluded
without raw hashes or target inspection.

Microsoft MS-SHLLINK defines LinkInfo and CommonNetworkRelativeLink fields that
preserve a network name, mapped device and common path suffix. LnkParse3 1.6 is
a maintained MIT-licensed read-only parser that exposes local and network
LinkInfo and tolerates malformed inputs.

## Decision

1. Execute `prepare_required_versions` before manifest creation.
2. Run the resolved Scope Repair inline with the extraction worker and retain
   the parent QueueItem lease.
3. Protect newer SourceEntry observations from older concurrent ingestion
   finalization.
4. Exclude normalized historical directory segments, including `old`, `旧`,
   `back`, `backup`, `bak` and `バックアップ`, from current customer candidates
   while retaining provenance.
5. Hash every `.lnk` and parse it with LnkParse3 using CP932 for legacy ANSI
   strings.
6. Reconstruct UNC targets from network root and common suffix instead of
   depending on a mapped drive in the worker session.
7. Restrict network targets to the registered UNC share and local targets to an
   allowed root.
8. Flatten an allowed target below the logical shortcut path.
9. Keep a visited identity for every physical directory. Stop at directory
   entry when the same directory, its covered ancestor or a back-link is seen.
10. Publish typed shortcut observations and historical exclusions in the
    extraction result.
11. Preserve the trailing separator of a UNC Share root when comparing physical
    directory coverage.
12. Hold one renewable Source lease from Scope resolution through aggregation.
    Scope Repair runs inside that lease, while queued manual or scheduled full
    ingestions wait for release.
13. Resolve the Manifest Document by the SourceEntry current relative path.
    Historical Documents linked to the same SourceEntry remain provenance and
    cannot become the current extraction input.
14. Compute raw SHA 256 before applying metadata-only policy. Clean supported
    files up to 100 MB and retain hash, path and reason for larger files.
15. Use the Windows extended-length form at the file I/O boundary for UNC
    paths of 248 characters or more. Logical and canonical paths remain
    unchanged.
16. Preserve `shortcut_target_flattened` on reusable files whose physical path
    is outside the Source root. Repeated learning cannot erase shortcut
    provenance.

## Consequences

An exhaustive customer extraction analyzes cleaned versions from its own
resolved Scope. Readable TXT files no longer fail because a source-wide scan is
still collecting. Historical documents cannot create current ledger facts.
Shortcut targets become auditable and reachable targets can contribute content
without recursive duplication. Targets outside the approved boundary remain
visible and unscanned.

## Acceptance

1. All readable OneBridge TXT files complete Scope Repair without
   `NOT_INGESTED`.
2. Historical paths produce zero current field candidates.
3. Every OneBridge `.lnk` has raw SHA 256 and a typed target observation.
4. An allowed external target is flattened under the shortcut logical path.
5. A back-link to an already covered directory stops before child scanning.
6. Missing and permission-denied targets remain visible with distinct codes.
7. Full backend tests, production extraction, browser result display and remote
   release equality pass.
8. A scheduled full ingestion cannot replace Document Versions while an
   extraction Manifest for the same Source is active.
9. A SourceEntry with both current and historical Documents selects the current
   canonical path and does not produce `SOURCE_CHANGED`.
10. Every readable file, including metadata-only files, has raw SHA 256.
11. A readable UNC file beyond the legacy Windows path limit is hashed and
    cleaned through its unchanged logical path.
12. A second Scope Repair retains shortcut provenance for reused target files.

## Rollback

Restore the prior verified release and stop any new Scope Repair ingestion.
SourceEntry hashes, link path documents, extraction checkpoints and audit events
remain immutable evidence.

## References

* Microsoft MS-SHLLINK structure overview:
  https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-shllink/747629b3-b5be-452a-8101-b9a2ec49978c
* Microsoft CommonNetworkRelativeLink:
  https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-shllink/23bb5877-e3dd-4799-9f50-79f05f938537
* LnkParse3 1.6.0:
  https://pypi.org/project/LnkParse3/1.6.0/
