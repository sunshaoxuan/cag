# 0.22.6 测试结果

## Automated

| Command | Result |
|---|---|
| `frontend: pnpm test` | 3 test files, 17 tests passed |
| `frontend: pnpm build` | TypeScript and Vite production build passed |
| `backend: .\\.venv\\Scripts\\python.exe -m pytest` | 119 passed, 2 skipped, 6 warnings; coverage 85.89% |
| `docker compose build frontend` | Passed |
| `docker compose up -d --no-deps frontend` | Frontend container recreated and started |

## Browser

| Surface | Result |
|---|---|
| `http://127.0.0.1:5173/code-knowledge`, 1280x720 | Button and all three controls shared `y=680`, `bottom=730`, `height=50` |
| `http://127.0.0.1:5173/code-knowledge`, 680x900 | Controls and button stacked at 563px width; button height 50px |
| Console warnings and errors | `[]` |
| Desktop screenshot | `docs/evidence/screenshots/code-knowledge-search-action-0.22.6-desktop.png` |
| Mobile screenshot | `docs/evidence/screenshots/code-knowledge-search-action-0.22.6-mobile.png` |

## Runtime boundary

The frontend container was rebuilt and restarted successfully. The host
Gateway remained on live version `0.22.5` because the queue status showed one
knowledge worker actively processing item
`665428ae-fec3-4a6b-af42-8ab2b61144b9`; restarting the Gateway was deferred to
preserve that active work. The source, tests and release files are `0.22.6`.

## Notes

The first full backend run exposed stale 0.22.5 version assertions and one intermittent knowledge-ingestion event-count failure. The release metadata and assertions were updated, and the complete suite passed on the second run.
