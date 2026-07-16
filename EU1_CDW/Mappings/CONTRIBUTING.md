# Contributing Mappings — EU1_CDW

## Overview

Curators edit the mapping sheet in Excel/Google Sheets, export via `scripts/excel-to-csv.py`, and submit it as a pull request. CI validates the file and posts a diff of what changed; reviewers judge **concept choices only**.

Reviewers do not judge routing. Routing is not in this sheet and cannot be: the ETL asks the *current* `concept.domain_id` of the mapped target at read time. There is no `target_column` and no routing map anywhere a human can write one — that is the entire point of the redesign (ADR D1/D5).

## Submission Steps

1. Download the mapping template (`mapping.csv` headers or `mapping_template.xlsx`)
2. Fill in your mappings following the column specifications below
3. Export to CSV (UTF-8, comma-delimited)
4. Open a pull request adding your CSV to this `Mappings/` directory
5. Use the mapping contribution PR template for your pull request

## Required Columns

| Column | Required | Description |
|--------|----------|-------------|
| `source_concept_code` | Yes | Unique code for the source concept (max 50 chars) |
| `source_concept_id` | No | Set to 0 for new concepts |
| `source_vocabulary_id` | Yes | The EU1 source vocabulary (e.g., `EU1_ORDER_SYNONYM`, `EU1_Units_UnitMeas`) |
| `source_domain` | No | OMOP domain (Condition, Procedure, Measurement, etc.) |
| `source_concept_class_id` | No | Defaults to `Suppl Concept` if blank |
| `source_description` | Yes | Human-readable name (max 255 chars). **Part of row identity** — see Duplicates |
| `source_description_synonym` | No | Alternative name / abbreviation |
| `relationship_id` | No | OMOP relationship (e.g., `Maps to`) |
| `predicate_id` | Yes | Predicate: `exactMatch`, `broadMatch`, `narrowMatch`, `noMatch` (or OHDSI: `eq`, `up`, `down`). Legacy `skos:` prefixed forms accepted. |
| `mapping_tool` | No | OHDSI mapping tool taxonomy: `MM_C`, `MM_U`, `AM-lib_C`, `AM-lib_U`, `AM-tool_C`, `AM-tool_U` |
| `confidence` | Yes | 0.0 to 1.0 |
| `target_concept_id` | Yes | OMOP concept_id of the target (0 if no match) |
| `target_concept_name` | No | Name of the target concept |
| `target_vocabulary_id` | No | Vocabulary of the target concept |
| `target_domain_id` | No | Domain of the target concept |
| `mapping_justification` | No | Reason for the mapping |
| `author_label` | No | Name of the person creating the mapping |
| `review_date` | No | Date reviewed (YYYY-MM-DD) |
| `reviewer_name` | No | Name of reviewer |
| `reviewer_specialty` | No | Clinical specialty of reviewer |
| `status` | No | Mapping status (e.g., `approved`, `pending`) |

## Extension Columns (Column 22+)

Columns 1–21 (`source_concept_code` through `status`) are **pipeline columns** — they are loaded into the database during vocabulary builds. Columns 22+ are Emory extension/workspace columns, stripped before the Builder load.

| Column | Type | Ships to the warehouse? |
|--------|------|--------------------------|
| `valid_start_date` | ISO date `YYYY-MM-DD` | Yes — released to `omop_etl.src_mapping_sssom` |
| `valid_end_date` | ISO date `YYYY-MM-DD`, `>= valid_start_date` | Yes — released to `omop_etl.src_mapping_sssom` |
| `source_frequency` | numeric | No — curation priority only, trimmed at release |

Register any new extension column in `scripts/cvb_constants.py` (`KNOWN_EXTENSION_COLUMNS`). Unregistered columns warn in CI and are silently dropped at release.

## Nothing is opt-out

Every curated row loads, including human-adjudicated no-matches. "A human tried and could not find anything right" is information: `noMatch` rows (with `target_concept_id = 0`) mint their source concept with no mapping relationship, and stand as the visible unmapped backlog. Do not delete a row to express "no match" — set the predicate.

## Predicate Reference

Predicates align with the OHDSI Vocabulary WG standard. Legacy `skos:` prefixed forms are accepted and normalized automatically.

### Relationship predicates (recorded in `concept_relationship_metadata`)

| Predicate | OHDSI code | Use when... |
|-----------|------------|-------------|
| `exactMatch` | `eq` | Source concept maps exactly to an existing OMOP concept |
| `broadMatch` | `up` | Source is more specific than target (source "Is a" target) |
| `narrowMatch` | `down` | Source is broader than target (target "Is a" source) |

### Pipeline directives (not relationship predicates)

| Directive | Use when... |
|-----------|-------------|
| `noMatch` | No existing OMOP concept; a new standard custom concept will be created (no mapping relationship is recorded) |

> **Note:** `relatedMatch` is no longer accepted. If you need to express associated concepts, use domain-specific OMOP relationships directly.

## Duplicates: row identity

A row's identity is the tuple **(`source_vocabulary_id`, `source_concept_code`, `source_description`, `target_concept_id`, `relationship_id`)**. Only a fully identical tuple is a duplicate, and CI fails on it.

Repeating a `source_concept_code` is legitimate and common:

- **Multi-mapping** — one source code that genuinely means two things maps to two distinct targets.
- **Multi-relationship** — one source/target pair related more than once: a `Maps to` edge alongside a `Has finding site` / `Has context` / `Has dir device` attribute edge, or the `Maps to value` row required for a Measurement item that carries a value. These become distinct `concept_relationship` rows; the pair is not redundant.
- **`*_VAL` vocabularies are description-keyed** — the device pull matches on the description *substring*, so the 48 `STRUCTURED_RESULT_TYPE_VAL` codes expand to 635 rows that share a code and differ by description fragment. The description is a join key, not a label. Do not "clean up" these rows by collapsing them.

## Validation Checklist

Before submitting your PR:

- [ ] All required columns are present
- [ ] No two rows share the full identity tuple (see Duplicates — repeated codes are fine)
- [ ] `predicate_id` uses valid SSSOM predicates
- [ ] `confidence` values are between 0 and 1
- [ ] `target_concept_id` is a valid OMOP concept_id (or 0 for noMatch)
- [ ] `valid_start_date` / `valid_end_date` are ISO dates and start <= end
- [ ] File is UTF-8 encoded CSV
- [ ] No trailing commas or malformed rows
