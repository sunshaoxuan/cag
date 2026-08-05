# Final receipt

## Scope

Version 0.22.7 adds local Codex API Key login support without changing the CAG
runtime boundary. The Gateway continues to use the Codex Agent app-server
process and does not become a direct OpenAI API client.

## Acceptance checklist

| Acceptance item | Result | Evidence |
|---|---|---|
| ChatGPT login remains supported | passed | Adapter and launcher tests |
| API Key login is accepted | passed | Adapter tests and live task |
| Real Codex Agent process is used | passed | `runtime.connected` provider and `app-server --stdio` source path |
| Agent thread and turn events remain available | passed | adapter event tests and live SSE |
| API Key is not read or stored by CAG | passed | source scan and process environment check |
| PostgreSQL and Redis remain the active services | passed | `/health/ready` |
| Gateway listens on all IPv4 interfaces | passed | live listener and Pester test |
| Frontend management console serves the release | passed | port 5173 HTTP 200 and production build |
| Tests and documentation are complete | passed | test results and versioned docs |

## Release state

The source changes are ready for the required `master` commit and push after
the final diff review. The live Gateway already reports version 0.22.7 from the
supervised process.
