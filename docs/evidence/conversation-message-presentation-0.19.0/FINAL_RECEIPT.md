# Version 0.19.0 final receipt

## Delivered

* Gray intermediate answers grouped by Agent run and message item.
* Native disclosure control, collapsed by default and expandable on demand.
* Terminal answer populated only after `task.completed`.
* GitHub-flavored Markdown rendering for the final report.
* Version, changelog, requirements, frontend design and evidence updates.

## Acceptance

Backend, frontend, build, dependency audit and isolated browser gates passed.
The browser acceptance used Fake Runtime and consumed no external model quota.
The isolated environment was removed after evidence capture.

## Runtime cutover

The source release is ready for `origin/master`. The production Gateway still
serves 0.18.0 because ingestion
`126daf48-bddd-435c-8e1c-5dfe0a1ff730` was running and ingestion
`1e159684-2144-4b61-aac6-2ea8c7c1595a` was queued at the release gate.
Restarting the long-running service would violate the active-work
preservation requirement. Runtime cutover remains deferred until both jobs
reach a terminal state.

## Rollback

Revert the 0.19.0 release commit, restore the 0.18.0 frontend package and
restart the managed frontend and Gateway only after confirming no active
knowledge work would be interrupted.
