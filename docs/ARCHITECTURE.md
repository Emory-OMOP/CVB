# CVB Architecture — descriptive inventory

**What this document is.** A description of what CVB *is* as of the commit named below: its inputs, the reference data it requires, which modules are alive, how it connects to Emory's warehouse, and how a build is actually run. Every load-bearing claim carries a `file:line` citation. Where the code does not settle a question, this document says **UNCERTAIN** rather than guessing.

**What this document is not.** It is not a design record and it rules nothing. CVB's design authority is [`docs/architecture/cvb_builder_ADR.md`](architecture/cvb_builder_ADR.md) (D1–D9, Accepted 2026-07-23), whose standing address is the atlas node `cvb-builder-adr`. Where a decision is needed, this document points there. Several things described below are known defects; they are inventoried, not resolved.

**Anchor.** All citations are against the tree at `d6afddd` ("Merge pull request #5 from Emory-OMOP/docs/cvb-builder-adr"), the tip of `main`. Two refs exist that are *not* this tree and must not be conflated with it:

| Ref | What it is | Status |
|---|---|---|
| `chore/cvb-interval-resolution` @ `128c39e` | One commit implementing ADR D4/D5/D6/D9 against the shared SQL | **Parked, unmerged**, pending the substrate consult (§7) |
| the shared checkout at `~/git_repos/org__Emory-OMOP/CVB` | Several merges behind, plus uncommitted provenance WIP | Not a description of the system; per ADR D2 (`cvb_builder_ADR.md:55`) committed refs are the only reviewable surface |

Where `128c39e` would change something material, this document says so explicitly and marks it as *not shipped*. Reading its facts as current state is precisely the error this document exists to prevent.

> ### Terminology: two different things are called "Athena"
>
> **OHDSI Athena** (`athena.ohdsi.org`) is the download site for the licensed OMOP vocabulary bundle. **AWS Athena** is the query engine over S3/Glue where Emory's warehouse lives. Almost every occurrence of the word "Athena" *inside this repo* means OHDSI Athena — including `docker/init-db/01-create-vocab-schema.sql:5`, the code comment at `update-nonstandard.sql:70`, and the download instructions in `.MIMIC/Ontology/readme.md:17`. This ambiguity has already misled one working session. This document writes **OHDSI Athena** or **AWS Athena** in full, never bare "Athena".

---

## 1. What CVB is

CVB (Custom Vocabulary Builder) turns per-package SSSOM `mapping.csv` sheets into custom OMOP concepts in the 2-billion id space, plus a set of delta CSVs mirroring the OMOP vocabulary tables. A *package* is a directory (`EU1_CDW/`, `EU2_Flowsheets/`, `_TEMPLATE/`) holding a curated mapping sheet, a per-vocabulary config (`vocab.env`), three per-vocabulary SQL files, and an `Ontology/` directory for promoted output. The build is a 12-step `psql` pipeline (`EU1_CDW/Builder/execute-pipeline.sh:54-153`) running against a PostgreSQL database that must already hold the licensed OHDSI vocabulary; it reads the sheet, works out which source codes have no custom concept yet, mints ids inside the package's reserved range, writes them into `vocab.*`, and exports the 2B-range rows as CSVs to `/tmp/output` (`execute-pipeline.sh:196-199`).

**What CVB is not.** CVB is not the mapping-sheet release surface. The same `mapping.csv` feeds two independent releases of two different artifacts, and the ADR names them as deliberately separate (`cvb_builder_ADR.md:21`): the **sheet-release surface** publishes the curated mapping *input* to AWS Athena via `scripts/package-mapping-release.py` (Seam A, §5), and the **delta-release surface** publishes the minted *output* via committed `Ontology/` directories zipped by `scripts/package-release.sh` (Seam B, §5). Only the first is built. CVB is also not a concept *store*: it has no queryable surface of its own, no API, and no serving layer — its products are CSV files and rows in a disposable Postgres.

CVB is a public repo with external consumers (the ADR cites TuftsCTSI lineage and public releases as the reason its design record lives here rather than in the enterprise repo, `cvb_builder_ADR.md:47`). Emory is one user of CVB, not the only one — a distinction that matters to §6.

---

## 2. Inputs

### 2.1 `<PACKAGE>/Mappings/mapping.csv` — the primary input

The curated SSSOM sheet. Read by `scripts/trim-csv-columns.py` (invoked at `execute-pipeline.sh:72`), `\copy`'d positionally into `temp.mapping` (`:73`), then normalized into `temp.source_to_update` by the per-package `load-source.sql`.

The canonical 21 pipeline columns are defined once, in `scripts/cvb_constants.py:16-38` (`EXPECTED_COLUMNS`): `source_concept_code`, `source_concept_id`, `source_vocabulary_id`, `source_domain`, `source_concept_class_id`, `source_description`, `source_description_synonym`, `relationship_id`, `predicate_id`, `confidence`, `target_concept_id`, `target_concept_name`, `target_vocabulary_id`, `target_domain_id`, `mapping_justification`, `mapping_tool`, `author_label`, `review_date`, `reviewer_name`, `reviewer_specialty`, `status`.

**The three packages do not agree on the header.** Verified by reading each file's line 1:

| Package | Cols | Data rows | Header shape |
|---|---|---|---|
| `_TEMPLATE/Mappings/mapping.csv:1` | 21 | 0 (header only) | canonical exactly |
| `EU1_CDW/Mappings/mapping.csv:1` | 24 | 36,858 | canonical 1–21 intact, then `valid_start_date` (22), `valid_end_date` (23), `source_frequency` (24) — extensions appended strictly after 21 |
| `EU2_Flowsheets/Mappings/mapping.csv:1` | 22 | 57,428 | cols 1–20 canonical, then **`ws_frequency` at 21** and `status` displaced to 22 |

**EU2's shape is a live defect, not a variation.** `execute-pipeline.sh` trims to `PIPELINE_COLS=21` (`EU2_Flowsheets/Builder/execute-pipeline.sh:65`) and `\copy`s positionally into `temp.mapping`, whose 21st column is `status` (`EU2_Flowsheets/Builder/sql/source-ddl.sql:37`). EU2's `ws_frequency` values therefore land in `temp.mapping.status`, and `status` never arrives at all. Both are declared `TEXT`, so nothing errors — the shift is silent. `ws_frequency` is non-empty on 25,810 of 57,428 rows. It is registered in `KNOWN_EXTENSION_COLUMNS` (`scripts/cvb_constants.py:55`) solely so CI stays green, with the comment "EU2_Flowsheets file drift". Recorded in the ADR backlog (`cvb_builder_ADR.md:195`). **UNCERTAIN:** the blast radius. No shared SQL branches on `status`, so the immediate build effect appears to be data loss rather than misbehavior, but this was traced statically only.

EU1_CDW documents its three deliberate prefix widths — 1–21 to the Builder, 1–23 to the release artifact, 1–24 as the curation sheet — at `EU1_CDW/README.md:11-17`.

Measured content of the two live sheets (CSV-aware parse, not naive comma-splitting):

| | EU1_CDW | EU2_Flowsheets |
|---|---|---|
| data rows | 36,858 | 57,428 |
| distinct `source_concept_code` | 36,147 | 55,937 |
| `exactMatch` / `broadMatch` / `narrowMatch` / `relatedMatch` | 34,298 / 235 / 0 / 0 | 5,789 / 19,105 / 4,242 / 28 |
| `noMatch` | 2,325 | 28,264 |
| rows with an explicit `relationship_id` | 34,533 | 29,045 |
| `source_concept_id` populated | **0 rows** | 57,428 rows |
| `target_concept_id` on `noMatch` rows | `0` on all 2,325 | `0` on all 28,264 |

Two consequences worth naming. First, EU1's `source_concept_id` column is empty on every row — that column is what the mint fills, and it is the column 37 downstream CDW join sites already select (§5). Second, `load-source.sql` discards the sheet's `source_concept_id` on load regardless (`EU1_CDW/Builder/sql/load-source.sql:68`, `NULL AS source_concept_id`), so a re-run does not read back previously minted ids from the sheet; id continuity comes from the database state, not the sheet (§3.3).

### 2.2 `<PACKAGE>/vocab.env` — per-package configuration

Sourced at `execute-pipeline.sh:20`, and read independently by the Streamlit app (`apps/mapping-contributor/lib/db.py`). Every variable and its consumer:

| Variable | Meaning | Passed to |
|---|---|---|
| `VOCAB_NAME` | display name | log output, promote paths |
| `VOCAB_ID` | OMOP `vocabulary_id` | `-v vocab_id` → `execute-core-update.sql` (`:145`), `create-delta-tables.sql` (`:163`) |
| `DB_NAME` | Postgres database name | `PG_DB` (`:34`) |
| `ID_RANGE_MIN` / `ID_RANGE_MAX` / `ID_RANGE_START` | S range bounds and descending-sequence start | `revert-id-sequence.sql` (`:87-91`); `ID_RANGE_MIN` also to steps 5 and delta creation |
| `NS_RANGE_MIN` / `NS_RANGE_MAX` | NS range bounds | `update-nonstandard.sql` (`:117-120`); `NS_RANGE_MAX` doubles as the upper bound for step 5 and delta creation (`:104`, `:165`) |
| `VOCAB_CONCEPT_ID` | the vocabulary's own concept id | `-v vocab_concept_id` → `execute-core-update.sql` (`:146`) |
| `MAPPING_FILES` / `STAGING_TABLES` | order-matched lists driving the load loop | `:66-75` |

Both live packages set `MAPPING_FILES="mapping.csv"` and `STAGING_TABLES="temp.mapping"` (`EU1_CDW/vocab.env:16-17`, `EU2_Flowsheets/vocab.env:16-17`). Note the deliberate overloading at `execute-pipeline.sh:104` and `:165`: steps 5 and the delta creation receive `id_range_min=${ID_RANGE_MIN}` paired with `id_range_max=${NS_RANGE_MAX}` — the union of both ranges, not the S range. The inline comment at `:97-101` explains why. ADR D4 (`cvb_builder_ADR.md:79-87`) names this interval `FULL_SPAN` and rules that it should be passed under distinct variable names; **that rename is not shipped on this tree.**

### 2.3 `id-registry.csv` — the range allocation authority

Seven rows at the repo root (`id-registry.csv:4-10`), with half-open `[min, max)` semantics stated in the header comment (`:1-2`):

| vocab | base | S range | NS range |
|---|---|---|---|
| Winship | 2000 | `[2000000000, 2000500000)` | `[2000500000, 2001000000)` |
| EU2_Flowsheets | 2001 | `[2001000000, 2001500000)` | `[2001500000, 2002000000)` |
| BHC | 2002 | `[2002000000, 2002500000)` | `[2002500000, 2003000000)` |
| EU1_CDW | 2003 | `[2003000000, 2003500000)` | `[2003500000, 2004000000)` |
| MIMIC | 2062 | `[2062000000, 2062500000)` | `[2061500000, 2062000000)` ← inverted |
| PSYCHIATRY | 2072 | `[2072000000, 2072500000)` | `[2071500000, 2072000000)` ← inverted |
| GIS | 2076 | `[2076000000, 2076500000)` | `[2075500000, 2076000000)` ← inverted |

Read by `scripts/new-vocab.sh` for collision checking and appended to on scaffold (`new-vocab.sh:164`). The ADR names it the **sole** allocation authority (D4, `cvb_builder_ADR.md:75`) and the three archived vocabularies' inverted layouts grandfathered-frozen (D5.3, `:101`). The registry's own rows carry no such annotation on this tree — D5.3's "annotated with registry comment lines" is not shipped.

**UNCERTAIN:** `Winship` (2000) and `BHC` (2002) have registry rows but no package directory anywhere in the repo. They may be reservations held for work living elsewhere.

**Stale duplicate:** `README.md:6-14` carries a "Reserved Ranges" table that disagrees with the registry (it lists GIS at 2.0515–2.0525, which matches no registry row). ADR D4 rules the registry authoritative and the README table stale; the correction is not shipped.

### 2.4 Reference data — see §3

The licensed OHDSI vocabulary is an input, and the largest one. It gets its own section because "which tables must be populated before a build" is the question this document exists to answer.

### 2.5 Runtime inputs

`PGHOST` / `PGUSER` from the compose environment, or a host as `$1` (`execute-pipeline.sh:32-33`); `PGPASSWORD: cvb_local` (`docker-compose.yml:27`). The repo is bind-mounted at `/workspace` and `./output` at `/tmp/output` (`docker-compose.yml:28-30`), which is why the build's "output directory" is a host directory.

### 2.6 Upstream extraction SQL (not run by the Builder)

`EU2_Flowsheets/raw_for_fca/*.sql` are hand-run against **Epic Clarity**, not against the CVB Postgres: `fca_master_extract.sql:2` says "Run in Clarity SQL client, export results as CSV"; `flowsheet_frequency.sql:8` reads `clarity_onprem_omop.ip_flwsht_meas` and is where the `ws_frequency` column of §2.1 originates. These feed the FCA pipeline (§4), which produces `mapping.csv` — they are inputs to the *curation* of the input, one level up from the Builder.

### 2.7 Other CSVs in `Mappings/` are not inputs

`EU2_Flowsheets/Mappings/` also holds `atomic_enriched.csv`, `clinical_review.csv`, `unmappable_items.csv` and about a dozen others. These are FCA working files. The Builder reads only `MAPPING_FILES` from `vocab.env`, which is `mapping.csv` in every package; `scripts/validate-mapping-csv.py` warns rather than errors on the rest.

---

## 3. Reference-data requirement — what must be populated before a build

**This is the section whose absence caused a working session to design a vocabulary-storage scheme from scratch.** The short answer: a CVB build requires a PostgreSQL database already loaded with the licensed OHDSI vocabulary, and the repo contains no procedure that loads it.

### 3.1 The schema is created empty

`docker/init-db/01-create-vocab-schema.sql` creates schemas `vocab` and `temp` (`:8-9`) and issues `CREATE TABLE IF NOT EXISTS` for 13 tables: `concept`, `concept_relationship`, `concept_ancestor`, `concept_synonym`, `vocabulary`, `concept_class`, `domain`, `relationship`, `source_to_concept_map`, `mapping_metadata`, `concept_relationship_metadata`, `mapping_exceptions`, `review_ids`. Its own header states the position plainly (`:5-6`):

> `NOTE: Base OMOP vocabulary data (Athena) must be loaded separately (licensed). This schema is empty by default.`

("Athena" there is **OHDSI Athena**.) So every table exists structurally; the question is which ones must also contain *rows* from the licensed bundle.

### 3.2 Which tables must be populated, on this tree

| Table | Must hold licensed data? | Where it is read | Consequence if empty |
|---|---|---|---|
| `vocab.concept` | **Yes — hard** | `update-nonstandard.sql:69` (`INNER JOIN vocab.concept cd ON cc.target_concept_id = cd.concept_id`), plus `:539`, `:568`, `:671`; `update-standard.sql:52`; `execute-core-update.sql:304-305` | The NS mint produces **nothing**. The join at `:69` is inner, so a mapping row whose target is absent is silently dropped; it also supplies the minted concept's `domain_id` and `concept_class_id` (`:48`, `:50`). |
| `vocab.concept_ancestor` | **Yes, for hierarchy** | `update-standard.sql:420` (`INNER JOIN vocab.concept_ancestor ca ON css.target_concept_id = ca.descendant_concept_id`) | Custom S concepts inherit their target's ancestor closure. Empty table → the `WITH parent_hierarchy` insert contributes zero rows and the build **succeeds with an incomplete `concept_ancestor_delta`**. Silent degradation, not failure. |
| `vocab.concept_relationship` | **Yes** | `update-standard.sql:380`; `update-nonstandard.sql:497`; `execute-core-update.sql:67,:130,:143,:156,:169`; `deprecate-and-update.sql:23` | Dedup against already-existing edges and deprecation detection stop working. |
| `vocab.concept_synonym` | **Yes** | `update-synonym.sql` | Synonym dedup stops working. |
| `vocab.source_to_concept_map` | **Yes** | `update-nonstandard.sql:602`; `execute-core-update.sql:188,:198,:279` | STCM dedup and update detection stop working. |
| `vocab.domain`, `vocab.relationship`, `vocab.concept_class` | **Yes, for export** | `create-delta-tables.sql:23,:25,:29` only | The corresponding delta CSVs come out empty. Not read during minting. |
| `vocab.vocabulary` | Written, and read for export | `create-delta-tables.sql:27`; `execute-core-update.sql:322` | The vocabulary's own row is created by `create-general-concepts.sql` (§6), not by the bundle. |
| `vocab.mapping_metadata` | No — CVB-owned | `update-nonstandard.sql:658,:676` | Allocates `mapping_concept_id` by `count(*)`; starts empty and grows. |
| `vocab.mapping_exceptions`, `vocab.review_ids` | No — local, optional | `pre-update.sql:68-76`; `update-nonstandard.sql:506-507,:633,:673` | Local exclusion list and reviewer lookup; created empty and usable empty. |

**Bottom line for this tree:** an execution environment needs the full licensed `concept`, `concept_ancestor`, `concept_relationship`, `concept_synonym` and `source_to_concept_map` tables, plus `domain`/`relationship`/`concept_class`. `concept_ancestor` is typically the largest table in the OMOP vocabulary by a wide margin, so its inclusion materially changes what "host the Builder somewhere" costs.

### 3.3 What the parked commit changes — and that it is not shipped

The parked commit `128c39e` retires the automated S source-item mint per ADR D9, which removes the only block that reads the `concept_ancestor` *closure* (the `parent_hierarchy` join above). On that branch `update-standard.sql` is 94 lines; on this tree it is **471** and the join is live at `:420`. If and when `128c39e` lands, the reference-data requirement shrinks to `concept`, `concept_relationship`, `concept_synonym`, `source_to_concept_map`, with `concept_ancestor` touched only at `LIMIT 0` for table shape plus 2B-range writes.

Two further claims that are true only of the parked branch and false here:

- **NS id allocation.** On this tree, `update-nonstandard.sql:46` reads `row_number() OVER (ORDER BY source_concept_code) + (SELECT COALESCE(max(concept_id), :ns_range_min) FROM vocab.concept WHERE concept_id < :ns_range_max AND concept_id > :ns_range_min)`. The parked branch changes the fallback to `:ns_range_min - 1`. As written here, the first id minted into an empty range is `ns_range_min + 1`, so `ns_range_min` itself is never allocated — an off-by-one at the range floor, consistent with the strict `> :ns_range_min` filter on the same line. This is arithmetic, not a sequence: it is portable set-based SQL, and it is *ordered*.
- **The Postgres sequence.** `vocab.master_id_assignment` (`revert-id-sequence.sql:5-10`, descending, `MINVALUE :id_range_min`, reseeded from existing minima at `:12-16`) is consumed at exactly one site: `update-standard.sql:37`, `nextval(...)` in the S mint. On this tree that path is live and the sequence is load-bearing for every S concept. Under D9 it would serve `create-general-concepts.sql` alone. So the claim "the mint requires a Postgres `nextval` allocator" is **true of the S path on this tree and false of the NS path in either case** — the ~36.5k NS concepts EU1 needs never touch the sequence.

### 3.4 No load procedure exists

**UNCERTAIN — and this is the load-bearing uncertainty.** No script, workflow, Makefile, or README step in this repo loads the licensed OHDSI bundle into the Postgres. `docker/init-db/01-create-vocab-schema.sql:5` says it "must be loaded separately" and nothing does it. `scripts/seed-from-ontology.sh` — which would load *CVB's own* committed deltas back, a different and smaller job — does not exist either; it is an ADR backlog item (`cvb_builder_ADR.md:116`, D6.3). The runbook rule D6.3 states ("never run an incremental build for a vocab with committed deltas against an unseeded DB") therefore has no tooling behind it.

Related gap: `docker-compose.yml` sets no `POSTGRES_DB`, so the init script runs against the default `postgres` database, while `vocab.env` points the build at `eu1_cdw_vocabulary` / `eu2_flowsheets_vocabulary`. Creating and initializing that database is done by `scripts/new-vocab.sh:146-160` at scaffold time, or by the two manual commands it prints at `:158-159`. A fresh clone plus `docker compose up` alone does not yield a buildable database.

---

## 4. Module inventory

| Module | What it is | Status | Evidence |
|---|---|---|---|
| `Builder/sql/shared/` (12 files, 2,018 lines) | The canonical pipeline SQL | **ACTIVE** | Invoked as steps 4–12 by every package's `execute-pipeline.sh` (`EU1_CDW/Builder/execute-pipeline.sh:87-153`); governed by the ADR |
| `<PACKAGE>/Builder/execute-pipeline.sh` | Per-package orchestrator, one full copy per package | **ACTIVE, duplicated** | ADR D7 (`cvb_builder_ADR.md:132`) rules it should become a 2-line shim over a canonical root copy; not shipped |
| `Builder/sql/tests/test_multirow_pipeline.sql` | Multirow-pipeline assertion suite | **ACTIVE — but unwired** | Exists; no workflow or script invokes it. **UNCERTAIN** whether it is ever run |
| `EU1_CDW/` | Cerner CDW legacy vocabulary, base 2003, 36,858-row sheet; replaces the retired `omop_etl.datamappings` SharePoint sheet | **ACTIVE** | `EU1_CDW/README.md:3`; `id-registry.csv:10`; `Ontology/` holds only `.gitkeep` — never built |
| `EU2_Flowsheets/` | Epic flowsheet vocabulary, base 2001, 57,428-row sheet | **ACTIVE** | `id-registry.csv:9`; the ADR calls it "the one live package" (`:9`); `Ontology/` holds only `.gitkeep` |
| `_TEMPLATE/` | Scaffold copied by `new-vocab.sh` | **ACTIVE, and currently in sync** | ADR D7 (`:138`) records the historical drift — `_TEMPLATE` froze at `28b8b88` while EU2 advanced at `48bb5ae`, and EU1_CDW was scaffolded from EU2 rather than from `_TEMPLATE`. PR #3 back-ported the fixes, and on this tree `_TEMPLATE/Builder` is byte-identical to `EU2_Flowsheets/Builder` apart from `create-general-concepts.sql`, the one designed-per-vocab file — the end state D7 predicted (`:140`). EU1's copies differ from EU2's only in comments. **The drift is cured; the mechanism that produced it is not** — the shims and CI drift gate D7 specifies are unshipped, so nothing prevents recurrence |
| `EU2_Flowsheets/fca/` (26 modules) | Formal Concept Analysis pipeline: builds an item × attribute incidence matrix from Clarity extracts, computes the concept lattice, classifies items atomic/compositional/unmappable, generates `mapping.csv` | **ACTIVE — upstream of the Builder, not part of it** | `fca/run_pipeline.sh` orchestrates; `EU2_Flowsheets/pyproject.toml` packages it; explicitly out of scope for the ADR (`:23`). Note `run_pipeline.sh:11` hardcodes an absolute path to one developer's machine |
| `EU2_Flowsheets/raw_for_fca/` | Clarity extract SQL + versioned artifacts feeding FCA | **ACTIVE (data)** | §2.6 |
| `EU2_Flowsheets/methodology/unmappable_clinical_review/` | Subagent-driven clinical review of 38,192 unmappable items | **DORMANT (frozen archive)** | Its README states "Status: Complete (2026-03-08)"; its Python files are byte-identical copies of their `fca/` counterparts |
| `apps/mapping-contributor/` (Streamlit) | Browse/map UI and bulk upload over `Mappings/*.csv`, with optional concept search against a local Postgres | **DORMANT** | No workflow, script, or README outside its own directory references it; out of scope per ADR `:23`; its DB layer hardcodes `localhost:5432` and degrades when the DB is offline. Five near-duplicate one-off scripts `apply_batch_mappings{,_02…_05}.py` sit beside it |
| `scripts/cvb_constants.py` | Single source for column, predicate, and tool vocabularies | **ACTIVE** | Imported by validate / coverage / excel / package-mapping-release |
| `scripts/validate-mapping-csv.py` | CSV validation with GitHub Actions annotations | **ACTIVE (CI)** | `.github/workflows/validate-mapping-pr.yml`, `pull_request` on `*/Mappings/*.csv` |
| `scripts/mapping-coverage.py` | Regenerates `COVERAGE.md` + `coverage-data.json` | **ACTIVE (CI)** | `.github/workflows/update-coverage.yml`, push to `main` |
| `scripts/trim-csv-columns.py` | Prefix-trims a CSV to N columns | **ACTIVE** | `execute-pipeline.sh:72` |
| `scripts/new-vocab.sh` | Scaffolds a package, checks and appends `id-registry.csv`, creates the database | **ACTIVE** | Generated both live `vocab.env` files (their header comments) |
| `scripts/diff-deltas.sh` | Compares `./output/` against `<VOCAB>/Ontology/` | **ACTIVE but not a gate** | ADR D6.5 (`:118`) enumerates: diffs the working tree not git, exits 0 on drift, compares only 3 files and only when counts changed, committed mode 100644 |
| `scripts/promote-deltas.sh` | Gated `output/` → `Ontology/` promotion | **ACTIVE** | PR #4; runs the drift diff first, copies only on `--apply`, never commits (`:101-137`) |
| `scripts/package-release.sh` | Zips `<VOCAB>/Ontology/` → `release/{VOCAB}-v{VERSION}.zip` | **ACTIVE (CI)** | `release-vocab.yml:28-31` |
| `scripts/package-mapping-release.py` | Emits the 23-column quoted CSV for AWS Athena | **ACTIVE** | §5, Seam A |
| `scripts/excel-to-csv.py` | `.xlsx` → validated UTF-8 CSV for curators | **ACTIVE (manual)** | `EU1_CDW/README.md:15` |
| `docker/` + `docker-compose.yml` | `postgres:16-alpine` plus a runner image with python3 | **ACTIVE** | The documented invocation (`execute-pipeline.sh:9`) |
| `.github/workflows/release-vocab.yml` | Packages and publishes vocabulary zips | **ACTIVE, with a known footgun** | Triggers on `workflow_dispatch` **and** `push: tags: ['v*']` (`:2-10`). ADR D8 (`:148`) rules the tag trigger removed; still present |
| `.github/workflows/build-{gis,mimic,psychiatry}-vocab.yml` | Legacy self-hosted-runner builds | **DORMANT (dead)** | Path filters are `GIS/Builder/**` etc. but the directories are dot-prefixed `.GIS/` — the filter can never match (`build-gis-vocab.yml:6`). They also `runs-on: self-hosted` and use the retired `git-integration.js`. ADR D7.4 orders deletion |
| `.GIS/`, `.MIMIC/`, `.PSYCHIATRY/` | Archived vocabularies: full forked pipeline copies plus **committed `Ontology/` delta sets** | **DORMANT (archived, grandfathered-frozen)** | Dot-prefixed; inverted id ranges frozen by D5.3; dual-minted concepts frozen by D9 (`:170`). These are the only committed delta sets in the repo |
| `publications/JAMIA/fca_methods_paper/` | Manuscript materials for the FCA methods paper | **DORMANT (documentation)** | No tooling references it |
| `publications/JAMIA/subagent_orchestration_mapping/` | Token-accounting scripts over session logs, plus finished result artifacts | **DORMANT (one-off analysis)** | Hardcodes a local `~/.claude/projects/...` path |
| `docs/architecture/cvb_builder_ADR.md` | The one design record | **ACTIVE** | Linked from `README.md:4` |
| `README.md` | Repo overview | **ACTIVE but substantially stale** | Describes Google Sheets sync, `git-integration.js` (`:28`), and Azure-hosted runners (`:76-83`) — all retired; its Reserved Ranges table (`:6-14`) is superseded by `id-registry.csv` |

Neither live package has a committed `Ontology/` baseline: both directories contain only `.gitkeep`. A release cut today would ship empty zips for both, which is issue #607 (`cvb_builder_ADR.md:190`).

---

## 5. The two seams

CVB touches Emory's warehouse at exactly two places. They carry different artifacts to different consumers, and **only one of them is built.**

### Seam A — the mapping sheet → AWS Athena. BUILT, in production.

```
EU1_CDW/Mappings/mapping.csv                          (24 cols, git)
  └─ scripts/package-mapping-release.py               → 23-col fully-quoted CSV
      └─ aws s3 cp → s3://416-omop-etl-hub/global-data/external/mapping_sssom/   [manual]
          └─ omop_etl.src_mapping_sssom               (Glue external table; macro create_external_table_src_mapping_sssom)
              └─ omop_etl.mapping_sssom               (dbt model, EmoryOMOPVocabulariesIngest)
                  └─ 37 join sites in EmoryOmopCDW + Winship / Nursing / BrainHealth pass-throughs
```

The contract is `RELEASE_COLUMNS` — the canonical 21 plus the two date extensions (`scripts/cvb_constants.py:58-61`). The serde is OpenCSVSerde with `quoteChar='"'`, `escapeChar='\'`, `skip.header.line.count=1`, and the packager quotes every field and doubles backslashes (`package-mapping-release.py:18-39`); this was chosen because the legacy LazySimpleSerDe ingest column-shifted 1,644 rows on embedded commas (`package-mapping-release.py:24-25`; `EU1_CDW/README.md:43`). Publication is a manual three-step runbook — package, `aws s3 cp`, then `dbt run-operation create_external_table_src_mapping_sssom && dbt build --select mapping_sssom` — documented verbatim at `EU1_CDW/README.md:31-41`, with workflow wiring explicitly deferred (`:35`). Parity is maintained by hand in two places: `ROW_IDENTITY_COLUMNS` "mirrored by the dbt test `mapping_sssom_duplicate_rows.sql` in `emory_omop_enterprise` — the two must agree" (`cvb_constants.py:80-81`).

Status: live for EU1_CDW at 36,858 rows (`cvb_builder_ADR.md:210`); not yet done for EU2/Epic. **UNCERTAIN:** whether the S3 object currently matches the committed sheet — the prefix is unversioned and no manifest is committed, so this is not statically verifiable from either repo.

**The consumer shipped before the producer.** The 37 CDW join sites already select `m.source_concept_id` — which is empty on all 36,858 rows (§2.1). `*_source_concept_id` therefore loads NULL in production today, and will until a mint runs and its ids are written back into column 2 of the sheet. Note the direction: **the minted ids reach AWS Athena through Seam A**, not Seam B.

### Seam B — the concept deltas → the warehouse. NOT BUILT.

The CVB side is defined and partly shipped. The build stops at `./output/` and never writes `Ontology/` (ADR D3, `cvb_builder_ADR.md:59-69`), enforced by `scripts/promote-deltas.sh`, which runs the drift diff first and copies only on `--apply` and never commits. Committed `Ontology/*.csv` is designated the row-level id-registry-of-record and the sole input to the release packager (ADR D2, `:49-57`). `scripts/package-release.sh` zips it.

**The warehouse side does not exist.** There is no S3 prefix for deltas, no `create_external_table_src_concept_delta` macro, no merged model, and no consumer of `Ontology/*.csv` anywhere in `emory_omop_enterprise`. `EmoryOMOPVocabulariesIngest` contains ten models — the nine OHDSI bundle tables plus `mapping_sssom` — and `concept.sql` is a straight typed read of `src_concept` alone. The "merged Emory concept surface" named in several existing dbt tests is aspirational naming over a surface that is community-bundle-only. The enterprise ADR's D7 contract, "Original ⊕ Delta → Merged", describes the *design*; the delta lane of it is unimplemented in every form.

**This is the single largest gap in the system: even after a successful mint, the minted concepts have nowhere to land.** Stating what the existing idiom implies Seam B would look like — promote and commit `Ontology/` → publish CSVs to a per-table S3 prefix → sibling `create_external_table_*` macros → a merged model unioning `src_concept` ⊕ `src_concept_delta` with delta-wins — is a description of the shape, not a recommendation, and none of those four steps exists.

There is no other coupling. A full-repo search finds no `boto3`, no AWS SDK dependency in any `pyproject.toml`, no IaC, no CI job with cloud credentials, and exactly one `s3://` URI in the whole repo (`EU1_CDW/README.md:36`).

---

## 6. Execution model

**How a build runs today.** From the repo root, against a running compose stack:

```bash
docker compose run runner EU1_CDW/Builder/execute-pipeline.sh
```

(`execute-pipeline.sh:9`). The runner container bind-mounts the repo at `/workspace` and `./output` at `/tmp/output`, and reaches the `db` service via `PGHOST=db` (`docker-compose.yml:17-31`). The twelve steps: create staging DDL → trim and `\copy` the sheet → normalize into `temp.source_to_update` → recreate the id sequence → evaluate differences → stage S concepts → stage NS concepts → stage synonyms → detect deprecations → dedup → apply to `vocab.*` → log. Then the export block creates the eleven `temp.*_delta` tables, writes `restore.sql` via `pg_dump --column-inserts`, and `\copy`s ten delta CSVs plus `update_log.csv` to `/tmp/output` (`:162-202`).

Registration is a run-once, per-package step that is **commented out by default** (`execute-pipeline.sh:49`): `create-general-concepts.sql` inserts the vocabulary's own concept into `vocab.concept` and its row into `vocab.vocabulary`. Reverting is `revert-db.sh` per package, over `hard-reset.sql`, which deletes every `>= 2000000000` row across seven tables plus *all* of `source_to_concept_map` and `mapping_metadata` (`hard-reset.sql:4-15`) — destructive against whatever database it is pointed at.

The persistent writes all happen in step 11, `execute-core-update.sql`: inserts into `vocab.concept` (`:3`, `:25`), `concept_relationship` (`:48`, `:74`, `:214`, `:229`), `concept_ancestor` (`:88`), `source_to_concept_map` (`:98`, `:285`), `concept_synonym` (`:308`), `mapping_metadata` (`:316`), `concept_relationship_metadata` (`:319`); updates to `concept_relationship` for deprecations (`:127`, `:140`, `:153`, `:166`), `source_to_concept_map` (`:185`, `:195`), `vocabulary.latest_update` (`:322`) and `vocab.concept` (`:326`).

**Where it runs in production is unruled.** The repo provides a local Docker Postgres and nothing else. The ADR rules thoroughly on *what* the pipeline computes (D4 intervals, D5 guards, D6 re-runnability, D9 resolution model) and never on *where it executes*, though its implementation guidance assumes PostgreSQL throughout — psql variables, `CREATE SEQUENCE`, `ctid`-based dedup, `pg_dump`. That is an open consult, not a settled decision: see §7.

One consequence of the current model worth stating plainly, because it is what makes the execution question expensive: `vocab.*` is both the reference data and the output store. The build reads the licensed bundle and writes minted rows into the same tables, so whatever hosts it must hold the full bundle (§3.2) *and* tolerate a destructive, rebuild-oriented workload (`hard-reset.sql`, per-run `DROP TABLE` on staging).

**Re-runnability.** ADR D6 (`cvb_builder_ADR.md:110-126`) defines the contract as id-*stability*, not byte-determinism, and names its preconditions: seeded database, working existence guards, hardened drift check. On this tree the seed script does not exist (§3.4), the S-side existence guard does not fire (§7), and `diff-deltas.sh` cannot serve as the acceptance test (D6.5). The contract is therefore stated but not currently demonstrable.

---

## 7. Known defects and open questions

These are inventoried with pointers, not resolved. Design questions belong as consults against `cvb-builder-adr` (`cvb_builder_ADR.md:197-199`), not in this document and not in PR bodies.

### 7.1 The open substrate consult — not ruled here

Board issue **`issue-cvb-mint-substrate-postgres-vs-athena`**, status `active`, owner `user`. The question: does Emory's EU1_CDW NS mint run through the dockerized Postgres Builder, or natively against inputs that already sit in AWS Athena (`omop_etl.mapping_sssom` plus the vocabulary bundle)? It was raised after an implementation session hardened the Postgres Builder for a full session before anyone asked where the database would live. Its own correction note (2026-07-24) narrows it: the enterprise ADR does scope the Builder's delta-generation subset into phase 1, so "a recorded decision defers the Builder" was retracted; what remains open is (a) where the Builder's Postgres runs and how it is isolated, and (b) that Seam B does not exist at all. **This document does not rule it.** It supplies §3 and §5 as the inventory the ruling needs.

### 7.2 D9 is ruled but not implemented — the mint would violate its own invariant

ADR D9 (`cvb_builder_ADR.md:159-172`) rules one concept per `(vocabulary_id, concept_code)`, NS-only automated mint, and zero-by-omission. **None of that is in the code on this tree.** `evaluate-difference.sql:16-26` still routes `nomatch` rows into `temp.concept_check_s` (the predicate is explicit at `:24`), and `update-standard.sql:23-52` still mints an S concept for each. For EU1_CDW that is **2,325 `noMatch` rows**, every one of which would receive a custom Standard concept on the first build. Meanwhile `temp.concept_check_ns` takes *all* `source_to_update` rows (`evaluate-difference.sql:83-90`), and `noMatch` rows carry `target_concept_id = 0` — so whether they *also* mint an NS concept depends on whether concept 0 is present in the loaded bundle, since `update-nonstandard.sql:69` inner-joins on it. **UNCERTAIN** (a standard OHDSI load does contain concept 0, which would make the dual mint materialize and directly violate D9's plank 1). The S half is unconditional either way. There is also no uniqueness gate and no NS exhaustion guard (ADR D5.2). The parked `128c39e` implements this; it is unmerged.

### 7.3 Interval-contract items not shipped (ADR D4/D5)

Range predicates are still strict at both ends rather than `>= min`: `evaluate-difference.sql:21,:88`, `create-delta-tables.sql:17-27`, `revert-id-sequence.sql:15`, `update-nonstandard.sql:46`. The `SRC_DESC_MATCH` dead-code path D5.4 orders removed is still present (`evaluate-difference.sql:30-33,:66-72`). The distinct psql variable names D4 specifies are not shipped (§2.2). The registry annotations for the inverted archived rows are not shipped (§2.3).

### 7.4 Export-set inconsistencies (ADR D2)

Verified against the code on this tree. `temp.concept_relationship_metadata_delta` is created (`create-delta-tables.sql:35`) but appears in **neither** the CSV export loop (`execute-pipeline.sh:183-194`) nor the `pg_dump` table list (`:171-180`) — a delta table that silently never ships. And `domain_delta` and `relationship_delta` ship as CSVs but are **absent** from the `pg_dump` list, so `restore.sql` does not round-trip the full set.

Partially good news, worth checking before the chore is scoped: D6.4 asks for `ORDER BY` on delta exports, and ten of the eleven `CREATE TABLE ... AS` statements in `create-delta-tables.sql` already carry one (all but `concept_class_delta` at `:29`). **UNCERTAIN** whether that satisfies the intent — a CTAS `ORDER BY` fixes heap order at creation, which `\copy` will normally follow, but it is not a guarantee the way an ordered `COPY (SELECT … ORDER BY …)` would be.

### 7.5 Sheet-shape defects

EU2's `ws_frequency` / `status` column shift (§2.1), on the ADR backlog at `:195`. EU2 also carries 28 `relatedMatch` rows, which `cvb_constants.py:91-94` does not list among `VALID_RELATIONSHIP_PREDICATES` — the ADR backlog records this as "EU2 CI red with 28 `relatedMatch` rows" (`:195`), and the measured count matches exactly.

Note one defect of this class that is **resolved** on this tree, contrary to an earlier inventory: `author_label` sits at the same position in `_TEMPLATE` and EU2 (`source-ddl.sql:33` in `temp.mapping` and `:67` in `temp.source_to_update`, in both files). PR #3's back-port fixed it; the two files are byte-identical.

A possible constraint conflict, flagged as **UNCERTAIN** because it has not been observed at runtime: `vocab.concept_relationship_metadata` carries `CHECK (relationship_predicate_id IN ('exactMatch','broadMatch','narrowMatch','relatedMatch','noMatch'))` (`docker/init-db/01-create-vocab-schema.sql:141`), while `update-nonstandard.sql:711` stages `trim(stu.predicate_id)` verbatim from the sheet. Both live sheets use the bare forms, which satisfy the check; a sheet using the `skos:`-prefixed forms that `cvb_constants.py:105-110` normalizes elsewhere would fail the insert at step 11. Whether any package can produce that is untested.

### 7.6 Release and process gaps

The `push: tags: ['v*']` trigger on `release-vocab.yml:8-10` means any semver milestone tag silently cuts a full vocabulary release; ADR D8 rules it removed. `diff-deltas.sh` is not a drift gate and is committed non-executable (D6.5). Three dead workflows remain (§4). `README.md` still documents a retired Google Sheets / Azure-runner / `git-integration.js` architecture.

### 7.7 Open questions carried from the ADR

The provenance-tagging WIP posture (`cvb_builder_ADR.md:203`) — uncommitted work touching the same files as the interval chore, with a rider that its `CONCEPT_RESOLUTION.md` must be rewritten to the D9 model. And the enterprise-side disagreement recorded in the substrate issue: the enterprise ADR's D6 (dual S+NS mint) is superseded by CVB D9 (NS-only) without the enterprise ADR having been amended.

### 7.8 CVB has no steward

There is no continuous owner. `cvb-builder-adr` is an *episodic design address* — it answers consults when asked, and correctly declines to be a standing maintainer. The absence of a steward is a documented root cause: the substrate issue names it directly ("CVB has no `ARCHITECTURE.md`, no inputs inventory, and no steward … so nothing contradicted the premise until the question was asked directly"). This document closes the first two. The third is a posture question for Daniel, raised in the PR that introduces this file, not decided here.
