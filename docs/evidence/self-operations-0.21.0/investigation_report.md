# Governed self-operations issue center investigation

## Objective

Version 0.21.0 makes operational failure handling a first-class CAG
capability. Failures enter one durable lifecycle that supports deduplication,
AI boundary classification, an improvement proposal, independent AI review,
administrator approval, isolated implementation, replay evaluation and
closure or reopening.

## Prior gap

The Gateway already had task, ingestion, audit, queue and learning records.
Each subsystem retained its own outcome. There was no shared issue identity,
immutable occurrence ledger, approval gate or cross-subsystem closure
workflow. Supervisor failures also occurred outside the API process and needed
a restart-safe intake path.

## Implemented boundary

The release adds:

* physical UUID issue, occurrence, artifact and event records;
* stable per-project fingerprints and external event idempotency;
* secret sanitization before persistence;
* a PostgreSQL operations queue with a dedicated worker pool;
* failure intake from tasks, ingestions, queue execution, API exceptions and
  the local supervisor spool;
* AI triage and planning through the local ChatGPT-authenticated Codex runtime;
* an independent AI review artifact;
* explicit approve and reject transitions;
* an isolated `codex/improvement/<issue-code>` implementation branch;
* manual and bulk implementation evidence for external remediation;
* independent replay evaluation with close or reopen behavior;
* a polling management UI and matching online API documentation.

## Safety controls

An issue cannot enter the implementation workflow without an explicit
administrator approval record. Credential, authorization, policy and external
dependency classifications wait for administrator or external evidence. The
implementation task receives instructions that prohibit direct production
mutation, local commits and pushes. All stage transitions append immutable
events and versioned artifacts.

## Runtime validation

The live 0.20.0 runtime stayed active while the new release was tested on
isolated ports, a temporary SQLite database and two temporary PostgreSQL
databases. The production cutover gate confirmed zero queued or leased work,
three idle workers and no active knowledge ingestion.

The browser acceptance issue `OI-570E6001E7` reached `waiting_approval` with:

* boundary `cag_internal`;
* confidence `0.84`;
* two versioned AI artifacts;
* nine immutable timeline events;
* no browser console warning or error.

The isolated issue and all temporary runtime resources were removed after
validation. The screenshot is retained as release evidence.
