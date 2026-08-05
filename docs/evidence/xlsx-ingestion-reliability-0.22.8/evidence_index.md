# Evidence index

| Claim | Evidence | Confidence | Limitation |
|---|---|---|---|
| Target workbook has structured content | Product parser read 14 sheets, 1001 populated cells and 47 formulas | high | Read-only point-in-time source |
| XLSX text is semantic | Extractor and knowledge tests cover sheet names, coordinates, formulas and cached values | high | Charts and images remain excluded |
| Duplicate rejection paths are idempotent | Same-batch and cross-flush service regression | high | Final production run pending |
| Interactive work remains available | Fake Runtime task completes while knowledge Worker is delayed | high | Synthetic delay |
| File inventory is auditable | API query test and frontend search, paging and processor evidence test | high | Browser acceptance pending |
