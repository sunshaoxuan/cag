# Production deployment

## Backup

The pre-migration PostgreSQL custom-format backup is:

`D:\workspace\cag\backups\releases\0.30.0-20260813T133340Z\agent_gateway-pre-0.30.0.dump`

Size: 5,106,219,859 bytes.

SHA 256:
`5188C09A094BBC1E2136E0189E119B8249844318B47BAC7AC04BD28D71C9B347`

## Runtime

* Version: 0.30.0
* Listener: 0.0.0.0:8000
* Supervisor: Running
* Readiness: ready
* PostgreSQL and pgvector: ready
* Alembic: 20260813_0029

## Object evidence exercise

* Artifact physical ID: `4791df72-e0ee-40b0-8a6a-15b82aedbafd`
* SHA 256: `3dd8ec35f8f83b870b4b58240af1916d178bd5b1d57aa6dd2a8c5fb72583a733`
* Encryption: `application_aes_gcm:f438b8e78e049c9d`
* Healthy replicas: 2
* Primary volume: D
* Independent replica volume: C
* Read after primary disconnect: passed
* Repaired replicas: 1
* Orphan objects: 0
* Database replica orphans: 0

The controlled object contains no customer data. Its disk bytes differ from the
plaintext. Source Entry, Document, Chunk and embedding-cache counts did not
change during the exercise.

## Known inherited incident

The enterprise knowledge key is unavailable and the formal knowledge status is
degraded. This state existed before migration 0029. The release preserves old
ciphertext and all provenance. The Artifact key is independent and cannot be
used to decrypt or overwrite historical Chunks.
