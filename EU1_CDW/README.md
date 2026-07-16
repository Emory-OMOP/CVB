# EU1_CDW — Custom Vocabulary

The curated SSSOM mapping surface for Emory's **CDW (Cerner legacy)** source concepts. This package replaces the hand-edited SharePoint sheet behind the retired `omop_etl.datamappings` table. Design authority: `emory_omop_enterprise/docs/architecture/datamappings_ingest/datamappings_ingest_ADR.md` (ADR v3, approved).

`EU1_*` source vocabularies are CDW-side; `EU2_*` are Epic-side. Phase 1 keeps the whole CDW corpus in this one package — a per-source-vocabulary split is a later refinement.

## The three column widths

`Mappings/mapping.csv` carries **24 columns**, and two downstream consumers each take a prefix of it. Extension columns are appended strictly after column 21 so that a plain prefix trim produces both shapes — do not reorder them.

| Columns | Shape | Consumer | Produced by |
|---|---|---|---|
| 1–21 | Canonical CVB SSSOM (`source_concept_code` … `status`) | Postgres Builder staging (`temp.mapping`) | `scripts/trim-csv-columns.py` at `PIPELINE_COLS=21`, called by `Builder/execute-pipeline.sh` |
| 1–23 | Canonical 21 + `valid_start_date` + `valid_end_date` | Athena external table `omop_etl.src_mapping_sssom` | `scripts/package-mapping-release.py` |
| 1–24 | Release 23 + `source_frequency` | The curation sheet itself (git) | curators / `scripts/excel-to-csv.py` |

`source_frequency` is a workspace column: it informs curation priority but is not part of the warehouse contract, so it is trimmed at release. The Builder trimming to 21 and the release emitting 23 are **not** in conflict — they are different prefixes of the same sheet.

## Extension columns

| Column | Type | Notes |
|---|---|---|
| `valid_start_date` | ISO date (`YYYY-MM-DD`) | Migration normalizes the legacy corpus to `1970-01-01` |
| `valid_end_date` | ISO date (`YYYY-MM-DD`) | Migration normalizes the legacy corpus to `2099-12-31`; must be `>= valid_start_date` |
| `source_frequency` | numeric | Source-system row volume for the code; prioritization only |

All three are registered in `scripts/cvb_constants.py` (`KNOWN_EXTENSION_COLUMNS`) and checked by `scripts/validate-mapping-csv.py`. An unregistered column beyond 21 warns in CI rather than failing — but it will be silently dropped at release, so register it before relying on it.

## Release to S3

```bash
# Emit the 23-column, fully-quoted release artifact
python scripts/package-mapping-release.py EU1_CDW/Mappings/mapping.csv release/mapping_sssom.csv

# Publish (phase 1: manual; the release workflow wiring is deferred)
aws s3 cp release/mapping_sssom.csv s3://416-omop-etl-hub/global-data/external/mapping_sssom/

# Then, in emory_omop_enterprise (prod target):
dbt run-operation create_external_table_src_mapping_sssom
dbt build --select mapping_sssom
```

The external table reads OpenCSVSerDe with `skip.header.line.count=1`, so the artifact keeps its header row and quotes every field — the legacy LazySimpleSerDe ingest column-shifted 1,644 rows on embedded commas (ADR audit finding 2) and that must not recur.

## Quick Start (Builder)

1. **Edit configuration** in `vocab.env` (already populated by scaffold)

2. **Edit the 3 vocab-specific SQL files** in `Builder/sql/`:
   - `create-general-concepts.sql` — Register vocabulary in OMOP tables (run once)
   - `source-ddl.sql` — Define staging tables for your mapping CSV columns
   - `load-source.sql` — Transform raw CSV data into the normalized `source_to_update` table

3. **Add mapping data** to `Mappings/mapping.csv`

4. **Run the pipeline**:
   ```bash
   # From repo root
   docker compose run runner EU1_CDW/Builder/execute-pipeline.sh
   ```

5. **Inspect output** in `./output/` (delta CSVs + restore.sql)

## ID allocation

Registered in `id-registry.csv` as base `2003`. Ranges are half-open — the maxima are exclusive:

- Standard: `[2003000000, 2003500000)`
- Non-standard: `[2003500000, 2004000000)`
- Vocabulary concept: `2003499999`

Usable ids run `2003000000`–`2003999999`; `2004000000` is never used. Per D6 the **NS mint is the main path** (every CDW source code becomes a browsable non-standard concept, mapped to a community standard via `concept_relationship`); the S mint is the rare branch for codes with no community target. 2B ids are stable forever once used.

## Directory Structure

```
EU1_CDW/
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

## Reverting

To remove all custom concepts and start fresh:

```bash
docker compose run runner EU1_CDW/Builder/revert-db.sh
```
