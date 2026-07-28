# Current release test results

Date: 2026-07-28

Version: 0.8.2

## Automated

| Check | Result |
|---|---|
| Backend Pytest | 62 passed |
| Backend coverage | 88.69 percent |
| Frontend Vitest | 10 passed in 2 files |
| Frontend TypeScript and production build | Passed |
| Docker Compose configuration | Passed |
| Frontend image build | Passed |
| Nginx configuration | Passed |

All automated checks ran from an archive of the staged Git tree. Concurrent
knowledge-source changes in the working tree were excluded.

## Live management console

The staged frontend image was deployed to the existing `cag-frontend-1`
container. The frontend uses same-origin `/api` requests and Nginx forwards
them to `host.docker.internal:8000`.

| Probe | Result |
|---|---|
| `http://192.168.20.54:5173/health` | HTTP 200 |
| `http://192.168.20.54:5173/api/v1/projects` | HTTP 200, 1 project |
| Overview through LAN IP | 12 audit traces, 2 knowledge sources, 18 capabilities |
| API audit route | 12 traces and 3,500 SSE events received |
| Browser warning and error console | 0 entries |
| HTML cache policy | `no-cache, no-store, must-revalidate` |
| Hashed asset cache policy | `public, max-age=31536000, immutable` |

The live host Gateway process continues to report 0.8.1 because this patch
changes the frontend connection boundary and did not restart the host process
while unrelated 0.9.0 backend work was present in the shared working tree. The
management console and proxied API path are live.

Screenshot:

```text
docs/evidence/screenshots/cag-management-console-0.8.2.png
```
