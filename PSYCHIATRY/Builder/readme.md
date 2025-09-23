# Psychiatry Vocabulary Pipeline

This repository documents the ETL pipeline for building and exporting psychiatry vocabulary data.  Below are two different levels of explanation: detailed (for developers) and high-level (for stakeholders).

---

## High level Pipeline
At a high level, the pipeline has five phases:
- Setup Environment – initialize folders and variables.
- Load Raw Sources – ingest CSV mapping files.
- QA & Staging – check data quality and prep staging tables.
- Core Update – update vocabulary tables.
- Export Deltas – export changes for integration.

```mermaid
flowchart TD

A[Setup Environment] --> B[Load Raw Sources] --> C[QA & Staging] --> D[Core Update] --> E[Export Deltas]

A:::phase
B:::phase
C:::phase
D:::phase
E:::phase

classDef phase fill:#e6f2ff,stroke:#3366cc,stroke-width:1px,rx:6,ry:6;
```

## Detailed Technical Pipeline
This diagram shows each command in the ETL process:
- Setup: prepare temp folders and environment.
- Load: create source tables and load mapping CSVs.
- QA/Staging: validate, clean, and prepare data.
- Update: apply core updates to vocabulary tables.
- Export: dump delta tables and export CSVs for downstream use.

```mermaid
flowchart TD

subgraph Inputs_and_Setup
  A1[rm -rf /tmp/output]
  A2[mkdir /tmp/output]
  A3[export SQL_DIRECTORY, MAP_DIRECTORY]
  A4[psql -f create-general-concepts.sql]
end

subgraph Load_Raw_Sources
  B1[psql -f source-ddl.sql]
  B2[psql -c \copy temp.psych_mapping FROM psych_mapping.csv]
  B2o[/psych_mapping.csv/]
  B3[psql -f load-source.sql]
  B4[psql -f revert-id-sequence.sql]
end

subgraph QA_and_Staging_Builds
  C1[psql -f evaluate-difference.sql]
  C2[psql -f update-standard.sql]
  C3[psql -f update-nonstandard.sql]
  C4[psql -f update-synonym.sql]
  C5[psql -f deprecate-and-update.sql]
  C6[psql -f pre-update.sql]
end

subgraph Core_Update_and_Logging
  D1[psql -f execute-core-update.sql]
  D2[psql -f message-log.sql]
  D3[psql -f create-delta-tables.sql]
end

subgraph Export_Deltas_and_Restore_Script
  E0[echo header >> restore.sql]
  E1[pg_dump --column-inserts temp.*_delta >> restore.sql]
  Eo1[/restore.sql/]

  E2[psql \copy temp.concept_delta TO concept_delta.csv]
  Eo2[/concept_delta.csv/]
end

A1 --> A2 --> A3
A3 --> A4
A3 --> B1
B1 --> B2
B2o --> B2
B2 --> B3 --> B4 --> C1
C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> D1
D1 --> D2 --> D3 --> E0
E0 --> E1 --> Eo1
E2 --> Eo2
```
