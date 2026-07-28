# Managed credential reveal investigation

Release: 0.11.0

## User requirement

When an operator edits a maintained knowledge source, its saved username and
password or access token must load into the form. The password field must
support explicit display and copying.

## Existing path

1. The source form wrote the supplied credential into Windows Credential
   Manager.
2. PostgreSQL retained only an opaque `credential_ref` and optional username.
3. Collection workers resolved the credential through
   `KnowledgeCredentialStore.get()`.
4. Source list, detail, update, history and SSE responses did not expose the
   stored secret.
5. The edit form displayed only a placeholder, so the operator could neither
   inspect nor copy the current value.

## Implemented path

1. `KnowledgeService.reveal_source_credential()` resolves the source physical
   UUID and reads the matching Windows Credential Manager entry.
2. `POST /api/v1/knowledge/sources/{source_id}/credential/reveal` performs the
   explicit reveal action and returns the current username and secret.
3. The reveal response is marked `Cache-Control: no-store, private`,
   `Pragma: no-cache` and `X-Content-Type-Options: nosniff`.
4. The edit action loads ordinary source metadata first, then calls the reveal
   endpoint when `credential_configured` is true.
5. The credential remains masked initially. The operator can select Display,
   Hide or Copy.
6. Copy uses the Clipboard API and retains a compatibility fallback for local
   browser environments.

## Security boundary

The generic knowledge-source APIs, histories and SSE events remain
secret-free. Secret retrieval is isolated behind a semantically explicit POST
operation. Production deployment must protect this endpoint with the same
administrator authentication, project authorization and audit boundary as
credential rotation. The current local management console remains a trusted
operator environment.

## Conclusion

The missing behavior was in the edit and API retrieval path. Credential
storage and collector consumption were already present. Version 0.11.0 adds
the explicit operator retrieval path without changing the database schema.
