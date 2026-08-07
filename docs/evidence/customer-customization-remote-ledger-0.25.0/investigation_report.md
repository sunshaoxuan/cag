# Customer customization and remote ledger investigation

## Objective

The customer ledger extraction must analyze `２．カスタマイズ情報` and `６．リモート接続情報`. The first directory produces `customizations`. The second directory produces `vpns` and `environments`.

The organization used for live acceptance is sample data. Its code, name, directory name and physical scope are prohibited from becoming a general parameter, default value, routing rule or classification condition. Runtime scope resolution uses organization identity, source physical ID, business attributes and the catalog.

## Implemented behavior

1. Analysis template version 2 registers structured schemas for customization, VPN and environment objects.
2. Directory taxonomy requests only `customizations` under the customization directory and only `vpns` and `environments` under the remote connection directory.
3. Object list values create independent review candidates. Scalar conflict semantics do not merge distinct object records.
4. Scoped ingestion pushes the selected prefix into the connector and preserves entries outside the selected scope.
5. Prompt text and citation excerpts are independently scanned for secrets after stored chunks are decrypted.
6. Active ingestion identity includes analysis scope and scope prefix. Ingestion execution claims the queued record atomically before collection.

## Live result

Extraction `fc2519ed-509f-49de-8c49-625e330412d3` completed with `review_required` and `EXTRACTION_PARTIAL`. Partial coverage is explicitly reported and remains reviewable.

Coverage was 296 total documents, 68 ready, 59 analyzed, 119 failed, 118 excluded and 0.331461 coverage rate. The current result contains 21 customization candidates, 5 VPN candidates and 5 environment candidates. Evidence contains `[REDACTED_SECRET]` where credential material was detected.

The result records analysis template version 2, extractor `customer-ledger-v2` and model `qwen3:14b`.

## Sample boundary verification

Production code under `backend/app`, `frontend/src` and `scripts` was searched for the sample organization code and name. No match was found. Tests and evidence may name the sample because they verify real scope behavior.
