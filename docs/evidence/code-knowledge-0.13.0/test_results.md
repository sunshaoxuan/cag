# Test results

| Verification | Result |
|---|---|
| Backend pytest | 77 passed, coverage 86.39 percent |
| Frontend Vitest | 11 passed |
| TypeScript and production build | Passed |
| Docker Compose config | Passed |
| Gateway image build | Passed after manifest-name correction |
| Frontend image build | Passed |
| PostgreSQL migration up, down, up | Passed |
| Linux Tree-sitter Java parse | Passed, parser reported `tree-sitter` |
| Real Ollama Japanese code embedding | Passed, 1024 nonzero dimensions |
| Real Ollama bounded deep reranking | Passed, five complete UUID candidates and code evidence retained first |
| Real 0.13.0 ingestion | Passed, 3 files, 4 symbols, 3 relations and 4 documentation links |
| Real code detail API | Passed, resolved call and linked Markdown evidence |
| Browser route and real data | Passed at 5174 verification instance |
| Browser console | No messages |
| Browser screenshots | `code-knowledge-overview-0.13.0.png`, `code-knowledge-0.13.0.png` |

The first Gateway image build rejected the grammar alias `c_sharp`. The package
manifest reported `csharp`. The Dockerfile and language mapping now use the
manifest name and the rebuilt image passed.

The main 8000 Gateway continued its pre-existing network-share ingestion during
verification. A scheduler-disabled 0.13.0 instance on 8001 and a temporary
frontend on 5174 provided live acceptance without interrupting that scan.
