# Long-term memory panel spacing investigation

## Finding

The `/memory` route rendered its governance surface with only `panel` and
`page-panel`. The shared padding rule listed the Knowledge, Capability, Audit,
Conversation, Execution and Result panels explicitly. The Memory panel was
absent, so its heading and empty state started at the outer border.

## Correction

* Added the semantic `memory-console` class to the governance panel.
* Added `memory-console` to the shared 30 pixel padding rule.
* Added a bordered, rounded and centered `memory-empty` inner surface.
* Added a component assertion for the panel and empty-state classes.

## Evidence

* `frontend/src/App.tsx`
* `frontend/src/styles.css`
* `frontend/src/App.test.tsx`
* `docs/evidence/screenshots/memory-panel-spacing-0.9.1.jpg`
