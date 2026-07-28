# Current release receipt

Version: 0.8.2

Date: 2026-07-28

Branch: `master`

## Delivered

* Port 5173 is the unified CAG visual management console.
* The console retains API testing, API audit, enterprise knowledge and
  capability governance in one routed application.
* Browser API and SSE requests use same-origin `/api` URLs.
* Frontend Nginx proxies `/api` to the host ChatGPT-authenticated Gateway.
* LAN browsers no longer resolve the Gateway as their own loopback address.
* HTML entry responses disable caching and hashed assets use immutable caching.

## Verified

* 62 backend tests passed with 88.69 percent coverage.
* 10 frontend tests and the production build passed.
* Compose configuration, frontend image build and `nginx -t` passed.
* LAN management console project API returned one project.
* Overview rendered 12 traces, 2 knowledge sources and 18 capabilities.
* API audit rendered 12 traces and received 3,500 SSE events.
* Browser console contained zero warnings and errors.
* Screenshot evidence was saved.

## Runtime boundary

Codex app-server remains a private local child process. Port 5173 exposes the
management frontend and its same-origin Gateway proxy. Port 8000 remains the
direct external API endpoint.

## Rollback

Deploy the prior `cag-frontend` image and recreate only the frontend service.
The host Gateway, database, task history and Codex runtime require no rollback.
