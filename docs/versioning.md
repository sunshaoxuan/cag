# Versioning and release records

## Version policy

The repository uses Semantic Versioning.

* Patch: defect repair without contract expansion.
* Minor: a completed implementation phase or backward-compatible feature group.
* Major: incompatible public API or deployment boundary changes.

## Required files per version

Every version updates:

* `VERSION`
* `CHANGELOG.md`
* `README.md`
* `docs/requirements-matrix.md`
* Affected architecture, API, security and deployment documents
* `docs/evidence/test_results.md`
* `docs/evidence/FINAL_RECEIPT.md`

## Required release procedure

1. Confirm the active branch is `master`.
2. Run unit and integration tests.
3. Run `git diff --check`.
4. Update evidence and version documents.
5. Commit the verified version.
6. Push directly to `origin/master`.
7. Confirm the remote `master` commit equals the local commit.

No other branch is permitted for this repository.
