# ADR 0011: Managed source credential reveal

## Status

Accepted for version 0.11.0.

## Context

Knowledge source secrets are stored in Windows Credential Manager. Database
rows retain an opaque credential reference and optional username. Earlier
versions treated source credentials as write only. Editing a saved source
therefore showed an empty password field and prevented an administrator from
reviewing or copying the saved value.

The management workflow requires the saved value to load during editing and
support display and copy. Returning secrets in the general source registry
would expand exposure to every page load and API consumer.

## Decision

Add one explicit action:

```text
POST /api/v1/knowledge/sources/{source_id}/credential/reveal
```

The service resolves the source physical ID, reads its opaque credential
reference from Windows Credential Manager, and returns username and secret.
The response carries private no-store, no-cache and nosniff headers.

General source, ingestion, SSE, task and audit contracts continue to exclude
the secret. The frontend calls the action only when an operator edits a source
with `credential_configured=true`. The value loads into a masked password
field. Display, hide and copy are separate local UI actions.

## Security boundary

Credential reveal belongs to the trusted administrative management boundary.
Caller authentication and project authorization remain production admission
controls. Until they are implemented, deployments must restrict source
maintenance APIs to a trusted network.

## Verification

Acceptance requires:

* the reveal action reads the operating system credential store
* an unknown source or missing credential returns 404
* response caching is disabled
* list and update responses exclude the secret
* edit loads the exact saved value
* display changes the input from password to text
* copy writes the exact value to the browser clipboard
* browser console and screenshot checks pass

## Rollback

Restore version 0.10.0 and remove the reveal route and frontend actions. Stored
credentials remain unchanged because this version adds no database migration.
