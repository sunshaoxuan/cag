# Final receipt

Version 0.8.0 makes the HTTP API the primary execution entry point and treats
the web task page as a test console. Every accepted task has one Trace ID and
every persisted action has one Gateway global sequence.

The external API, idempotency contract, Task SSE, global Audit SSE, audit query
APIs and browser monitor passed automated and real local subscription-Codex
validation.

Production publication outside loopback remains blocked on Gateway caller
authentication, project authorization, HTTPS and rate limiting.
