# Operational decision brief investigation

Date: 2026-07-31

Version: 0.22.0

## Target issue

`OI-6B26534BF5` has physical ID
`ec0a212a-0aae-4bb5-9acd-85a6b14b3037`.

The 0.21.1 production record reported:

* status `waiting_approval`;
* approval status `pending`;
* boundary `cag_internal` with confidence `0.84`;
* occurrence count `2`;
* latest persisted outer Review recommendation `approve`.

The same Review artifact embedded a final report whose summary began with
`REVISE. Do not approve implementation` and listed seven blocking findings.
The approval projection and the independent Review therefore contradicted each
other.

## Root cause

The app-server runtime stored the final Agent message as a free-form summary.
The issue service persisted that report inside another artifact object and
derived approval from the presence of selected legacy fields. A Review with
commands or validation output could therefore produce an outer approval even
when its actual decision required revision.

The same representation forced administrators to read nested reports and
runtime events to reconstruct the problem, proposed correction and acceptance
criteria.

## Correction

Version 0.22.0:

1. validates planner and reviewer output against strict schemas;
2. stores an explicit implementation route;
3. stores a reviewer-facing decision brief;
4. exposes Review recommendation and blocker count as first-class fields;
5. enters `plan_revision_required` for invalid, incomplete, revise or blocked
   decisions;
6. repeats the Review gate in the approval API;
7. keeps complete artifacts and timeline events collapsed as audit evidence;
8. assigns issue event sequences with an atomic row counter.

## Route judgment

The issue boundary is CAG internal. The required correction changes CAG
planning, Review parsing, persistence, approval gates and management UI. It is
eligible for the governed `agent_self_improvement` route after a valid
independent Review and administrator approval. A human engineer remains an
available implementation route when the planner identifies protected code,
missing authority or judgment that cannot be delegated.

This judgment classifies the implementation authority. It does not approve the
seven unresolved findings in the historical plan.
