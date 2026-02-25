# MY_VOCAB — Custom Vocabulary

## Quick Start

1. **Edit configuration** in `vocab.env` (already populated by scaffold script)

2. **Edit the 3 vocab-specific SQL files** in `Builder/sql/`:
   - `create-general-concepts.sql` — Register vocabulary in OMOP tables (run once)
   - `source-ddl.sql` — Define staging tables for your mapping CSV columns
   - `load-source.sql` — Transform raw CSV data into the normalized `source_to_update` table

3. **Add mapping data** to `Mappings/mapping.csv`

4. **Run the pipeline**:
   ```bash
   # From repo root
   docker compose run runner MY_VOCAB/Builder/execute-pipeline.sh
   ```

5. **Inspect output** in `./output/` (delta CSVs + restore.sql)

## Directory Structure

```
MY_VOCAB/
├── vocab.env                          # All configurable parameters
├── Builder/
│   ├── execute-pipeline.sh            # Orchestration script
│   ├── revert-db.sh                   # Reset database to clean state
│   └── sql/
│       ├── source-ddl.sql             # EDIT: staging table schema
│       ├── load-source.sql            # EDIT: CSV -> source_to_update transform
│       └── create-general-concepts.sql # EDIT: vocabulary registration
├── Mappings/
│   ├── mapping.csv                    # Mapping data (CSV)
│   └── CONTRIBUTING.md                # Instructions for external contributors
├── Ontology/                          # Generated delta tables (pipeline output)
└── README.md                          # This file
```

## Pipeline Steps

1. Create staging tables (`source-ddl.sql`)
2. Load CSV data into staging (`\copy`)
3. Transform to normalized format (`load-source.sql`)
4. Reset ID sequence (`shared/revert-id-sequence.sql`)
5. Evaluate new vs existing concepts (`shared/evaluate-difference.sql`)
6. Stage standard concepts (`shared/update-standard.sql`)
7. Stage non-standard concepts (`shared/update-nonstandard.sql`)
8. Stage synonyms (`shared/update-synonym.sql`)
9. Detect mapping updates/deprecations (`shared/deprecate-and-update.sql`)
10. Deduplicate staging tables (`shared/pre-update.sql`)
11. Apply core update to vocab tables (`shared/execute-core-update.sql`)
12. Generate update log (`shared/message-log.sql`)
13. Export delta tables to CSV + restore.sql

## Reverting

To remove all custom concepts and start fresh:

```bash
docker compose run runner MY_VOCAB/Builder/revert-db.sh
```
