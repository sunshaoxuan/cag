# Evidence index

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Original task was making progress at failure | Extraction event 86 completed at 14:05:43 UTC and failure event 87 recorded `overall_deadline` at 14:05:49 UTC | High | Production PostgreSQL history |
| Original public task did not report document progress | Generic Task had one `task.created` event while extraction had 87 internal events | High | Production PostgreSQL history |
| Aggregate deadline is removed | `backend/app/knowledge/extraction.py`, `backend/app/config.py` and regression test | High | Current source and test |
| Every manifest child reports a terminal event | Five-document test covers analyzed, model failure, metadata-only and excluded children | High | Fake Ollama integration test |
| Running API returns persisted progress | `_task_response` regression assertions and real 452-document response | High | Current API |
| Public monitor receives document progress | `audit-active-progress.png`, task event rows and zero browser Console issues | High | Current production browser |
| Worker remains live during extraction | Queue status reports current extraction item and a current heartbeat | High | Current production API |
| Production parent reached aggregation | Extraction `5cd11502-565f-4ec6-949a-539112cbfb7b` completed as `review_required` at 06:35:44 JST | High | Current production API |
| All production children reported terminal outcomes | Audit replay contains 128 `document.extracted`, 285 `document.extraction_failed` and 39 `document.excluded` events | High | Current production SSE replay |
| Public lifecycle is complete | Audit detail reports completed, 458 events and last global sequence 14712 | High | Current production API and Browser DOM |
| Audit reload avoids duplicate refreshes | Frontend single-flight test and `audit-completed-progress.png` | High | Unit test and current production browser |
| Browser Console is clean | Browser developer log query returned zero warning and error entries | High | Current production browser |
