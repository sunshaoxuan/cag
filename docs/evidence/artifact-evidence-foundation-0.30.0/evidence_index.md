# Evidence index

| Evidence | Result | Boundary |
|---|---|---|
| Backend complete suite | 209 passed, 4 skipped, 85.07% coverage | PostgreSQL integration tests remain separately skipped by their existing opt-in gate |
| Frontend suite | 3 files, 23 tests passed | Component behavior |
| TypeScript and production build | passed | Static and bundle verification |
| Migration round trip | passed | Upgrade and downgrade through 0029 |
| Formal PostgreSQL | Alembic 20260813_0029 | Production state |
| Pre-migration backup | 5,106,219,859 bytes, SHA 256 recorded in deployment receipt | Local protected release backup |
| Production Artifact | `4791df72-e0ee-40b0-8a6a-15b82aedbafd` | Controlled non-business sample |
| Production replicas | 2 healthy replicas on D and C drives | Independent volume boundary |
| Production recovery | Primary removed, content read from replica, primary restored | Real execution |
| Object and database orphan check | 0 and 0 | Reconciliation and FK closure |
| Browser DOM | v0.30.0, 1 evidence object, 2 healthy replicas | Formal page |
| Browser Console | 0 warning, 0 error | CAG application console |
| Browser screenshot | `browser-artifact-summary-0.30.0.png`, SHA 256 `F35077E557CDF90EFBDD7E3535435B7820FDC1D73C1E45704C2DD29F32B1F0A1` | Cropped before customer source details |
| Historical knowledge status | `ready=false`, missing enterprise knowledge key | Inherited incident, still open |
