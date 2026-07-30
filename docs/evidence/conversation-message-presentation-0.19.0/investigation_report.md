# Conversation message presentation 0.19.0 investigation

## Problem

The API test console projected every `agent.message` and
`agent.message.delta` into the main answer. In a deep Harness run, the
Executor response could therefore look terminal while verification Agents and
learning capture were still active.

## Verified path

1. Conversation SSE preserves every allowed runtime event.
2. `reflectLiveEvent` receives investigator, Executor and reviewer messages.
3. Version 0.18.0 assigned each message directly to `ChatTurn.answer`.
4. The actual terminal report arrives through `getTask` after
   `task.completed`.

## Implemented boundary

Version 0.19.0 keeps Agent messages in `intermediateMessages`, keyed by
`agent_run_id` plus `item_id`. The messages render in a gray native
`details` disclosure that is collapsed by default. `ChatTurn.answer` is
populated only from `final_report.summary` after the terminal event.

The terminal report uses `react-markdown` with `remark-gfm`. Raw HTML is not
enabled. Headings, lists, links, code, blockquotes and tables receive
management-console styling.

## Result

The user can distinguish live execution feedback from the final answer while
the complete SSE and audit history remain available in the adjacent monitor.
