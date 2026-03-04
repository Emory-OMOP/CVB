# Contributing Mappings

## Overview

External teams contribute concept mappings by submitting CSV files via pull request.
Emory reviews and incorporates mappings into the vocabulary build pipeline.

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
| `source_vocabulary_id` | Yes | Must match the vocabulary ID (e.g., `CARDIOLOGY`) |
| `source_domain` | No | OMOP domain (Condition, Procedure, Measurement, etc.) |
| `source_concept_class_id` | No | Defaults to `Suppl Concept` if blank |
| `source_description` | Yes | Human-readable name (max 255 chars) |
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

## Workspace Columns (Column 22+)

Columns 1–21 (`source_concept_code` through `status`) are **pipeline columns** — they are loaded into the database during vocabulary builds.

**Column 22 and beyond are workspace columns.** The pipeline automatically strips these before loading. Use them freely for:

- Usage frequency / volume metrics
- Prioritization notes
- Template/context information
- Coordinator assignments or comments
- Any other operational data that aids the mapping workflow

Workspace columns are preserved in the CSV and visible in the coverage dashboard, but never enter the vocabulary database.

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

## Validation Checklist

Before submitting your PR:

- [ ] All required columns are present
- [ ] `source_concept_code` values are unique within the file
- [ ] `predicate_id` uses valid SSSOM predicates
- [ ] `confidence` values are between 0 and 1
- [ ] `target_concept_id` is a valid OMOP concept_id (or 0 for noMatch)
- [ ] File is UTF-8 encoded CSV
- [ ] No trailing commas or malformed rows
