# Evidence index

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Target was never claimed in the shared queue | QueueItem `d567e012-4610-446f-adc1-b0a052aea091`, initial `attempt_count=0` | High | Historical live query |
| One full ingestion occupied the only worker | Queue status worker item `fb58ec93-cfb1-4df0-a315-a3fb91c69d4f`, 742,066 chunk checkpoint | High | Production snapshot |
| Dedicated extraction worker claimed the task | Queue status worker process and target QueueItem in `extraction` | High | Production API |
| Prompt truncation and runner failure occurred | Ollama logs with 10,879 to 16,501 token prompts and CUDA runner termination | High | Runtime log |
| Prompt bounding restored throughput | Ollama generation requests mostly completed in 1 to 4 seconds with no truncation in the acceptance window | High | Runtime log |
| Original action completed | Generic Task `completed`, extraction `review_required`, QueueItem `completed` | High | Production API and PostgreSQL |
| Extraction UI is visible | `cag-extraction-queue-status.png` | High | CAG page only |
| CAG Console is clean | Browser Console returned zero warning or error records | High | Current browser tab |
| OneOps browser verification is blocked | `oneops-iab-domain-auth-pending.png`, Edge DOM `ERR_BLOCKED_BY_CLIENT` | High | Authenticated OneOps screenshot missing |
| Final runtime has one current worker set | Queue API returned five current worker registrations, all owned by PID 13800; process inspection found one worker child and one API listener | High | Historical worker rows remain as audit records with stopped heartbeats |
| Target remains terminal after restart | QueueItem `d567e012-4610-446f-adc1-b0a052aea091` is `completed` in `extraction`, attempt count 5, with no lease owner or lease expiry | High | Current production PostgreSQL query |
