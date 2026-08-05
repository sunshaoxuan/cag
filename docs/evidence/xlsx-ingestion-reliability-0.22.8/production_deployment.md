# 0.22.8 production deployment

Date: 2026-08-05

## Cutover gate

Before publication, the interactive, knowledge and operations queues had no
queued or leased items. Two interactive Workers, one knowledge Worker and one
operations Worker were idle. The managed supervisor was running and the
Gateway listened on `0.0.0.0:8000`.

The newest UPDS scheduled ingestion remained failed with
`uq_knowledge_ingestion_rejections_ingestion_path`, which is the defect fixed
by this release.

## Backup

The PostgreSQL custom-format pre-release backup is:

`D:\workspace\cag\backups\releases\0.22.8-20260805T1240Z\agent_gateway-pre-0.22.8.dump`

* size: 1768997244 bytes
* SHA256: `837E650A3A1B8BF95CD497C4F989D5ECABD5435C5F74D67296057FEAA5C79FB0`

The backup was copied from the PostgreSQL container and the temporary
container copy was removed. The active database was not overwritten.

## Publication and live acceptance

Commit, remote identity, managed cutover, schema revision, live browser and
full UPDS learning results are appended after each gate completes.
