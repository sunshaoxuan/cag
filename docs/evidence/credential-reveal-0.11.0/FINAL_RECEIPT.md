# Final receipt

Release: 0.11.0

Status: implementation, automated tests and live runtime acceptance complete.
Git publication is recorded by the enclosing repository history.

Delivered:

* Explicit retrieval of a saved source credential from Windows Credential
  Manager
* Edit-form loading of the saved username and secret
* Masked-by-default secret display with Display, Hide and Copy actions
* Cache prevention headers for the reveal response
* Generic API, event and history paths remain secret-free
* API, frontend, architecture, security and ADR documentation

Live acceptance:

* Host Gateway reported version 0.11.0 and the frontend used the host Gateway
  proxy.
* A synthetic credential was saved through the API and resolved from Windows
  Credential Manager with an exact-value match.
* Generic source output did not contain the synthetic secret.
* Edit loaded the saved username and secret while keeping the input masked.
* Display, Hide and Copy completed in the live browser.
* The Windows clipboard contained the exact synthetic value after Copy.
* Browser console warnings and errors were empty.
* The synthetic credential and clipboard value were cleared after acceptance.

Security condition:

* Production exposure requires administrator authentication, project
  authorization and audit coverage for credential reveal.

Rollback:

1. Deploy version 0.10.0.
2. Remove the credential reveal route and its frontend call.
3. Keep existing Credential Manager entries and opaque database references.

No database downgrade is required.
